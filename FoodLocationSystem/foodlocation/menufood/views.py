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


class OrderViewSet(viewsets.ViewSet, generics.CreateAPIView, generics.RetrieveAPIView, generics.ListAPIView):
    serializer_class = OrderSerializer
    # queryset = Order.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    # đặt món - tạo đơn hàng
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.is_valid():
            # Lưu thông tin đơn hàng
            order = serializer.save(delivery_fee=15000, order_status=Order.PENDING, user=request.user)

            # Lưu thông tin chi tiết đơn hàng
            order_details_data = request.data.pop('order_details')
            for order_detail_data in order_details_data:
                food_id = order_detail_data.pop('food')
                food = Food.objects.get(id=food_id)
                OrderDetail.objects.create(order=order, food=food, **order_detail_data)

            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # lấy danh sách các hóa đơn chưa được xác nhận cho cửa hàng
    @action(methods=['get'], detail=False, url_path='pedding-order')
    def get_list_pedding(self, request):
        user = self.request.user
        if user.user_role != User.STORE:
            return Response({'error': 'User is not a store'})

        # Lấy danh sách các đơn hàng có trạng thái 'PENDING' và không có trường store_id
        orders = Order.objects.filter(order_status=Order.PENDING).exclude(user__user_role=User.STORE)\
                                .select_related('paymentmethod', 'user')

        # Lấy các order_detail của các đơn hàng
        order_details = OrderDetail.objects.filter(order__in=orders).select_related('food')

        # Lấy các món ăn của các order_detail
        foods = Food.objects.filter(id__in=order_details.values_list('food_id', flat=True)).select_related('menu_item')

        # Lấy các menu item của các món ăn
        menu_items = MenuItem.objects.filter(id__in=foods.values_list('menu_item_id', flat=True))

        # Lấy các cửa hàng của các menu item
        stores = User.objects.filter(id__in=menu_items.values_list('store_id', flat=True))

        # Tạo dictionary để lưu thông tin đơn hàng của từng cửa hàng
        orders_dict = {}
        try:
            # if stores.get('name_store') == user.name_store:
            for store in stores:
                if store.id == user.id:
                    orders_dict[store.id] = {
                        'store_id': store.id,
                        'store_name': store.name_store,
                        'orders': []
                    }

            # Đổ dữ liệu đơn hàng vào các store tương ứng
            for order in orders:
                order_dict = {
                    'id': order.id,
                    'amount': order.amount,
                    'delivery_fee': order.delivery_fee,
                    'receiver_name': order.receiver_name,
                    'receiver_phone': order.receiver_phone,
                    'receiver_address': order.receiver_address,
                    'created_date': order.created_date,
                    'payment_status': order.payment_status,
                    'payment_method': order.paymentmethod.name,
                    'user_id': order.user.id,
                    'user_name': order.user.username,
                    'order_details': []
                }

                # Thêm thông tin các order_detail vào đơn hàng
                for order_detail in order_details.filter(order=order):
                    food = foods.get(id=order_detail.food_id)
                    menu_item = menu_items.get(id=food.menu_item_id)
                    store = stores.get(id=menu_item.store_id)

                    order_detail_dict = {
                        'food_id': food.id,
                        'food_name': food.name,
                        'menu_item_id': menu_item.id,
                        'menu_item_name': menu_item.name,
                        'store_id': store.id,
                        'store_name': store.name_store,
                        'unit_price': order_detail.unit_price,
                        'quantity': order_detail.quantity
                    }
                    if store.id == user.id:
                        order_dict['order_details'].append(order_detail_dict)

                if store.id == user.id:
                    orders_dict[store.id]['orders'].append(order_dict)

            return Response(list(orders_dict.values()))
        except Order.DoesNotExist:
             return Response(status=status.HTTP_404_NOT_FOUND, data={'message': 'Không tìm thấy đơn hàng nào'})

    # def get_queryset(self):
    #     user = self.request.user
    #     if user.user_role == User.STORE:
    #         return Order.objects.filter(order_status=Order.PENDING)
    #     return Order.objects.none()
    #
    # def list(self, request, *args, **kwargs):
    #     queryset = self.get_queryset()
    #     serializer = self.get_serializer(queryset, many=True)
    #     return Response(serializer.data)


    # @action(methods=['post'], detail=True, url_path='confirm-order')
    # def confirm_order(self, request, pk):
    #     user = request.user
    #     if user.user_role != User.STORE:
    #         return Response({"message": "Bạn không có quyền thực hiện chức năng này."},
    #                         status=status.HTTP_403_FORBIDDEN)
    #
    #     order_id = request.data.get('order_id')
    #     try:
    #         order = Order.objects.get(pk=order_id, order_status=Order.PENDING)
    #     except Order.DoesNotExist:
    #         return Response({"message": "Không tìm thấy đơn hàng cần xác nhận hoặc đơn hàng đã được xử lý."},
    #                         status=status.HTTP_404_NOT_FOUND)
    #
    #     store = MenuItem.objects.filter(store=user, menuitem_food__food=order.orderdetail_set.first().food).first()
    #     if not store:
    #         return Response({"message": "Đơn hàng này không thuộc quyền quản lý của bạn."},
    #                         status=status.HTTP_403_FORBIDDEN)
    #
    #     order.order_status = Order.ACCEPTED
    #     order.save()
    #     return Response({"message": "Xác nhận đơn hàng thành công."}, status=status.HTTP_200_OK)

        # try:
        #     order = Order.objects.get(pk)
        #     if request.method.__eq__('PATCH'):
        #         order.order_status = Order.ACCEPTED
        #         order.save()
        #         return Response({'message': f'Đơn hàng {pk} đã được xác nhận thành công!'}, status=status.HTTP_200_OK)
        # except Order.DoesNotExist:
        #     return Response(status=status.HTTP_404_NOT_FOUND)
        #
        # return Response(status=status.HTTP_404_NOT_FOUND, data={'message': f'Đơn hàng {pk} chưa được xác nhận. Vui lòng thử lại!'})


class OrderDetailViewSet(viewsets.ViewSet, generics.RetrieveUpdateDestroyAPIView):
    queryset = OrderDetail.objects.all()
    serializer_class = OrderDetailSerializer
    lookup_field = 'id'







