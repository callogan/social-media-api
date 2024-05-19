from django.urls import path, include
from rest_framework import routers
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from social_network.views import (
    UserViewSet,
    CreateUserView,
    PostViewSet,
    CommentViewSet,
    HashtagViewSet,
)

router = routers.DefaultRouter()
router.register("users", UserViewSet)
router.register("posts", PostViewSet)
router.register("comments", CommentViewSet)
router.register("hashtags", HashtagViewSet)

comment_list = CommentViewSet.as_view(
    actions={"get": "list", "post": "create"}
)

urlpatterns = [
    path(
        "users/register/",
        CreateUserView.as_view(),
        name="user-create"
    ),
    path(
        "users/login/",
        TokenObtainPairView.as_view(),
        name="token-obtain-pair"
    ),
    path(
        "users/login/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh"
    ),
    path(
        "users/login/verify/",
        TokenVerifyView.as_view(),
        name="token-verify"
    ),
    path(
        "posts/<int:pk>/comments/",
        comment_list,
        name="comment-post"
    ),
] + router.urls

app_name = "social_network"
