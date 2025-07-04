from rest_framework import serializers

from user.models import User, UserProfile
from .models import Task, Comment, CommentLike


class SampleUserProfileData(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ["full_name", "profile_picture"]

    def get_profile_picture(self, obj):
        request = self.context.get("request")
        url = obj.get_profile_picture
        return request.build_absolute_uri(url) if request else url


class SampleUserData(serializers.ModelSerializer):
    profile = SampleUserProfileData(source="userprofile", read_only=True)

    class Meta:
        model = User
        fields = ["id", "profile"]


class CommentLikeSerializer(serializers.ModelSerializer):
    created_by = SampleUserData(read_only=True)

    class Meta:
        model = CommentLike
        fields = ("id", "created_by", "comment", "reaction_type", "created_at")
        read_only_fields = ("id", "created_by", "created_at")


class CommentSerializer(serializers.ModelSerializer):
    created_by = SampleUserData(read_only=True)
    replies = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "created_by",
            "task",
            "parent",
            "content",
            "replies",
            "likes",  # <-- Add likes field (optional)
            "like_count",  # <-- Add like_count field (optional)
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "task", "created_at", "updated_at"]

    def get_replies(self, obj):
        replies = obj.replies.all()  # Get all replies (children)
        return CommentSerializer(replies, many=True, context=self.context).data

    def get_like_count(self, obj):
        return obj.likes.count()

    def get_likes(self, obj):
        likes = obj.likes.select_related(
            "created_by", "created_by__userprofile"
        )  # Avoid N+1 queries
        data = []

        for like in likes:
            user = like.created_by
            profile_picture_url = None
            request = self.context.get("request")

            if hasattr(user, "userprofile") and user.userprofile.profile_picture:
                profile_picture_url = request.build_absolute_uri(
                    user.userprofile.get_profile_picture
                )
            else:
                # fallback if no profile or no picture
                profile_picture_url = (
                    "/static/default_images/default_profile_picture.jpg"
                )
                profile_picture_url = request.build_absolute_uri(profile_picture_url)

            data.append(
                {
                    "id": user.id,
                    "username": user.username,
                    "image": profile_picture_url,
                    "reaction_type": like.reaction_type,
                    "reaction_display": like.get_reaction_type_display(),
                }
            )

        return data

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["created_by"] = user
        return super().create(validated_data)


class SampleTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "owner",
            "title",
            "description",
            "status",
            "priority",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]


class TaskSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "owner",
            "title",
            "description",
            "status",
            "priority",
            "created_at",
            "updated_at",
            "comments",
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]
