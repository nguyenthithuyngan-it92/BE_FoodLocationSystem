from rest_framework import viewsets, permissions, generics, parsers, status
from rest_framework.decorators import action
from rest_framework.views import Response
from .models import Food, User, MenuItem, Order, OrderDetail, Tag
from .serializers import (
    UserSerializer, StoreSerializer,
    MenuItemSerializer, TagSerializers, FoodSerializer,
    OrderSerializer, OrderDetailSerializer
)

from . import paginators
from django.db.models import Count


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.filter(active=True)
    serializer_class = TagSerializers
    pagination_class = paginators.BaseCustomPaginator


class FoodViewSet(viewsets.ViewSet, generics.RetrieveAPIView, generics.ListAPIView):
    queryset = Food.objects.filter(active=True)
    serializer_class = FoodSerializer
    pagination_class = paginators.BaseCustomPaginator

    def get_queryset(self):
        q = self.queryset

        name = self.request.query_params.get('name')
        if name:
            q = q.filter(name__icontains=name)

        tags = self.request.query_params.get('tags')
        if tags:
            q = q.filter(tags=tags)

        price = self.request.query_params.get('price')
        if price:
            q = q.filter(price=price)

        # store_id = self.request.query_params.get('store_id')
        # if store_id:
        #     q = q.filter(store_id=store_id)

        return q


class UserViewSet(viewsets.ViewSet, generics.CreateAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    parser_classes = [parsers.MultiPartParser, ]

    def get_permissions(self):
        if self.action in ['current_user']:
            return [permissions.IsAuthenticated()]

        return [permissions.AllowAny()]

    # xem và chỉnh sửa thông tin user khi đã được xác thực
    @action(methods=['get', 'put'], detail=False, url_path='current-user')
    def current_user(self, request):
        u = request.user
        if request.method.__eq__('PUT'):
            for k, v in request.data.items():
                setattr(u, k, v)
            u.save()

        return Response(UserSerializer(u, context={'request': request}).data, status=status.HTTP_200_OK)


class StoreViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = User.objects.filter(is_active=True, is_verify=True, user_role=1)
    serializer_class = StoreSerializer
    pagination_class = paginators.StorePaginator

    def get_queryset(self):
        menu = self.queryset
        menu = menu.annotate(
            menu_count=Count('menuitem_store')
        )

        kw = self.request.query_params.get('kw')
        if kw:
            menu = menu.filter(name_store__icontains=kw)

        return menu

    @action(methods=['get'], detail=True, url_path='menu-item')
    def get_menu_item(self, request, pk):
        store = self.get_object()
        menu_item = store.menuitem_store.filter(active=True).annotate(
            food_count=Count('menuitem_food'))

        kw = request.query_params.get('kw')
        if kw:
            menu_item = menu_item.filter(name__icontains=kw)

        return Response(MenuItemSerializer(menu_item, many=True).data, status=status.HTTP_200_OK)


class MenuItemViewSet(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView):
    serializer_class = MenuItemSerializer

    def get_queryset(self):
        menu = MenuItem.objects.filter(active=True).annotate(
            food_count=Count('menuitem_food')
        )

        kw = self.request.query_params.get('kw')
        if kw:
            menu = menu.filter(name__icontains=kw)

        return menu

    @action(methods=['get'], detail=True, url_path='foods')
    def get_list_foods(self, request, pk):
        menu = self.get_object()
        food = menu.menuitem_food.filter(active=True)

        kw = request.query_params.get('kw')
        if kw:
            food = food.filter(name__icontains=kw)

        return Response(FoodSerializer(food, many=True, context={'request': request}).data, status=status.HTTP_200_OK)


class OrderViewSet(viewsets.ViewSet, generics.ListCreateAPIView, generics.RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.is_valid():
            # Lưu thông tin đơn hàng
            order = serializer.save(delivery_fee=15000, order_status=Order.PENDING)

            # Lưu thông tin chi tiết đơn hàng
            order_details_data = request.data.pop('order_details')
            for order_detail_data in order_details_data:
                food_id = order_detail_data.pop('food')
                food = Food.objects.get(id=food_id)
                OrderDetail.objects.create(order=order, food=food, **order_detail_data)

            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrderDetailViewSet(viewsets.ViewSet, generics.RetrieveUpdateDestroyAPIView):
    queryset = OrderDetail.objects.all()
    serializer_class = OrderDetailSerializer
    lookup_field = 'id'





