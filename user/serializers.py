from rest_framework import serializers
from .models import User, UserProfile
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone


class SampleUserData(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "username"]
        extra_kwargs = {
            "username": {"validators": []}  # disable default uniqueness validator
        }

    def validate_username(self, value):
        user = self.context["request"].user
        if User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value


class UserProfileSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()
    cover_picture = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "full_name",
            "full_address",
            "country",
            "city",
            "phone_number",
            "gender",
            "date_of_birth",
            "age",
            "is_adult",
            "marital_status",
            "bio",
            "profile_picture",
            "cover_picture",
            "work",
            "education",
        ]

    def get_profile_picture(self, obj):
        request = self.context.get("request")
        url = obj.get_profile_picture
        return request.build_absolute_uri(url) if request else url

    def get_cover_picture(self, obj):
        request = self.context.get("request")
        url = obj.get_cover_picture
        return request.build_absolute_uri(url) if request else url


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(source="userprofile", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "username",
            "source",
            "is_active",
            "profile",
            "date_joined",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "password", "password2"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords must match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")  # Remove password2 from data
        user = User.objects.create_user(**validated_data)
        return user


class ActiveAccountSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=100)
    otp = serializers.CharField(max_length=100)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                "New password and confirm password do not match."
            )
        return data


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_otp(self, value):
        """Validate the OTP"""
        user = User.objects.get(email=self.initial_data["email"])
        if user.otp != value:
            raise serializers.ValidationError("Invalid OTP")
        return value

    def save(self):
        email = self.validated_data["email"]
        new_password = self.validated_data["new_password"]

        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.save()

        # Clear OTP after successful reset
        user.otp = None
        user.save()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class SocialLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(
        required=False, allow_blank=True
    )  # Optional for login
    first_name = serializers.CharField(
        required=False, allow_blank=True
    )  # Optional for login
    last_name = serializers.CharField(
        required=False, allow_blank=True
    )  # Optional for login
    profile_image = serializers.ImageField(
        required=False, allow_null=True
    )  # Optional for login
    source = serializers.CharField(
        required=False, allow_blank=True
    )  # Optional for login

    def create_or_get_user(self, validated_data):
        email = validated_data.get("email")
        username = validated_data.get("username", email.split("@")[0])
        first_name = validated_data.get("first_name", "")
        last_name = validated_data.get("last_name", "")
        source = validated_data.get("source", "local")
        image = validated_data.get("profile_image", None)

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": username,
                "first_name": first_name,
                "last_name": last_name,
                "source": source,
            },
        )
        if created and image:
            user.userprofile.profile_picture = image
            user.userprofile.save()

        refresh = RefreshToken.for_user(user)
        tokens = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

        return user, created, tokens


class UserProfileUpdate(serializers.ModelSerializer):
    user = SampleUserData()

    class Meta:
        model = UserProfile
        fields = [
            "profile_picture",
            "cover_picture",
            "country",
            "city",
            "phone_number",
            "bio",
            "gender",
            "date_of_birth",
            "age",
            "is_adult",
            "marital_status",
            "work",
            "education",
            "user",
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
