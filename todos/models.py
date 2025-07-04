from django.db import models
from user.models import User

# Create your models here.
class Task(models.Model):
    STATUS_CHOICES = [
        ("todo", "To Do"),
        ("in_progress", "In Progress"),
        ("done", "Done"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="todo")
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default="medium"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class CommentLike(models.Model):
    REACTION_CHOICES = (
        ("like", "👍"),
        ("love", "❤️"),
        ("haha", "😂"),
        ("wow", "😮"),
        ("sad", "😢"),
        ("angry", "😡"),
    )

    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.ForeignKey(
        "Comment", on_delete=models.CASCADE, related_name="likes"
    )  # Connect to Comment
    reaction_type = models.CharField(
        max_length=10, choices=REACTION_CHOICES, default="like"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [
            "created_by",
            "comment",
        ]  # Ensure one reaction per user per comment

    def __str__(self):
        return f"{self.get_reaction_type_display()} reaction by {self.created_by.username} on {self.created_at}"


class Comment(models.Model):
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )  # For replies
    content = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    @property
    def is_reply(self):
        return self.parent is not None

    def __str__(self):
        if self.is_reply:
            return f"Reply by {self.created_by.username} on {self.created_at}"
        return f"Comment by {self.created_by.username} on {self.created_at}"

