from django.db.models import Q
from rest_framework import generics, status, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from social_network.models import User, Post, Comment, Hashtag
from social_network.permissions import IsAuthorOrIfAuthenticatedReadOnly
from social_network.serializers import (
    UserSerializer,
    UserListSerializer,
    UserImageSerializer,
    PostSerializer,
    PostListSerializer,
    PostDetailSerializer,
    PostImageSerializer,
    CommentSerializer,
    HashtagSerializer,
    HashtagListSerializer,
    HashtagDetailSerializer,
)


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


class UserViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet,
):
    serializer_class = UserSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthorOrIfAuthenticatedReadOnly,)
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return UserListSerializer
        if self.action == "upload_image":
            return UserImageSerializer
        return self.serializer_class

    def get_queryset(self):
        last_name = self.request.query_params.get("last_name")

        queryset = self.queryset

        if last_name:
            queryset = queryset.filter(last_name__icontains=last_name)

        return queryset

    @action(
        methods=["POST"],
        detail=True,
        url_path="follow-unfollow",
        permission_classes=[IsAuthenticated],
    )
    def follow_unfollow(self, request, pk=None):
        """Endpoint for following/unfollowing certain user."""
        following = self.get_object()
        follower = self.request.user
        if following not in follower.followings.all():
            follower.followings.add(following)
            following.followers.add(follower)
        else:
            follower.followings.remove(following)
            following.followers.remove(follower)

        return Response(status=status.HTTP_200_OK)

    @action(
        methods=["GET"],
        detail=True,
        url_path="followings",
        permission_classes=[IsAuthenticated],
    )
    def followings(self, request, pk):
        """Endpoint to retrieve followings of certain user."""
        user = User.objects.get(id=pk)
        followings = user.followings.all()

        serializer = UserSerializer(followings, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=["GET"],
        detail=True,
        url_path="followers",
        permission_classes=[IsAuthenticated],
    )
    def followers(self, request, pk):
        """Endpoint to retrieve followers of certain user."""
        user = User.objects.get(id=pk)
        followers = user.followers.all()

        serializer = UserSerializer(followers, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=["GET"],
        detail=True,
        url_path="published-posts",
        permission_classes=[IsAuthenticated],
    )
    def published_posts(self, request, pk):
        """Endpoint to retrieve published posts of certain user."""
        user = User.objects.get(id=pk)
        posts = user.posts.filter(published=True)

        serializer = PostSerializer(posts, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=["GET"],
        detail=True,
        url_path="liked-posts",
        permission_classes=[IsAuthenticated],
    )
    def liked_posts(self, request, pk):
        """Endpoint to retrieve a post that was liked by current user."""
        user = self.request.user
        liked_posts = user.post_like.all()

        serializer = PostSerializer(liked_posts, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAuthenticated],
    )
    def upload_image(self, request, pk=None):
        """Endpoint for uploading profile picture to current user."""
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class HashtagViewSet(
    generics.ListCreateAPIView,
    mixins.UpdateModelMixin,
    generics.RetrieveAPIView,
    viewsets.GenericViewSet
):
    serializer_class = HashtagSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    queryset = Hashtag.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return HashtagListSerializer
        if self.action == "retrieve":
            return HashtagDetailSerializer
        return self.serializer_class


class PostViewSet(ModelViewSet):
    serializer_class = PostSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (
        IsAuthenticated,
        IsAuthorOrIfAuthenticatedReadOnly,
    )
    queryset = Post.objects.all()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        user = self.request.user
        user_followings = user.followings.all()
        queryset = self.queryset.filter(
            Q(author=user) | Q(author__in=user_followings)
        ).filter(published=True)

        hashtag = self.request.query_params.get("hashtag")
        title = self.request.query_params.get("title")
        author_last_name = self.request.query_params.get("author_last_name")

        if hashtag:
            queryset = queryset.filter(hashtags__name__icontains=hashtag)

        if title:
            queryset = queryset.filter(title__icontains=title)

        if author_last_name:
            queryset = queryset.filter(
                author__last_name__icontains=author_last_name
            )

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return PostListSerializer
        if self.action == "retrieve":
            return PostDetailSerializer
        if self.action == "upload_image":
            return PostImageSerializer
        return self.serializer_class

    @action(
        methods=["POST"],
        detail=True,
        url_path="like-unlike",
        permission_classes=[IsAuthenticated],
    )
    def like(self, request, pk=None):
        """Endpoint for liking/unliking certain post."""
        post = self.get_object()
        serializer = PostSerializer(post)

        if post.likes.filter(id=request.user.id).exists():
            post.likes.remove(request.user)
        else:
            post.likes.add(request.user)

        post.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAuthenticated],
    )
    def upload_image(self, request, pk=None):
        """Endpoint for uploading an image to certain post."""
        post = self.get_object()
        serializer = self.get_serializer(post, data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class CommentViewSet(ModelViewSet):
    serializer_class = CommentSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthorOrIfAuthenticatedReadOnly,)
    queryset = Comment.objects.all()

    def get_queryset(self):
        queryset = Comment.objects.all()
        if self.action in ["retrieve", "list"]:
            post_id = self.request.query_params.get("post_id")
            queryset = queryset.filter(post__id=post_id)

            return queryset

        return queryset

    def perform_create(self, serializer):
        post_id = self.request.query_params.get("post_id")
        serializer.save(
            author=self.request.user, post=Post.objects.get(id=post_id)
        )
