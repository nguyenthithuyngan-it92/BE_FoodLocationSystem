from django.urls import path, include, re_path
from rest_framework import routers
from . import views
from .admin import admin_site

router = routers.DefaultRouter()
router.register('tags', views.TagViewSet, basename='tag')
router.register('foods', views.FoodViewSet, basename='food')
router.register('users', views.UserViewSet, basename='user')
router.register('stores', views.StoreViewSet, basename='store')
router.register('menu-items', views.MenuItemViewSet, basename='menu-item')
router.register('orders', views.OrderViewSet, basename='order')
router.register('order-details', views.OrderDetailViewSet, basename='order-details')
router.register('comments', views.CommentViewSet, basename='comment')
router.register('subcribes', views.SubcribeViewSet, basename='subcribe')
router.register('food-store', views.FoodStoreViewSet, basename='food-store')
router.register('food-list', views.FoodByStoreViewSet, basename='food-list')

urlpatterns = [
    path('', include(router.urls)),
    path('admin/', admin_site.urls),
]
