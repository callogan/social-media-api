from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from social_network.models import Post, Comment
from social_network.serializers import CommentSerializer


class UnauthenticatedCommentApiTests(TestCase):
    def test_auth_required(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test_user@test.com",
            "testpass"
        )

        post = Post.objects.create(
            author=self.user,
            title="Test post",
            content="Test post content"
        )

        comment = Comment.objects.create(
            author=self.user,
            post=post,
            content="Test comment content"
        )

        url = reverse("social_network:comment-detail", args=[comment.id])
        resp = self.client.get(url, {"post_id": post.id})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCommentApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="john_simmons@test.com",
            password="testpass",
            first_name="John",
            last_name="Simmmons"
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.post = Post.objects.create(
            author=self.user,
            title="Test post",
            content="Test post content"
        )

    def test_create_comment(self):
        payload = {
            "content": "Test comment content"
        }
        create_url = (
            reverse("social_network:comment-list") + f"?post_id={self.post.id}"
        )
        resp = self.client.post(create_url, payload)

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        comment = Comment.objects.get(id=resp.data["id"])
        self.assertEqual(payload["content"], comment.content)

    def test_get_comment_detail(self):
        comment = Comment.objects.create(
            author=self.user,
            post=self.post,
            content="Comment #5"
        )
        comments_url = reverse("social_network:comment-list")
        resp = self.client.get(comments_url, {"post_id": {self.post.id}})
        serializer = CommentSerializer(comment)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data[0], serializer.data)

    def test_get_comment_list(self):
        comment_number = 3
        for num in range(comment_number):
            Comment.objects.create(
                author=self.user,
                post=self.post,
                content=f"Comment #{num}"
            )
        comments_url = reverse("social_network:comment-list")
        resp = self.client.get(comments_url, {"post_id": {self.post.id}})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), comment_number)

        comments = Comment.objects.all()
        serializer = CommentSerializer(comments, many=True)

        self.assertEqual(resp.data, serializer.data)

    def test_update_comment(self):
        comment = Comment.objects.create(
            author=self.user,
            post=self.post,
            content="Test comment content"
        )
        payload = {
            "content": "Some changes"
        }

        resp = self.client.patch(
            reverse("social_network:comment-detail", args=[comment.id]),
            data=payload
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        updated_comment = Comment.objects.get(id=comment.id)

        self.assertEqual(updated_comment.content, payload["content"])

    def test_delete_comment(self):
        comment = Comment.objects.create(
            author=self.user,
            post=self.post,
            content="Test comment content"
        )
        resp = self.client.delete(
            reverse("social_network:comment-detail", args=[comment.id]),
        )

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
