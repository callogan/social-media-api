from django.urls import path, include
from rest_framework import routers

from social_network.views import (
    UserViewSet,
    CreateUserView,
    PostViewSet,
    CommentViewSet,
)

router = routers.DefaultRouter()
router.register("users", UserViewSet)
router.register("posts", PostViewSet)
router.register("comments", CommentViewSet)

comment_list = CommentViewSet.as_view(
    actions={"get": "list", "post": "create"}
)

urlpatterns = [
    path("users/register/", CreateUserView.as_view(), name="user-create"),
    path(
        "posts/<int:pk>/comments/",
        comment_list,
        name="comment-post"
    ),
] + router.urls

app_name = "social_network"
