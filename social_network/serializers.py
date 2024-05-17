from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from social_network.models import Post, Comment


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "password",
            "is_staff",
            "followers",
            "followings",
            "profile_picture",
            "bio"
        )
        read_only_fields = ("is_staff",)
        extra_kwargs = {"password": {"write_only": True, "min_length": 8}}

    def create(self, validated_data):
        return get_user_model().objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()

        return user


class UserListSerializer(UserSerializer):
    followers = serializers.IntegerField(
        source="followers.count", read_only=True
    )
    followings = serializers.IntegerField(
        source="followings.count", read_only=True
    )
    posts = serializers.IntegerField(source="posts.count", read_only=True)

    class Meta:
        model = get_user_model()
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "posts",
            "followers",
            "followings"
        )


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()

    class Meta:
        model = Comment
        fields = ("id", "author", "created_at", "content")
        read_only_fields = ("created_at",)


class PostSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M")
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "author",
            "content",
            "created_at",
            "published",
            "publish_time",
            "comments"
        )
        read_only_fields = ("id", "author", "likes")

    def validate(self, data):
        if not data.get("published") and data.get("publish_time") is None:
            raise ValidationError("Enter the publication date")
        return data


class PostListSerializer(PostSerializer):
    author = serializers.SlugRelatedField(
        slug_field="last_name", read_only=True
    )
    likes = serializers.IntegerField(source="likes.count", read_only=True)
    is_liked = serializers.BooleanField(read_only=True)
    comments = serializers.IntegerField(
        source="comments.count", read_only=True
    )

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "author",
            "published",
            "publish_time",
            "likes",
            "comments",
            "is_liked"
        )


class PostDetailSerializer(PostSerializer):
    author = UserListSerializer(many=False, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    likes = serializers.IntegerField(source="likes.count", read_only=True)

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "content",
            "author",
            "created_at",
            "likes",
            "comments"
        )
