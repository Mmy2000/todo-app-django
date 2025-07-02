import random
from rest_framework import status,generics
from rest_framework.views import APIView
from user.models import  UserProfile
from rest_framework_simplejwt.tokens import RefreshToken
from core.pagination import CustomPagination
from .serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    UserProfileUpdate,
    UserSerializer,
    ActiveAccountSerializer,
    SocialLoginSerializer,
)
from core.responses import CustomResponse
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils.translation import gettext as _
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q

# Create your views here.
User = get_user_model()


class SendOTPEmailMixin:
    def send_otp(self, email):
        otp = random.randint(1000, 9999)

        self.send_message(email, f"Your OTP code is {otp}", "Your OTP Code")
        return otp

    def send_message(self, email, message, subject):
        email = EmailMessage(
            subject, message, from_email=settings.EMAIL_HOST_USER, to=[email]
        )
        try:
            email.send()
        except Exception as e:
            # This because sending mail from pc issues
            pass


class RegisterView(SendOTPEmailMixin, generics.CreateAPIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            user_data = UserSerializer(user, context={"request": request}).data
            otp = self.send_otp(user.email)
            user.otp = otp
            user.save()

            return CustomResponse(
                data={
                    "access": access_token,
                    "refresh": str(refresh),
                    "user_data": user_data,
                },
                status=status.HTTP_201_CREATED,
                message="User registered successfully. Check your email for OTP.",
            )

        return CustomResponse(
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
            message=serializer.errors,
        )


class ActiveAccountView(SendOTPEmailMixin, APIView):
    def post(self, request):
        serializer = ActiveAccountSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get("email")
            otp = serializer.validated_data.get("otp")

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return CustomResponse(
                    data={"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
                )

            if user.otp == otp:
                user.is_active = True
                user.otp = None
                user.save()
                self.send_message(
                    email,
                    "account activated successfully",
                    "account activated successfully",
                )
                return CustomResponse(
                    data=user.otp,
                    status=status.HTTP_200_OK,
                    message="Account activated successfully",
                )

            return CustomResponse(
                data={"error": "Invalid OTP"},
                status=status.HTTP_400_BAD_REQUEST,
                message="Invalid OTP",
            )

        return CustomResponse(
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
            message=serializer.errors,
        )


class LoginView(APIView):
    def post(self, request):
        email_or_username = request.data.get("email_or_username")
        password = request.data.get("password")

        if not email_or_username or not password:
            return CustomResponse(
                data={"error": "Email/Username and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Check if the input is an email or username
            if "@" in email_or_username:
                user = User.objects.get(email=email_or_username)
            else:
                user = User.objects.get(username=email_or_username)
        except User.DoesNotExist:
            return CustomResponse(
                data={"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
                message="Invalid credentials",
            )

        if not user.check_password(password):
            return CustomResponse(
                data={"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
                message="Invalid credentials",
            )

        # Tokens & data
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        user_data = UserSerializer(user, context={"request": request}).data

        if not user.is_active:
            return CustomResponse(
                data={
                    "access": access_token,
                    "refresh": str(refresh),
                    "user_data": user_data,
                },
                status=status.HTTP_403_FORBIDDEN,
                message="Account not active. Please verify OTP.",
            )

        return CustomResponse(
            data={
                "access": access_token,
                "refresh": str(refresh),
                "user_data": user_data,
            },
            status=status.HTTP_200_OK,
            message="Login successful",
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data["current_password"]):
                return CustomResponse(
                    data={},
                    status=status.HTTP_400_BAD_REQUEST,
                    message="Current password is incorrect",
                )

            user.set_password(serializer.validated_data["new_password"])
            user.save()
            return CustomResponse(
                data={},
                status=status.HTTP_200_OK,
                message="Password changed successfully",
            )
        return CustomResponse(
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
            message="Password change failed",
        )


class ForgotPasswordView(SendOTPEmailMixin, generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            email = serializer.validated_data["email"]
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return CustomResponse(
                    data={},
                    message=_("User with this email does not exist."),
                    status=status.HTTP_404_NOT_FOUND,
                )

            otp = random.randint(1000, 9999)
            user.otp = otp
            user.save()

            subject = "Password Reset Request"
            message = f"Hello, use this code to reset your password {otp} ."
            self.send_message(email, message, subject)
            return CustomResponse(
                data={},
                message=_("Password reset email has been sent."),
                status=status.HTTP_200_OK,
            )
        return CustomResponse(
            data=serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )


class ResetPasswordView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            email = serializer.validated_data["email"]
            password = serializer.validated_data["new_password"]
            if User.objects.filter(email=email):
                user = User.objects.get(email=email)
                if user.check_password(password):
                    return CustomResponse(
                        data={},
                        message="not allowed one of your past passwords",
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                user.set_password(password)
                user.otp = None
                user.save()
                return CustomResponse(
                    data={},
                    message="password changed successfully",
                    status=status.HTTP_200_OK,
                )
            else:
                return CustomResponse(
                    data={},
                    message="user not found",
                    status=status.HTTP_400_BAD_REQUEST,
                )


class ResendCodeView(generics.GenericAPIView, SendOTPEmailMixin):
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            email = serializer.validated_data["email"]
            otp = self.send_otp(email)
            user = User.objects.get(email=email)
            user.otp = otp
            user.save()
            return CustomResponse(
                data={},
                message=_("code has been sent successfully"),
                status=status.HTTP_200_OK,
            )


class SocialLoginView(generics.GenericAPIView, SendOTPEmailMixin):

    def post(self, request, *args, **kwargs):
        serializer = SocialLoginSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user, created, tokens = serializer.create_or_get_user(
                serializer.validated_data
            )
            if created:
                # New user registered
                user.otp = random.randint(1000, 9999)
                user.save()
                self.send_message(
                    user.email, f"Your OTP code is {user.otp}", "Your OTP Code"
                )
                return CustomResponse(
                    data={
                        "access": tokens["access"],
                        "refresh": tokens["refresh"],
                        "user_data": UserSerializer(
                            user, context={"request": request}
                        ).data,
                    },
                    status=status.HTTP_201_CREATED,
                    message="User registered successfully. Check your email for OTP.",
                )
            else:
                # Existing user logged in
                if not user.is_active:
                    return CustomResponse(
                        data={
                            "access": tokens["access"],
                            "refresh": tokens["refresh"],
                            "user_data": UserSerializer(
                                user, context={"request": request}
                            ).data,
                        },
                        status=status.HTTP_403_FORBIDDEN,
                        message="Account not active. Please verify OTP.",
                    )
                return CustomResponse(
                    data={
                        "access": tokens["access"],
                        "refresh": tokens["refresh"],
                        "user_data": UserSerializer(
                            user, context={"request": request}
                        ).data,
                    },
                    status=status.HTTP_200_OK,
                    message="Login successful",
                )

        return CustomResponse(
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
            message="Invalid data",
        )


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return CustomResponse(
                data={},
                message=_("logged out successfully"),
                status=status.HTTP_205_RESET_CONTENT,
            )
        except Exception as e:
            return CustomResponse(
                data={}, message=str(e), status=status.HTTP_400_BAD_REQUEST
            )


class ProfileView(APIView):
    serializer_class = UserSerializer
    permission_classes = [
        IsAuthenticated
    ]  # Allow both anonymous and authenticated users

    def get(self, request):
        user = request.user
        user = get_object_or_404(User, id=user.id)
        serializer = self.serializer_class(
            user, partial=True, context={"request": request}
        )

        return CustomResponse(
            data=serializer.data,
            message=_("User profile retrieved successfully"),
            status=status.HTTP_200_OK,
        )


class ProfileUpdateView(APIView):
    serializer_class = UserProfileUpdate
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        try:
            profile = (
                user.userprofile
            )  # make sure every user has a UserProfile instance
        except UserProfile.DoesNotExist:
            return CustomResponse(
                message=_("User profile not found"), status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.serializer_class(
            profile, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            user_serializer = UserSerializer(user, context={"request": request})
            return CustomResponse(
                data=user_serializer.data,
                message=_("User profile updated successfully"),
                status=status.HTTP_200_OK,
            )
        return CustomResponse(
            data=serializer.errors,
            message=_("Failed to update profile"),
            status=status.HTTP_400_BAD_REQUEST,
        )
