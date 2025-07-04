from django.urls import path
from .views import TaskListCreateView, TaskDetailView,AddCommentView,UpdateCommentView,DeleteCommentView,CommentLikeAPIView

urlpatterns = [
    path("", TaskListCreateView.as_view(), name="task-list-create"),
    path("<int:pk>/", TaskDetailView.as_view(), name="task-detail"),
    path(
        "<int:pk>/comment/", AddCommentView.as_view(), name="add-comment"
    ),  # for adding a comment to a specific post
    path(
        "comment/<int:pk>/update/",
        UpdateCommentView.as_view(),
        name="update-comment",
    ),  # for updating a specific comment
    path(
        "comment/<int:pk>/delete/",
        DeleteCommentView.as_view(),
        name="delete-comment",
    ),  # for deleting a specific comment
    path(
        "comment/<int:pk>/like/",
        CommentLikeAPIView.as_view(),
        name="like-comment",
    ),  # for liking a specific comment
]
