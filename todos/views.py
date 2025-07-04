from rest_framework.views import APIView
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from .models import Task, Comment,CommentLike
from .serializers import TaskSerializer, CommentSerializer, SampleTaskSerializer
from core.pagination import CustomPagination
from core.responses import CustomResponse


class TaskListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPagination

    def get(self, request):
        status_filter = request.query_params.get("status")
        tasks = Task.objects.filter(owner=request.user)
        if status_filter:
            tasks = tasks.filter(status=status_filter)

        paginator = self.pagination_class()
        paginated_tasks = paginator.paginate_queryset(tasks, request)
        serializer = SampleTaskSerializer(
            paginated_tasks, many=True, context={"request": request}
        )
        pagination_meta = paginator.get_pagination_meta()

        return CustomResponse(
            data=serializer.data, status=status.HTTP_200_OK, pagination=pagination_meta
        )

    def post(self, request):
        serializer = TaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(owner=request.user)
            return CustomResponse(
                data=serializer.data,
                status=status.HTTP_201_CREATED,
                message="Task created successfully",
            )
        return CustomResponse(
            data=serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )


class TaskDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk, user):
        return get_object_or_404(Task, pk=pk, owner=user)

    def get(self, request, pk):
        task = self.get_object(pk, request.user)
        serializer = TaskSerializer(task, context={"request": request})
        return CustomResponse(data=serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        task = self.get_object(pk, request.user)
        serializer = TaskSerializer(task, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(owner=request.user)
            return CustomResponse(
                data=serializer.data,
                status=status.HTTP_200_OK,
                message="Task updated successfully",
            )
        return CustomResponse(
            data=serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        task = self.get_object(pk, request.user)
        task.delete()
        return CustomResponse(
            data={},
            status=status.HTTP_204_NO_CONTENT,
            message="Task deleted successfully",
        )


class AddCommentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            task = Task.objects.get(pk=pk)
        except Task.DoesNotExist:
            return CustomResponse(
                data={},
                message="Task not found",
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CommentSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save(task=task)
            return CustomResponse(
                data=serializer.data,
                message="Comment added successfully",
                status=status.HTTP_201_CREATED,
            )

        return CustomResponse(
            data={}, message=serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )


class CommentLikeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            comment = Comment.objects.get(pk=pk)
            reaction_type = request.data.get(
                "reaction_type", "like"
            )  # Default to 'like' if not specified

            # Validate reaction type
            if reaction_type not in dict(CommentLike.REACTION_CHOICES):
                return CustomResponse(
                    status=status.HTTP_400_BAD_REQUEST,
                    message="Invalid reaction type",
                )

            # Check if a Like by this user already exists
            like = comment.likes.filter(created_by=request.user).first()

            if not like:
                # Create a Like object with reaction
                like = CommentLike.objects.create(
                    created_by=request.user,
                    comment=comment,
                    reaction_type=reaction_type,
                )

                message = f"Comment {reaction_type} reaction added successfully"
            else:
                if like.reaction_type == reaction_type:
                    # If same reaction, remove it (unlike)
                    like.delete()
                    message = f"Comment {reaction_type} reaction removed successfully"
                else:
                    # If different reaction, update it
                    like.reaction_type = reaction_type
                    like.save()
                    message = (
                        f"Comment reaction updated to {reaction_type} successfully"
                    )

            serializer = CommentSerializer(comment, context={"request": request})
            return CustomResponse(
                data=serializer.data,
                status=status.HTTP_200_OK,
                message=message,
            )

        except Comment.DoesNotExist:
            return CustomResponse(
                status=status.HTTP_404_NOT_FOUND,
                message="Comment not found",
            )


class UpdateCommentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        try:
            comment = Comment.objects.get(pk=pk)
        except Comment.DoesNotExist:
            return CustomResponse(
                data={},
                message="Comment not found",
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CommentSerializer(
            comment, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                data=serializer.data,
                message="Comment updated successfully",
                status=status.HTTP_200_OK,
            )

        return CustomResponse(
            data={}, message=serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )


class DeleteCommentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            comment = Comment.objects.get(pk=pk)
            comment.delete()
            return CustomResponse(
                data={},
                message="Comment deleted successfully",
                status=status.HTTP_200_OK,
            )
        except Comment.DoesNotExist:
            return CustomResponse(
                data={}, message="Comment not found", status=status.HTTP_404_NOT_FOUND
            )
