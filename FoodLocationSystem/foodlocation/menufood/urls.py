from django.urls import path, include, re_path
from rest_framework import routers
from . import views
from .admin import admin_site

router = routers.DefaultRouter()
router.register('tags', views.TagViewSet, basename='tag')
router.register('foods', views.FoodViewSet, basename='food')
router.register('users', views.UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('admin/', admin_site.urls),
]
