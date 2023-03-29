from rest_framework import viewsets, permissions, generics, parsers, status
from rest_framework.decorators import action
from rest_framework.views import Response
from .models import Food, User, MenuItem
from .serializers import FoodSerializer, UserSerializer, StoreSerializer, MenuItemSerializer, FoodDetailsSerializer
from .paginators import StorePaginator


class FoodViewSet(viewsets.ViewSet, generics.RetrieveAPIView, generics.ListAPIView):
    queryset = Food.objects.filter(active=True)
    serializer_class = FoodDetailsSerializer


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
    queryset = User.objects.filter(is_active=True, is_verify=True)
    serializer_class = StoreSerializer
    pagination_class = StorePaginator

    def get_queryset(self):
        q = self.queryset

        kw = self.request.query_params.get('kw')
        if kw:
            q = q.filter(name_store__icontains=kw)

        return q

    @action(methods=['get'], detail=True, url_path='menu-item')
    def get_menu_item(self, request, pk):
        store = self.get_object()
        menu_item = store.menuitem_store.filter(active=True)

        kw = request.query_params.get('kw')
        if kw:
            menu_item = menu_item.filter(name__icontains=kw)

        return Response(MenuItemSerializer(menu_item, many=True).data, status=status.HTTP_200_OK)


class MenuItemViewSet(viewsets.ViewSet, generics.ListAPIView):
    queryset = MenuItem.objects.filter(active=True)
    serializer_class = MenuItemSerializer

    @action(methods=['get'], detail=True, url_path='foods')
    def get_list_foods(self, request, pk):
        menu = self.get_object()
        food = menu.menuitem_food.filter(active=True)

        kw = request.query_params.get('kw')
        if kw:
            food = food.filter(name__icontains=kw)

        return Response(FoodSerializer(food, many=True, context={'request': request}).data, status=status.HTTP_200_OK)

