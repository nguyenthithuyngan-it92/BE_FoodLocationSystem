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
        menu_items = store.menuitem_store.filter(active=True).annotate(
            food_count=Count('menuitem_food'))

        kw = request.query_params.get('kw')
        if kw:
            menu_items = menu_items.filter(name__icontains=kw)

        return Response(MenuItemSerializer(menu_items, many=True).data, status=status.HTTP_200_OK)


class MenuItemViewSet(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView,
                      generics.CreateAPIView, generics.UpdateAPIView, generics.DestroyAPIView):
    serializer_class = MenuItemSerializer

    def get_queryset(self):
        menu = MenuItem.objects.filter(active=True).annotate(
            food_count=Count('menuitem_food')
        )

        kw = self.request.query_params.get('kw')
        if kw:
            menu = menu.filter(name__icontains=kw)

        return menu

    def get_permissions(self):
        if self.action in ['create', 'update', 'delete', 'destroy', 'set_status_menu']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    # tạo menu cho từng cửa hàng đăng nhập vào
    def create(self, request):
        # Lấy thông tin người dùng và kiểm tra quyền truy cập của người dùng
        user = request.user
        if user.user_role != User.STORE or user.is_active == 0 or user.is_superuser == 1 or user.is_staff == 1:
            return Response({"message": f"Bạn không có quyền thực hiện chức năng này!"},
                            status=status.HTTP_403_FORBIDDEN)
        if user.is_verify != 1:
            return Response({"message": f"Tài khoản cửa hàng {user.name_store} chưa được chứng thực để thực hiện chức năng thêm menu!"},
                            status=status.HTTP_403_FORBIDDEN)

        name = request.data.get('name')

        if name:
            MenuItem.objects.create(name=name, active=True, store=request.user)
            return Response({"message": f"Lưu thông tin menu thành công cho cửa hàng {user.name_store}!", "data": request.data},
                            status=status.HTTP_201_CREATED)
        return Response({"message": "Lưu thông tin menu không thành công!"}, status=status.HTTP_400_BAD_REQUEST)

    # chỉnh sửa menu cho từng cửa hàng đăng nhập vào
    def update(self, request, pk):
        try:
            menu = MenuItem.objects.get(id=pk)
            # Lấy thông tin người dùng và kiểm tra quyền truy cập của người dùng
            user = request.user
            if user.user_role != User.STORE or user.is_active == 0 or user.is_superuser == 1 or user.is_staff == 1:
                return Response({"message": f"Bạn không có quyền thực hiện chức năng này!"},
                                status=status.HTTP_403_FORBIDDEN)
            if user.is_verify != 1:
                return Response({"message": f"Tài khoản cửa hàng {user.name_store} chưa được chứng thực để thực hiện chức năng chỉnh sửa menu!"},
                                status=status.HTTP_403_FORBIDDEN)
            if request.method == 'PUT':
                serializer = MenuItemSerializer(menu, data=request.data, partial=True)
                if serializer.is_valid():
                    if menu.store == user:
                        serializer.save()
                        return Response({"message": "Chỉnh sửa thông tin menu thành công!", "data": request.data},
                                        status=status.HTTP_200_OK)
                    return Response({"message": "Chỉnh sửa thông tin menu không thành công! Bạn không có quyền chỉnh sửa menu này"},
                                    status=status.HTTP_400_BAD_REQUEST)
            return Response({"message": "Chỉnh sửa thông tin menu không thành công!"},
                            status=status.HTTP_400_BAD_REQUEST)
        except MenuItem.DoesNotExist:
            return Response({'error': 'Không tìm thấy menu!'}, status=status.HTTP_404_NOT_FOUND)

    # xóa menu cho từng cửa hàng đăng nhập vào
    def destroy(self, request, *args, **kwargs):
        try:
            user = request.user
            if user == self.get_object().store:
                return super().destroy(request, *args, **kwargs)

            return Response({"message": f"Bạn không có quyền thực hiện chức năng này!"},
                            status=status.HTTP_403_FORBIDDEN)
        except MenuItem.DoesNotExist:
            return Response({'error': 'Không tìm thấy menu!'}, status=status.HTTP_404_NOT_FOUND)

    # lấy danh sách các món ăn của từng menu
    @action(methods=['get'], detail=True, url_path='foods')
    def get_list_foods(self, request, pk):
        menu = self.get_object()
        food = menu.menuitem_food.filter(active=True)

        kw = request.query_params.get('kw')
        if kw:
            food = food.filter(name__icontains=kw)

        return Response(FoodSerializer(food, many=True, context={'request': request}).data, status=status.HTTP_200_OK)

    # thiết lập trạng thái menu (active)
    @action(methods=['post'], detail=True, url_path='set-status-menu')
    def set_status_menu(self, request, pk):
        user = request.user
        if user.user_role != User.STORE or user.is_active == 0 or user.is_superuser == 1 or user.is_staff == 1:
            return Response({"message": "Bạn không có quyền thực hiện chức năng này."},
                            status=status.HTTP_403_FORBIDDEN)
        if user.is_verify != 1:
            return Response({"message": f"Tài khoản cửa hàng {user.name_store} chưa được chứng thực để thực hiện chức năng này!"},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            menu = MenuItem.objects.get(id=pk)
        except MenuItem.DoesNotExist:
            return Response({'message': f'Menu không được tìm thấy trong cửa hàng {user.name_store}!'},
                            status=status.HTTP_404_NOT_FOUND)

        if request.method == 'POST':
            if menu.store.id == user.id:
                if menu.active == 1:
                    menu.active = 0
                    menu.save()
                    return Response({'message': f'Menu {menu.name} đã được tắt trạng thái sẵn bán thành công!'},
                                    status=status.HTTP_200_OK)
                if menu.active == 0:
                    menu.active = 1
                    menu.save()
                    return Response({'message': f'Menu {menu.name} đã được bật trạng thái sẵn bán thành công!'},
                                    status=status.HTTP_200_OK)
            return Response({'message': f'Menu {menu.name} không thuộc quyền xử lý của bạn. Cập nhật không thành công!'},
                            status=status.HTTP_404_NOT_FOUND)

        return Response({'message': f'Menu {menu.name} cập nhật trạng thái không thành công. Vui lòng thử lại!'},
                        status=status.HTTP_404_NOT_FOUND)


class FoodStoreViewSet(viewsets.ViewSet, generics.CreateAPIView):
    serializer_class = FoodSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        # Lấy thông tin người dùng và kiểm tra quyền truy cập của người dùng
        user = request.user
        if user.user_role != User.STORE or user.is_active == 0 or user.is_superuser == 1 or user.is_staff == 1:
            return Response({"message": f"Bạn không có quyền thực hiện chức năng này!"},
                            status=status.HTTP_403_FORBIDDEN)
        if user.is_verify != 1:
            return Response({"message": f"Tài khoản cửa hàng {user.name_store} chưa được chứng thực để thực hiện chức năng thêm món ăn!"},
                            status=status.HTTP_403_FORBIDDEN)

        # Lấy MenuItem
        menu_item_id = request.data.get('menu_item')
        try:
            menu_item = MenuItem.objects.get(pk=menu_item_id, store=user)
        except MenuItem.DoesNotExist:
            return Response({"message": f"Không tìm thấy menu nào của cửa hàng {user.name_store}! Vui lòng tạo menu!"},
                            status=status.HTTP_404_NOT_FOUND)

        # Tạo Food
        name = request.data.get('name')
        price = request.data.get('price')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        description = request.data.get('description')
        image = request.data.get('image')

        if name != "" and price != "":
            food = Food.objects.create(name=name, active=True, price=price, description=description,
                                       start_time=start_time, end_time=end_time,
                                       image=image, menu_item=menu_item)
            
            # Gắn tag vào food
            tags = request.data.get("tags")
            if tags is not None:
                for tag in tags:
                    try:
                        tag = Tag.objects.get(id=tag['id'])
                    except Tag.DoesNotExist:
                        return Response({"message": f"Không tìm thấy tag!"},
                                        status=status.HTTP_404_NOT_FOUND)
                    food.tags.add(tag)

            return Response({"message": f"Lưu thông tin món ăn thành công cho cửa hàng {user.name_store}!"},
                            status=status.HTTP_201_CREATED)
        return Response({"message": "Lưu thông tin món ăn không thành công!"}, status=status.HTTP_400_BAD_REQUEST)

        # serializer = FoodSerializer(data=request.data)
        # if serializer.is_valid():
        #     food = serializer.save(menu_item=menu_item)
        #
        #     # Gắn tag vào food
        #     tags = request.data.get("tags")
        #     if tags is not None:
        #         for tag in tags:
        #             tags = Tag.objects.filter(pk__in=tag)
        #             food.tags.add(tags)
        #         food.save()
        #
        #     return Response(serializer.data,
        #                     {"message": "Lưu thông tin món ăn thành công!", "data": request.data},
        #                     status=status.HTTP_201_CREATED)
        #
        # return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrderViewSet(viewsets.ViewSet, generics.CreateAPIView, generics.RetrieveAPIView, generics.ListAPIView):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    # đặt món - tạo đơn hàng
    def create(self, request):
        # Lấy thông tin người dùng và kiểm tra quyền truy cập của người dùng
        user = request.user
        if user.user_role != User.USER or user.is_active == 0 or user.is_superuser == 1 or user.is_staff == 1:
            return Response({"message": "Bạn không có quyền thực hiện chức năng đặt món!"},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.is_valid():
            # Lưu thông tin đơn hàng
            order = serializer.save(order_status=Order.PENDING, user=request.user)

            # Lưu thông tin chi tiết đơn hàng
            order_details_data = request.data.pop('order_details')
            # kiểm tra thông tin món được đặt có hợp lệ
            for order_detail_data in order_details_data:
                food_id = order_detail_data.pop('food')
                food = Food.objects.get(id=food_id)
                if not food:
                    return Response({"message": "Món ăn nào được đặt không hợp lệ!"},
                                    status=status.HTTP_400_BAD_REQUEST)
                if food.active == 0:
                    return Response({"message": f"Món ăn {food.name} hiện tại không còn bán!"},
                                    status=status.HTTP_400_BAD_REQUEST)
                if food.menu_item.store != order.store:
                    OrderDetail.objects.filter(order_id=order.id).delete()
                    Order.objects.filter(id=order.id).delete()
                    return Response(
                        {"message": f"Món ăn {food.name} không có trong cửa hàng! Đặt hàng không thành công!"},
                        status=status.HTTP_400_BAD_REQUEST)

                OrderDetail.objects.create(order=order, food=food, **order_detail_data)

            headers = self.get_success_headers(serializer.data)
            return Response({"message": "Đặt hàng thành công!", "data": serializer.data},
                            status=status.HTTP_201_CREATED, headers=headers)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # xem chi tiết đơn hàng cho user
    def retrieve(self, request, pk):
        try:
            order = Order.objects.get(id=pk)
            user = request.user

            if user.user_role == User.STORE and order.store != user \
                    and order.user != user and user.user_role == User.USER:
                return Response({'error': 'Forbidden', 'message': 'Bạn không có quyền xem đơn hàng này!'},
                                status=status.HTTP_403_FORBIDDEN)

            data = {
                'id': order.id,
                'created_date': order.created_date,
                'amount': order.amount,
                'delivery_fee': order.delivery_fee,
                'order_status': order.order_status,
                'receiver_name': order.receiver_name,
                'receiver_phone': order.receiver_phone,
                'receiver_address': order.receiver_address,
                'payment_date': order.payment_date,
                'payment_status': order.payment_status,
                'paymentmethod': order.paymentmethod.name,
                'user': order.user.id,
                'store': order.store.id,
                'order_details': []
            }

            for order_detail in order.orderdetail_set.all():
                order_detail_data = {
                    'unit_price': order_detail.unit_price,
                    'quantity': order_detail.quantity,
                    'food': {
                        'id': order_detail.food.id,
                        'name': order_detail.food.name,
                        'price': order_detail.food.price,
                        'menu_item': order_detail.food.menu_item.name,
                    }
                }

                data['order_details'].append(order_detail_data)

            return Response(data, status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            return Response({'error': 'Không tìm thấy đơn hàng!'}, status=status.HTTP_404_NOT_FOUND)

    # lấy thông tin các đơn hàng của user
    def list(self, request):
        try:
            user = request.user
            orders = Order.objects.all()
            if user.user_role == User.STORE:
                orders = orders.filter(store=user.id)
            elif user.user_role == User.USER:
                orders = orders.filter(user=user.id)
            else:
                return Response({'error': 'Forbidden', 'message': 'Bạn không có quyền thực hiện chức năng này!'},
                                status=status.HTTP_403_FORBIDDEN)

            return Response(OrderSerializer(orders, many=True).data, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({'error': 'Bạn không có đơn hàng nào!'}, status=status.HTTP_404_NOT_FOUND)

    # lấy danh sách các hóa đơn chưa được xác nhận cho cửa hàng
    @action(methods=['get'], detail=False, url_path='pending-order')
    def get_list_pending(self, request):
        user = self.request.user
        if user.user_role != User.STORE or user.is_active == 0 or user.is_superuser == 1 or user.is_staff == 1:
            return Response({"message": "Bạn không có quyền thực hiện chức năng này.",
                             "statusCode": status.HTTP_403_FORBIDDEN},
                            status=status.HTTP_403_FORBIDDEN)

        # Lấy danh sách các đơn hàng có trạng thái 'PENDING'
        orders = Order.objects.filter(order_status=Order.PENDING, store=user.id).exclude(user__user_role=User.STORE) \
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
            for store in stores:
                orders_dict[store.id] = {
                    'store': store.id,
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
                    'store_id': order.store.id,
                    'store_name': order.store.name_store,
                    'order_details': []
                }

                # Thêm thông tin các order_detail vào đơn hàng
                for order_detail in order_details.filter(order=order):
                    food = foods.get(id=order_detail.food_id)
                    menu_item = menu_items.get(id=food.menu_item_id)
                    # store = stores.get(id=menu_item.store_id)

                    order_detail_dict = {
                        'food_id': food.id,
                        'food_name': food.name,
                        'menu_item_id': menu_item.id,
                        'menu_item_name': menu_item.name,
                        'unit_price': order_detail.unit_price,
                        'quantity': order_detail.quantity
                    }
                    # if store.id == user.id:
                    order_dict['order_details'].append(order_detail_dict)

                # if store.id == user.id:
                orders_dict[store.id]['orders'].append(order_dict)

            if not list(orders_dict.values()):
                return Response({"message": f"Không có đơn hàng cần xác nhận của cửa hàng {user.name_store}.",
                                 "statusCode": status.HTTP_404_NOT_FOUND},
                                status=status.HTTP_404_NOT_FOUND)

            return Response({"message": f"Danh sách đơn hàng cần xác nhận của cửa hàng {user.name_store}",
                             "statusCode": status.HTTP_200_OK, "data": list(orders_dict.values())},
                            status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            return Response({"message": f"Không có đơn hàng cần xác nhận của cửa hàng {user.name_store}.",
                             "statusCode": status.HTTP_404_NOT_FOUND},
                            status=status.HTTP_404_NOT_FOUND)

    # xác nhận đơn hàng - order_status=ACCEPTED
    @action(methods=['post'], detail=True, url_path='confirm-order')
    def confirm_order(self, request, pk):
        user = request.user
        if user.user_role != User.STORE or user.is_active == 0 or user.is_superuser == 1 or user.is_staff == 1:
            return Response({"message": "Bạn không có quyền thực hiện chức năng này."},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            order = Order.objects.get(id=pk)
        except Order.DoesNotExist:
            return Response({'message': f'Đơn hàng không được tìm thấy hoặc đã được xử lý!'},
                            status=status.HTTP_404_NOT_FOUND)

        if request.method == 'POST':
            if order.store.id == user.id:
                if order.order_status == Order.PENDING:
                    order.order_status = Order.ACCEPTED
                    order.save()
                    return Response({'message': f'Đơn hàng {pk} đã được xác nhận thành công!'},
                                    status=status.HTTP_200_OK)
            return Response({'message': f'Đơn hàng {pk} không thuộc quyền xử lý của bạn. Cập nhật không thành công!'},
                            status=status.HTTP_404_NOT_FOUND)

        return Response({'message': f'Đơn hàng {pk} xác nhận không thành công. Vui lòng thử lại!'},
                        status=status.HTTP_404_NOT_FOUND)

    @action(methods=['get'], detail=False, url_path='accepted-order')
    def get_list_accepted(self, request):
        user = self.request.user
        if user.user_role != User.STORE or user.is_active == 0 or user.is_superuser == 1 or user.is_staff == 1:
            return Response({"message": "Bạn không có quyền thực hiện chức năng này.",
                             "statusCode": status.HTTP_403_FORBIDDEN},
                            status=status.HTTP_403_FORBIDDEN)

        # Lấy danh sách các đơn hàng có trạng thái 'ACCEPTED'
        orders = Order.objects.filter(order_status=Order.ACCEPTED, store=user.id).exclude(user__user_role=User.STORE) \
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
            for store in stores:
                orders_dict[store.id] = {
                    'store': store.id,
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
                    'store_id': order.store.id,
                    'store_name': order.store.name_store,
                    'order_details': []
                }

                # Thêm thông tin các order_detail vào đơn hàng
                for order_detail in order_details.filter(order=order):
                    food = foods.get(id=order_detail.food_id)
                    menu_item = menu_items.get(id=food.menu_item_id)
                    # store = stores.get(id=menu_item.store_id)

                    order_detail_dict = {
                        'food_id': food.id,
                        'food_name': food.name,
                        'menu_item_id': menu_item.id,
                        'menu_item_name': menu_item.name,
                        'unit_price': order_detail.unit_price,
                        'quantity': order_detail.quantity
                    }
                    # if store.id == user.id:
                    order_dict['order_details'].append(order_detail_dict)

                # if store.id == user.id:
                orders_dict[store.id]['orders'].append(order_dict)

            if not list(orders_dict.values()):
                return Response({"message": f"Không có đơn hàng nào đang được giao của cửa hàng {user.name_store}.",
                                 "statusCode": status.HTTP_404_NOT_FOUND},
                                status=status.HTTP_404_NOT_FOUND)

            return Response({"message": f"Danh sách đơn hàng đang được giao của cửa hàng {user.name_store}",
                             "statusCode": status.HTTP_200_OK, "data": list(orders_dict.values())},
                            status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            return Response({"message": f"Không có đơn hàng nào đang được giao của cửa hàng {user.name_store}.",
                             "statusCode": status.HTTP_404_NOT_FOUND},
                            status=status.HTTP_404_NOT_FOUND)

    # xác nhận đơn hàng giao thành công - order_status=SUCCESSED
    @action(methods=['post'], detail=True, url_path='complete-order')
    def complete_order(self, request, pk):
        user = request.user
        if user.user_role != User.STORE or user.is_active == 0 or user.is_superuser == 1 or user.is_staff == 1:
            return Response({"message": "Bạn không có quyền thực hiện chức năng này."},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            order = Order.objects.get(id=pk)
        except Order.DoesNotExist:
            return Response({'message': f'Đơn hàng không được tìm thấy hoặc đã được xử lý!'},
                            status=status.HTTP_404_NOT_FOUND)

        if request.method == 'POST':
            if order.store.id == user.id:
                if order.order_status == Order.ACCEPTED:
                    if order.payment_status == 0:
                        order.order_status = Order.SUCCESSED
                        order.payment_status = True
                        order.save()
                    return Response({'message': f'Đã xác nhận đơn hàng {pk} giao hàng thành công!'},
                                    status=status.HTTP_200_OK)
            return Response({'message': f'Đơn hàng {pk} không thuộc quyền xử lý của bạn. Cập nhật không thành công!'},
                            status=status.HTTP_404_NOT_FOUND)

        return Response({'message': f'Đơn hàng {pk} xác nhận không thành công. Vui lòng thử lại!'},
                        status=status.HTTP_404_NOT_FOUND)


class OrderDetailViewSet(viewsets.ViewSet, generics.RetrieveUpdateDestroyAPIView):
    queryset = OrderDetail.objects.all()
    serializer_class = OrderDetailSerializer
    lookup_field = 'id'
