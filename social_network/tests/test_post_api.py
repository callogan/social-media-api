import tempfile

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from social_network.models import Post, post_image_file_path, Hashtag
from social_network.serializers import PostListSerializer


class UnauthenticatedPostApiTests(TestCase):
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

        url = reverse("social_network:post-detail", args=[post.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedPostApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test_user@test.com",
            password="testpass",
            first_name="Test",
            last_name="User"
        )
        refresh = RefreshToken.for_user(self.user)
        self.token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.post = Post.objects.create(
            author=self.user,
            title="Test post",
            content="Test post content"
        )

    def test_create_post(self):
        payload = {
            "author": self.user.id,
            "title": "Test post",
            "content": "Test post content",
            "published": True,
            "hashtags": [],
            "created_at": timezone.now()
        }
        create_url = reverse("social_network:post-list")
        resp = self.client.post(create_url, payload)

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        post = Post.objects.get(id=resp.data["id"])
        self.assertEqual(payload["title"], post.title)
        self.assertEqual(payload["author"], post.author.id)

    def test_get_post(self):
        user_url = reverse("social_network:post-detail", args=[self.post.id])
        resp = self.client.get(user_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_get_author_and_followers_posts_only(self):
        follower = get_user_model().objects.create_user(
            email="nicolas_satter@test.com",
            password="testpass1",
            first_name="Nicolas",
            last_name="Satter"
        )
        non_follower = get_user_model().objects.create_user(
            email="lucia_mattern@@test.com",
            password="testpass2",
            first_name="Lucia",
            last_name="Mattern"
        )
        self.user.followings.add(follower)

        follower_post = Post.objects.create(
            author=follower,
            title="Follower's post",
            content="Test post content 1"
        )
        follower_post.save()

        non_follower_post = Post.objects.create(
            author=non_follower,
            title="Non-follower's post",
            content="Test post content 2"
        )
        non_follower_post.save()

        url = reverse("social_network:post-list")
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        target_posts = [self.post, follower_post]
        serializer = PostListSerializer(target_posts, many=True)

        self.assertEqual(resp.data, serializer.data)

        post_ids_in_resp = [post["id"] for post in resp.data]

        self.assertNotIn(non_follower_post.id, post_ids_in_resp)

    def test_filter_by_hashtag(self):
        hashtag_names = {"economy", "innovations"}
        hashtags = {
            name: Hashtag.objects.create(name=name)
            for name in hashtag_names
        }

        post1 = Post.objects.create(
            author=self.user,
            title="Cycles",
            content="Economic cycles are imminent."
        )
        post2 = Post.objects.create(
            author=self.user,
            title="Markets",
            content="Markets are on a suspense."
        )
        post3 = Post.objects.create(
            author=self.user,
            title="Renewables",
            content="Green energy trends are dominating."
        )
        post4 = Post.objects.create(
            author=self.user,
            title="Automation",
            content="Robotic tools are being implemented widely."
        )

        post1.hashtags.add(hashtags["economy"])
        post2.hashtags.add(hashtags["economy"])

        economy_posts = {post1.pk, post2.pk}

        post1.hashtags.add(hashtags["innovations"])
        post3.hashtags.add(hashtags["innovations"])

        url = reverse("social_network:post-list")
        resp = self.client.get(url, {"hashtag": "economy"})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        self.assertEqual(set(p["id"] for p in resp.data), economy_posts)

        for post in resp.data:
            post_hashtags = set(post["hashtags"])
            self.assertTrue("economy" in post_hashtags)

    def test_filter_by_title(self):
        post1 = Post.objects.create(
            author=self.user,
            title="Management",
            content="Management content"
        )
        post2 = Post.objects.create(
            author=self.user,
            title="Manager",
            content="Manager content"
           )
        post3 = Post.objects.create(
            author=self.user,
            title="Hedge",
            content="Hedge content"
        )

        manage_posts = {post1.pk, post2.pk}

        url = reverse("social_network:post-list")
        resp = self.client.get(url, {"title": "manage"})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(set(p["id"] for p in resp.data), manage_posts)

        post_titles = [item["title"].lower() for item in resp.data]

        self.assertTrue(
            any(["manage" in t for t in post_titles])
        )

    def test_filter_by_author_last_name(self):
        user2 = get_user_model().objects.create_user(
            email="nick_larson@test.com",
            password="testpass1",
            first_name="Nick",
            last_name="Larson"
        )
        user3 = get_user_model().objects.create_user(
            email="william_jason@test.com",
            password="testpass2",
            first_name="William",
            last_name="Jason"
        )

        post1 = Post.objects.create(
            author=self.user,
            title="Test post 1",
            content="Economic growth is needed."
        )
        post2 = Post.objects.create(
            author=self.user,
            title="Test post 2",
            content="Stagflation is coming up."
        )
        post3 = Post.objects.create(
            author=self.user,
            title="Test post 3",
            content="Innovations are necessary."
        )
        post4 = Post.objects.create(
            author=self.user,
            title="Test post 4",
            content="Employment rate is surging."
        )

        self.user.followings.add(user2)
        self.user.followings.add(user3)

        target_posts = {post2.pk, post3.pk, post4.pk}

        url = reverse("social_network:post-list")
        resp = self.client.get(url, {"author_last_name": "son"})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(set(p["id"] for p in resp.data), target_posts)

        authors = [item["author"].lower() for item in resp.data]
        self.assertTrue(
            any(["son" in t for t in authors])
        )

    def test_like_post_if_not_liked(self):
        followed_user = get_user_model().objects.create_user(
            email="john_simmons@test.com",
            password="testpass"
        )
        post = Post.objects.create(
            author=followed_user,
            title="Test post",
            content="Test post content"
        )
        self.user.followings.add(followed_user)
        resp = self.client.post(
            reverse("social_network:post-detail", args=[post.id]) +
            "like-unlike/"
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn(self.user, post.likes.all())

    def test_unlike_post_if_liked(self):
        followed_user = get_user_model().objects.create_user(
            email="john_simmons@test.com",
            password="testpass"
        )
        post = Post.objects.create(
            author=followed_user,
            title="Test post",
            content="Test post content"
        )
        self.user.followings.add(followed_user)
        post.likes.add(self.user)

        resp = self.client.post(
            reverse("social_network:post-detail", args=[post.id]) +
            "like-unlike/"
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.user, post.likes.all())

    def test_upload_image_to_post(self):
        url = (
                reverse(
                    "social_network:post-upload-image", args=[self.post.id]
                )
        )

        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            resp = self.client.post(url, {"image": ntf}, format="multipart")

        self.post.refresh_from_db()

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("image", resp.data)

        uploaded_image = self.post.image
        self.assertTrue(uploaded_image.file)

    def test_post_image_file_path(self):
        filename = "test_image.jpg"
        result_path = post_image_file_path(self.post, filename)

        self.assertTrue(slugify(self.post.title) in result_path)

        uuid_part = result_path.split(
            slugify(self.post.title)
        )[1].split(".jpg")[0]

        self.assertEqual(len(uuid_part), 37)
        self.assertTrue(
            all(
                c.isdigit() or c.isalpha() or c in "-_" for c in uuid_part
            )
        )
        self.assertTrue(slugify(self.post.title) in result_path)

    def test_update_post(self):
        payload = {"content": "New content text", "published": True}

        resp = self.client.patch(
            reverse("social_network:post-detail", args=[self.post.id]),
            data=payload,
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        updated_post = Post.objects.get(id=self.post.id)

        self.assertEqual(updated_post.content, payload["content"])

    def test_delete_post(self):
        comment = Post.objects.create(
            author=self.user,
            title="Test post",
            content="Test post content"
        )
        resp = self.client.delete(
            reverse("social_network:post-detail", args=[comment.id]),
        )

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
