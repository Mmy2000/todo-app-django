from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import uuid
from django.conf import settings


class MyAccountManager(BaseUserManager):
    def create_user(self, first_name, last_name, email, password=None):
        if not email:
            raise ValueError("User must have an email address")

        # Ensure username is unique
        username = email.split("@")[0]  # Use the part before the @ as a base username
        while User.objects.filter(username=username).exists():
            # Append a short random string for uniqueness
            random_string = uuid.uuid4().hex[:6]  # Take first 6 characters of a UUID
            username = f"{username}@{random_string}"

        user = self.model(
            email=self.normalize_email(email),
            username=username,  # Auto-generated username
            first_name=first_name,
            last_name=last_name,
        )

        user.set_password(password)
        user.is_active = False
        user.save(using=self._db)
        return user

    def create_superuser(self, first_name, last_name, email, password):
        user = self.create_user(first_name, last_name, email, password)
        user.is_admin = True
        user.is_staff = True
        user.is_superadmin = True
        user.is_active = True  # Superuser should be active by default
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    SOURCES = (
        ("local", "local"),
        ("google", "google"),
        ("facebook", "facebook"),
        ("linkedin", "linkedin"),
        ("twitter", "twitter"),
    )

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=100, unique=True)

    # required
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now_add=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_superadmin = models.BooleanField(default=False)
    otp = models.CharField(max_length=6, blank=True, null=True)
    source = models.CharField(choices=SOURCES, max_length=50, default="local")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = MyAccountManager()

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, add_label):
        return True


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(
        upload_to="users/profile_pictures/", blank=True, null=True
    )
    cover_picture = models.ImageField(
        upload_to="users/cover_pictures/", blank=True, null=True
    )
    country = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    marital_status = models.CharField(max_length=20, blank=True, null=True)
    phone_number = models.CharField(max_length=50, null=True, blank=True)
    work = models.CharField(max_length=50, blank=True, null=True)
    education = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField("created_at", default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_active = models.DateTimeField(default=timezone.now)

    @property
    def age(self):
        if self.date_of_birth:
            return timezone.now().year - self.date_of_birth.year
        return None

    @property
    def is_adult(self):
        if self.date_of_birth:
            return (timezone.now().year - self.date_of_birth.year) >= 18
        return None

    @property
    def get_profile_picture(self):
        if self.profile_picture:
            return self.profile_picture.url
        return "/static/default_images/default_profile_picture.jpg"

    @property
    def get_cover_picture(self):
        if self.cover_picture:
            return self.cover_picture.url
        return "/static/default_images/beach_1.jpg"

    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"

    @property
    def full_address(self):
        return f"{self.country} | {self.city}"

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} Profile"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
