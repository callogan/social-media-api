import tempfile

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.text import slugify

from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from social_network.models import Post, user_image_file_path
from social_network.serializers import UserSerializer, PostSerializer


class UnauthenticatedUserApiTests(TestCase):
    def test_auth_required(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test_user@test.com",
            "testpass"
        )

        user_url = reverse("social_network:user-detail", args=[self.user.id])
        resp = self.client.get(user_url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_user(self):
        payload = {
            "email": "test_user@test.com",
            "password": "testpass",
            "bio": "Test bio"
        }
        create_url = reverse("social_network:user-create")
        resp = self.client.post(create_url, payload)

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(id=resp.data["id"])
        for key in payload.keys():
            if key != "password":
                self.assertEqual(payload[key], getattr(user, key))


class AuthenticatedUserApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="greta_grundig@test.com",
            password="testpass",
            first_name="Greta",
            last_name="Grundig"
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_get_user(self):
        user_url = reverse("social_network:user-detail", args=[self.user.id])
        resp = self.client.get(user_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_search_user_by_last_name(self):
        target_user = get_user_model().objects.get(last_name="Grundig")
        resp = self.client.get(
            reverse("social_network:user-list"),
            {"last_name": target_user.last_name}
        )
        self.assertIn(resp.data[0]["last_name"], target_user.last_name)

    def test_add_user_to_following(self):
        followed_user = get_user_model().objects.create_user(
            email="brigham_young@test.com",
            password="testpass",
            first_name="Brigham",
            last_name="Young"
        )

        resp = self.client.post(
            reverse("social_network:user-detail", args=[followed_user.id])
            + "follow-unfollow/"
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(
            self.user.followings.filter(id=followed_user.id).exists()
        )

    def test_remove_user_from_followings(self):
        followed_user = get_user_model().objects.create_user(
            email="bryan_griffin@test.com",
            password="testpass",
            first_name="Bryan",
            last_name="Griffin"
        )
        self.user.followings.add(followed_user)

        resp = self.client.post(
            reverse("social_network:user-detail", args=[followed_user.id]) +
            "follow-unfollow/"
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(
            self.user.followings.filter(id=followed_user.id).exists()
        )

    def test_list_followings(self):
        brian_griffin = get_user_model().objects.create_user(
            email="jessica_simmons@test.com",
            password="testpass1",
            first_name="Jessica",
            last_name="Simmons"
        )

        lisa_simpson = get_user_model().objects.create_user(
            email="scarlette_kindey@@test.com",
            password="testpass2",
            first_name="Scarlette",
            last_name="Kindey"
        )

        brian_griffin.followings.add(self.user)
        lisa_simpson.followings.add(self.user)

        resp = self.client.get(
            reverse("social_network:user-detail", args=[self.user.id]) +
            "followers/"
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        serializer = UserSerializer(self.user.followers.all(), many=True)

        self.assertEqual(resp.data, serializer.data)

    def test_liked_posts_list(self):
        bryan_griffin = get_user_model().objects.create_user(
            email="bryan_griffin@test.com",
            password="testpass",
            first_name="Bryan",
            last_name="Griffin"
        )

        first_post = Post.objects.create(
            author=bryan_griffin,
            title="First_post",
            content="Some content 1"
        )
        second_post = Post.objects.create(
            author=bryan_griffin,
            title="Second_post",
            content="Some content 2"
        )
        first_post.likes.add(self.user)
        second_post.likes.add(self.user)

        resp = self.client.get(
            reverse("social_network:user-detail", args=[self.user.id]) +
            "liked-posts/"
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        serializer = PostSerializer(self.user.post_like.all(), many=True)

        self.assertEqual(resp.data, serializer.data)

    def test_upload_image_to_user(self):
        url = (
            reverse("social_network:user-upload-image", args=[self.user.id])
        )

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            resp = self.client.post(url, {"image": ntf}, format="multipart")

        self.user.refresh_from_db()

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("image", resp.data)

        uploaded_image = self.user.image

        self.assertTrue(uploaded_image.file)

    def test_user_image_file_path(self):
        filename = "test_image.jpg"
        result_path = user_image_file_path(self.user, filename)

        self.assertTrue(slugify(self.user.last_name) in result_path)

        uuid_part = result_path.split(
            slugify(self.user.last_name)
        )[1].split(".jpg")[0]

        self.assertEqual(len(uuid_part), 37)
        self.assertTrue(
            all(
                c.isdigit() or c.isalpha() or c in "-_" for c in uuid_part
            )
        )
        self.assertTrue(slugify(self.user.last_name) in result_path)

    def test_update_user(self):
        payload = {"email": "greta_watson@test.com", "last_name": "Watson"}

        resp = self.client.patch(
            reverse("social_network:user-detail", args=[self.user.id]),
            data=payload,
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        updated_user = get_user_model().objects.get(id=self.user.id)

        self.assertEqual(updated_user.email, payload["email"])
        self.assertEqual(updated_user.last_name, payload["last_name"])

    def test_delete_user(self):
        resp = self.client.delete(
            reverse("social_network:user-detail", args=[self.user.id]),
        )

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
