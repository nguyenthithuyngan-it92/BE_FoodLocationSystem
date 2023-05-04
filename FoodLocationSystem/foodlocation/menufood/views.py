import calendar

from rest_framework import viewsets, permissions, generics, parsers, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import action, permission_classes
from rest_framework.views import Response, APIView
from .models import Food, User, MenuItem, Order, OrderDetail, Tag, Comment, Like, Rating, Subcribes, PaymentMethod
from .serializers import (
    FoodSerializer,
    FoodDetailsSerializer,
    UserSerializer,
    StoreSerializer,
    MenuItemSerializer,
    TagSerializer,
    OrderSerializer,
    OrderDetailSerializer,
    AuthorizedFoodDetailsSerializer,
    SubcribeSerializer,
    CommentSerializer,
    PaymentMethodSerializer
)
from . import paginators
import json
from .perms import CommentOwner
from django.db.models import Count
from django.core.mail import send_mail, EmailMessage
from datetime import datetime


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.filter(active=True)
    serializer_class = TagSerializer
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

    def get_permissions(self):
        if self.action in ['assign_tags', 'comments', 'like', 'rating']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.request.user.is_authenticated:
            return AuthorizedFoodDetailsSerializer

        return self.serializer_class

    @action(methods=['post'], detail=True, url_path='tags')
    def assign_tags(self, request, pk):
        food = self.get_object()
        tags = request.data['tags']
        for t in tags:
            tag, _ = Tag.objects.get_or_create(name=t)
            food.tags.add(tag)
        food.save()

        return Response(FoodDetailsSerializer(food, context={'request': request}).data)

    @action(methods=['post'], detail=True, url_path='comments')
    def comments(self, request, pk):
        c = Comment(content=request.data['content'], food=self.get_object(), user=request.user)
        c.save()

        return Response(CommentSerializer(c).data, status=status.HTTP_201_CREATED)

    @action(methods=['post'], detail=True, url_path='like')
    def like(self, request, pk):
        l, created = Like.objects.get_or_create(food=self.get_object(), user=request.user)
        if not created:
            l.liked = not l.liked
        l.save()

        return Response(status=status.HTTP_200_OK)

    @action(methods=['post'], detail=True, url_path='rating')
    def rating(self, request, pk):
        r, _ = Rating.objects.get_or_create(food=self.get_object(), user=request.user)
        r.rate = request.data['rate']
        r.save()

        return Response(status=status.HTTP_200_OK)

    # @action(methods=['post'], detail=True, url_path='rating')
    # def create_review(self, request, pk):
    #     serializer = ReviewSerializer(data=request.data)
    #     if serializer.is_valid():
    #         food_id = serializer.validated_data['food_id']
    #         store_id = serializer.validated_data['store_id']
    #         rating = serializer.validated_data['rating']
    #         # comment = serializer.validated_data['comment']
    #
    #         try:
    #             food = Food.objects.get(pk=food_id)
    #         except Food.DoesNotExist:
    #             return Response({'error': 'Món ăn không tồn tại!!!'}, status=status.HTTP_400_BAD_REQUEST)
    #
    #         try:
    #             store = User.objects.get(pk=store_id, user_role=User.STORE)
    #         except User.DoesNotExist:
    #             return Response({'error': 'Cửa hàng không tồn tại!!!'}, status=status.HTTP_400_BAD_REQUEST)
    #
    #         user = request.user
    #         #Kiểm tra người dùng đã đánh giá món ăn này chưa
    #         try:
    #             rating_obj = Rating.objects.get(user=user, food=food)
    #         except Rating.DoesNotExist:
    #             rating_obj = Rating(user=user, food=food)
    #
    #         rating_obj.rate = rating
    #         rating_obj.save()
    #         # #Tạo comment mới
    #         # comment_obj = Comment(user=user, food=food, content=comment)
    #         # comment_obj.save()
    #         return Response(serializer.data, status=status.HTTP_201_CREATED)
    #     return Response(serializer.dat, status=status.HTTP_400_BAD_REQUEST)


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
    serializer_class = StoreSerializer

    def get_queryset(self):
        menu = User.objects.filter(is_active=True, is_verify=True, user_role=1)
        menu = menu.annotate(
            menu_count=Count('menuitem_store')
        )

        kw = self.request.query_params.get('kw')
        if kw:
            menu = menu.filter(name_store__icontains=kw)

        return menu

    @action(methods=['get'], detail=True, url_path='list_food_by_store')
    def list_food_by_store(self, request, pk):
        store = self.get_object()
        # Lấy tất cả các menu item của tất cả các store
        menu_items = MenuItem.objects.filter(store__in=store)

        # Lấy tất cả các food của tất cả các menu item
        foods = Food.objects.filter(menu_item__in=menu_items)

        data = {}
        try:
            data[store.id] = {
                'store': store.id,
                'name_store': store.name_store,
                'address': store.address,
                'phone': store.phone,
                'foods': []
            }

            # Thêm thông tin các order_detail vào đơn hàng
            for food in foods:
                if food.menu_item.store.id == store.id:
                    food_dict = {
                        'id': food.id,
                        'name': food.name,
                        'active': food.active,
                        'price': food.price,
                        'image': food.image_food.url if food.image_food else None,
                        'description': food.description,
                        'start_time': str(food.start_time),
                        'end_time': str(food.end_time)
                    }

                data[food.menu_item.store.id]['foods'].append(food_dict)

            return Response({"message": f"Thông tin chi tiết của cửa hàng {store.name_store}",
                             "statusCode": status.HTTP_200_OK, "data": data},
                            status=status.HTTP_200_OK)
            if not data:
                return Response({"message": f"Không có thông tin của cửa hàng {store.name_store}.",
                                 "statusCode": status.HTTP_404_NOT_FOUND},
                                status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)})

    @action(methods=['get'], detail=True, url_path='menu-item')
    def get_menu_item(self, request, pk):
        store = self.get_object()
        menu_items = store.menuitem_store.filter(active=True).annotate(
            food_count=Count('menuitem_food'))

        kw = request.query_params.get('kw')
        if kw:
            menu_items = menu_items.filter(name__icontains=kw)

        return Response(MenuItemSerializer(menu_items, many=True).data, status=status.HTTP_200_OK)

    def get_permissions(self):
        if self.action in ['get_store_detail', 'get_menu_store']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    @action(methods=['get'], detail=False, url_path='menu-management')
    def get_menu_store(self, request):
        user = request.user
        if user.user_role != User.STORE or user.is_active == 0 or user.is_superuser == 1 or user.is_staff == 1:
            return Response({"message": f"Bạn không có quyền thực hiện chức năng này!"},
                            status=status.HTTP_403_FORBIDDEN)
        if user.is_verify != 1:
            return Response({"message": f"Tài khoản cửa hàng {user.name_store} chưa được chứng thực!"},
                            status=status.HTTP_403_FORBIDDEN)

        # Lấy store
        store = User.objects.get(id=user.id)
        menu_items = store.menuitem_store.annotate(
            food_count=Count('menuitem_food'))

        return Response(MenuItemSerializer(menu_items, many=True).data, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='food-management')
    def get_food_store(self, request):
        user = request.user
        if user.user_role != User.STORE or user.is_active == 0 or user.is_superuser == 1 or user.is_staff == 1:
            return Response({"message": f"Bạn không có quyền thực hiện chức năng này!"},
                            status=status.HTTP_403_FORBIDDEN)
        if user.is_verify != 1:
            return Response({"message": f"Tài khoản cửa hàng {user.name_store} chưa được chứng thực!"},
                            status=status.HTTP_403_FORBIDDEN)

        # Lấy store
        try:
            store = User.objects.get(id=user.id, user_role=User.STORE)
            foods = Food.objects.filter(menu_item__store=user.id)

            serializer = FoodSerializer(foods, many=True)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({'error': 'Store not found.'}, status=404)

        # Lấy tất cả các menu item của tất cả các store
        # menu_items = MenuItem.objects.filter(store__in=store)
        #
        # # Lấy tất cả các food của tất cả các menu item
        # foods = Food.objects.filter(menu_item__in=menu_items)
        #
        # data = {}
        # try:
        #     for s in store:
        #         data[s.id] = {
        #             'store': s.id,
        #             'name_store': s.name_store,
        #             'address': s.address,
        #             'phone': s.phone,
        #             'menu_items': []
        #         }
        #
        #     # Đổ dữ liệu đơn hàng vào các store tương ứng
        #     for menu in menu_items:
        #         menu_dict = {
        #             'id': menu.id,
        #             'name': menu.name,
        #             'active': menu.active,
        #             'foods': []
        #         }
        #
        #         # Thêm thông tin các order_detail vào đơn hàng
        #         for food in foods:
        #             if food.menu_item.id == menu.id:
        #                 food_dict = {
        #                     'id': food.id,
        #                     'name': food.name,
        #                     'active': food.active,
        #                     'price': food.price,
        #                     'image': food.image_food.url if food.image_food else None,
        #                     'description': food.description,
        #                     'start_time': str(food.start_time),
        #                     'end_time': str(food.end_time)
        #                 }
        #                 menu_dict['foods'].append(food_dict)
        #
        #         data[menu.store.id]['menu_items'].append(menu_dict)
        #
        #     return Response({"message": f"Thông tin chi tiết của cửa hàng {user.name_store}",
        #                      "statusCode": status.HTTP_200_OK, "data": data},
        #                     status=status.HTTP_200_OK)
        #     if not data:
        #         return Response({"message": f"Không có thông tin của cửa hàng {user.name_store}.",
        #                          "statusCode": status.HTTP_404_NOT_FOUND},
        #                         status=status.HTTP_404_NOT_FOUND)
        # except Exception as e:
        #     return Response({'error': str(e)})


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
                super().destroy(request, *args, **kwargs)
                return Response({"message": "Xóa thông tin menu thành công!"},
                                status=status.HTTP_200_OK)

            return Response({"message": f"Memu này không thuộc quyền xóa của bạn!"},
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
                    for food in menu.menuitem_food.all():
                        food.active = 0
                        food.save()
                    menu.save()
                    return Response({'message': f'Menu và các món ăn trong menu {menu.name} đã được tắt trạng thái sẵn bán thành công!'},
                                    status=status.HTTP_200_OK)
                if menu.active == 0:
                    menu.active = 1
                    for food in menu.menuitem_food.all():
                        food.active = 1
                        food.save()
                    menu.save()
                    return Response({'message': f'Menu và các món ăn trong menu {menu.name} đã được bật trạng thái sẵn bán thành công!'},
                                    status=status.HTTP_200_OK)
            return Response({'message': f'Menu {menu.name} không thuộc quyền xử lý của bạn. Cập nhật không thành công!'},
                            status=status.HTTP_404_NOT_FOUND)

        return Response({'message': f'Menu {menu.name} cập nhật trạng thái không thành công. Vui lòng thử lại!'},
                        status=status.HTTP_404_NOT_FOUND)


class FoodStoreViewSet(viewsets.ViewSet, generics.CreateAPIView, generics.UpdateAPIView, generics.RetrieveAPIView, generics.DestroyAPIView):
    serializer_class = FoodSerializer()
    queryset = Food.objects.all()
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ['create', 'update', 'delete', 'destroy', 'set_status_food']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    # tạo món ăn cho từng cửa hàng đăng nhập vào
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
            menu_item = MenuItem.objects.get(pk=menu_item_id)
        except MenuItem.DoesNotExist:
            return Response({"message": f"Không tìm thấy menu nào của cửa hàng {user.name_store}! Vui lòng tạo menu!"},
                            status=status.HTTP_404_NOT_FOUND)

        # Tạo Food
        name = request.data.get('name')
        price = request.data.get('price')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        description = request.data.get('description')
        image_food = request.data.get('image_food')

        if name != "" and price != "":
            food = Food.objects.create(name=name, active=True, price=price, description=description,
                                       start_time=start_time, end_time=end_time,
                                       image_food=image_food, menu_item=menu_item)

            # Gắn tag vào food
            tags = json.loads(request.data.get("tags"))
            if tags is not None:
                for tag in tags:
                    try:
                        tag = Tag.objects.get(id=tag['id'])
                    except Tag.DoesNotExist:
                        return Response({"message": f"Không tìm thấy tag!"},
                                        status=status.HTTP_404_NOT_FOUND)
                    food.tags.add(tag)

            # followers = Subcribes.objects.filter(store=user.id)
            # if followers:
            #     for f in followers:
            #         # send mail
            #         email = f.follower.email
            #         subject = "Xác nhận đơn hàng đã được giao thành công"
            #         content = """
            #             Chào {0},
            #             Cửa hàng {1} - {7} bạn theo dõi vừa đăng món ăn mới.
            #             Chi tiết:
            #             Tên món ăn: {2}
            #             Giá bán: {3:,.0f} VND
            #             Thời gian bán trong ngày: {4} - {5}
            #             Danh mục: {6}
            #             Cám ơn bạn đã tin tưởng chọn dịch vụ của chúng tôi.
            #             Mọi thắc mắc và yêu cầu hỗ trợ xin gửi về địa chỉ foodlocationapp@gmail.com.
            #             """.format(f.follower.first_name + " " + f.follower.last_name,
            #                        user.name_store, name,
            #                        price, start_time, end_time,
            #                        menu_item.name, user.address)
            #         if email and subject and content:
            #             send_email = EmailMessage(subject, content, to=[email])
            #             send_email.send()
            #             return Response(status=status.HTTP_200_OK)

            return Response({"message": f"Lưu thông tin món ăn thành công cho cửa hàng {user.name_store}!"},
                            status=status.HTTP_201_CREATED)
        return Response({"message": "Lưu thông tin món ăn không thành công!"}, status=status.HTTP_400_BAD_REQUEST)

    # chỉnh sửa món ăn cho từng cửa hàng đăng nhập vào
    def update(self, request, pk):
        try:
            food = Food.objects.get(id=pk)
            # Lấy thông tin người dùng và kiểm tra quyền truy cập của người dùng
            user = request.user
            if user.user_role != User.STORE or user.is_active == 0 or user.is_superuser == 1 or user.is_staff == 1:
                return Response({"message": f"Bạn không có quyền thực hiện chức năng này!"},
                                status=status.HTTP_403_FORBIDDEN)
            if user.is_verify != 1:
                return Response({"message": f"Tài khoản cửa hàng {user.name_store} chưa được chứng thực để thực hiện chức năng chỉnh sửa món ăn!"},
                                status=status.HTTP_403_FORBIDDEN)

            if request.method == 'PUT':
                serializer = FoodSerializer(food, data=request.data, partial=True)
                if serializer.is_valid():
                    if food.menu_item.store == user:
                        serializer.save()
                        return Response({"message": f"Chỉnh sửa thông tin món ăn thành công  cho cửa hàng {user.name_store}!",
                                         "data": serializer.data},
                                        status=status.HTTP_200_OK)
                    return Response({"message": f"Không tìm thấy menu phù hợp của cửa hàng {user.name_store}! Vui lòng thử lại!"},
                                    status=status.HTTP_404_NOT_FOUND)

            return Response({"message": "Chỉnh sửa thông tin món ăn không thành công!"},
                            status=status.HTTP_400_BAD_REQUEST)
        except Food.DoesNotExist:
            return Response({'error': 'Không tìm thấy món ăn!'}, status=status.HTTP_404_NOT_FOUND)

    # xóa món ăn cho từng cửa hàng đăng nhập vào
    def destroy(self, request, *args, **kwargs):
        try:
            user = request.user
            if user == self.get_object().menu_item.store:
                super().destroy(request, *args, **kwargs)
                return Response({"message": "Xóa thông tin món ăn thành công!"},
                                status=status.HTTP_200_OK)

            return Response({"message": f"Món ăn này không thuộc quyền xóa của bạn!"},
                            status=status.HTTP_403_FORBIDDEN)
        except Food.DoesNotExist:
            return Response({'error': 'Không tìm thấy món ăn!'}, status=status.HTTP_404_NOT_FOUND)

    # thiết lập trạng thái món ăn (active)
    @action(methods=['post'], detail=True, url_path='set-status-food')
    def set_status_food(self, request, pk):
        user = request.user
        if user.user_role != User.STORE or user.is_active == 0 or user.is_superuser == 1 or user.is_staff == 1:
            return Response({"message": "Bạn không có quyền thực hiện chức năng này."},
                            status=status.HTTP_403_FORBIDDEN)
        if user.is_verify != 1:
            return Response({"message": f"Tài khoản cửa hàng {user.name_store} chưa được chứng thực để thực hiện chức năng này!"},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            food = Food.objects.get(id=pk)
        except Food.DoesNotExist:
            return Response({'message': f'Món ăn không được tìm thấy trong cửa hàng {user.name_store}!'},
                            status=status.HTTP_404_NOT_FOUND)

        if request.method == 'POST':
            if food.menu_item.store == user:
                if food.active == 1:
                    food.active = 0
                    food.save()
                    return Response({'message': f'Món ăn {food.name} đã được tắt trạng thái sẵn bán thành công!'},
                                    status=status.HTTP_200_OK)
                if food.active == 0:
                    food.active = 1
                    food.save()
                    return Response({'message': f'Món ăn {food.name} đã được bật trạng thái sẵn bán thành công!'},
                                    status=status.HTTP_200_OK)
            return Response({'message': f'Món ăn {food.name} không thuộc quyền xử lý của bạn. Cập nhật không thành công!'},
                            status=status.HTTP_404_NOT_FOUND)

        return Response({'message': f'Món ăn {food.name} cập nhật trạng thái không thành công. Vui lòng thử lại!'},
                        status=status.HTTP_404_NOT_FOUND)


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

        try:
            orders = Order.objects.filter(store=user, order_status=Order.PENDING)

            return Response(OrderSerializer(orders, many=True).data,
                            status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    # xác nhận đơn hàng
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

                if order.order_status == Order.ACCEPTED:
                    if order.payment_status == 0:
                        order.order_status = Order.SUCCESSED
                        order.payment_status = True
                        order.save()

                        # send mail
                        email = order.user.email
                        subject = "Xác nhận đơn hàng đã được giao thành công"
                        content = """
                            Chào {0},
                            Chúng tôi đã ghi nhận thanh toán của bạn.
                            Chi tiết:
                            Mã đơn hàng: {1}
                            Tên cửa hàng: {2}
                            Tên khách hàng nhận: {3}
                            Địa chỉ giao hàng: {4}
                            Tổng thanh toán: {5:,.0f} VND
                            Hình thức thanh toán: {6}
                            Ngày thanh toán: {7}
                            Cám ơn bạn đã tin tưởng chọn dịch vụ của chúng tôi.
                            Mọi thắc mắc và yêu cầu hỗ trợ xin gửi về địa chỉ foodlocationapp@gmail.com.
                            """.format(order.user.first_name + " " + order.user.last_name,
                                       order.pk, order.store.name_store,
                                       order.receiver_name, order.receiver_address,
                                       order.amount, order.paymentmethod.name, order.payment_date)
                        if email and subject and content:
                            send_email = EmailMessage(subject, content, to=[email])
                            send_email.send()
                            return Response(data={"message": "Gửi mail thành công! Đã xác nhận đơn hàng giao hàng thành công!"},
                                            status=status.HTTP_200_OK)
                        return Response({'message': f'Đơn hàng {pk} đã được xác nhận thành công! Khách hàng chưa nhận được mail!'},
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

        try:
            orders = Order.objects.filter(store=user, order_status=Order.ACCEPTED)

            return Response(OrderSerializer(orders, many=True).data,
                            status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    # xác nhận đơn hàng giao thành công - order_status=SUCCESSED
    # @action(methods=['post'], detail=True, url_path='complete-order')
    # def complete_order(self, request, pk):
    #     user = request.user
    #     if user.user_role != User.STORE or user.is_active == 0 or user.is_superuser == 1 or user.is_staff == 1:
    #         return Response({"message": "Bạn không có quyền thực hiện chức năng này."},
    #                         status=status.HTTP_403_FORBIDDEN)
    #
    #     try:
    #         order = Order.objects.get(id=pk)
    #     except Order.DoesNotExist:
    #         return Response({'message': f'Đơn hàng không được tìm thấy hoặc đã được xử lý!'},
    #                         status=status.HTTP_404_NOT_FOUND)
    #
    #     if request.method == 'POST':
    #         if order.store.id == user.id:
    #             if order.order_status == Order.ACCEPTED:
    #                 if order.payment_status == 0:
    #                     order.order_status = Order.SUCCESSED
    #                     order.payment_status = True
    #                     order.save()
    #
    #                     # send mail
    #                     email = order.user.email
    #                     subject = "Xác nhận đơn hàng đã được giao thành công"
    #                     content = """
    #                         Chào {0},
    #                         Chúng tôi đã ghi nhận thanh toán của bạn.
    #                         Chi tiết:
    #                         Mã đơn hàng: {1}
    #                         Tên cửa hàng: {2}
    #                         Tên khách hàng nhận: {3}
    #                         Địa chỉ giao hàng: {4}
    #                         Tổng thanh toán: {5:,.0f} VND
    #                         Hình thức thanh toán: {6}
    #                         Ngày thanh toán: {7}
    #                         Cám ơn bạn đã tin tưởng chọn dịch vụ của chúng tôi.
    #                         Mọi thắc mắc và yêu cầu hỗ trợ xin gửi về địa chỉ foodlocationapp@gmail.com.
    #                         """.format(order.user.first_name + " " + order.user.last_name,
    #                                    order.pk, order.store.name_store,
    #                                    order.receiver_name, order.receiver_address,
    #                                    order.amount, order.paymentmethod.name, order.payment_date)
    #                     if email and subject and content:
    #                         send_email = EmailMessage(subject, content, to=[email])
    #                         send_email.send()
    #                         return Response(data={"message": "Gửi mail thành công! Đã xác nhận đơn hàng giao hàng thành công!"},
    #                                         status=status.HTTP_200_OK)
    #
    #                 return Response({'message': f'Đã xác nhận đơn hàng {pk} giao hàng thành công!'},
    #                                 status=status.HTTP_200_OK)
    #         return Response({'message': f'Đơn hàng {pk} không thuộc quyền xử lý của bạn. Cập nhật không thành công!'},
    #                         status=status.HTTP_404_NOT_FOUND)
    #
    #     return Response({'message': f'Đơn hàng {pk} xác nhận không thành công. Vui lòng thử lại!'},
    #                     status=status.HTTP_404_NOT_FOUND)


class OrderDetailViewSet(viewsets.ViewSet, generics.RetrieveUpdateDestroyAPIView):
    queryset = OrderDetail.objects.all()
    serializer_class = OrderDetailSerializer
    lookup_field = 'id'


class CommentViewSet(viewsets.ViewSet, generics.ListAPIView, generics.DestroyAPIView, generics.UpdateAPIView):
    queryset = Comment.objects.filter(active=True)
    serializer_class = CommentSerializer
    permission_classes = [CommentOwner, ]


class SubcribeViewSet(viewsets.ViewSet, generics.ListAPIView, generics.DestroyAPIView, generics.UpdateAPIView):
    queryset = Subcribes.objects.filter(active=True)
    serializer_class = SubcribeSerializer

    def get_permissions(self):
        if self.action in ['post', 'delete', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    # lấy danh sách subcribes theo từng cửa hàng
    @action(methods=['get'], detail=True)
    def get_sub_by_store_id(self, request, pk):
        try:
            store = User.objects.get(id=pk, user_role=User.STORE)
            if store:
                subs = Subcribes.objects.filter(store=pk)

                serializer = SubcribeSerializer(subs, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'Store not found.'}, status=status.HTTP_404_NOT_FOUND)

    # đếm tổng follower theo từng cửa hàng
    @action(methods=['get'], detail=True)
    def count_follower_by_store(self, request, pk):
        try:
            store = User.objects.get(id=pk, user_role=User.STORE)
            if store:
                follower = User.objects.filter(id=pk)
                follower = follower.annotate(total_followers=Count('store'))
                data = [{'store_id': f.id, 'name_store': f.name_store, 'total_followers': f.total_followers}
                        for f in follower]
                return Response(data, status=status.HTTP_200_OK)
            return Response({'error': 'Không tìm thấy thông tin!'}, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({'error': 'Không tìm thấy thông tin!'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        try:
            follower = request.user
            store_id = request.data.get('store_id')
            store = User.objects.get(id=store_id)

            sub = Subcribes.objects.create(follower=follower, store=store)

            # serializer = SubcribeSerializer(sub)
            return Response(request.data, status=status.HTTP_201_CREATED)
        except User.DoesNotExist:
            return Response({'message': 'Người dùng không tồn tại!'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, sub_id):
        try:
            sub = Subcribes.objects.get(id=sub_id)

            #Check permission
            if request.user != sub.follower:
                return Response({'message': 'Bạn không có quyền để xóa!'}, status=status.HTTP_401_UNAUTHORIZED)

            sub.delete()

            return Response({'message': 'Hủy theo dõi thành công!!!'}, status=status.HTTP_200_OK)

        except Subcribes.DoesNotExist:
            return Response({'message': 'Theo dõi không được tìm thấy!'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FoodByStoreViewSet(viewsets.ViewSet):
    serializer_class = FoodSerializer

    def get_queryset(self):
        store_id = self.kwargs.get('store_id')
        queryset = Food.objects.filter(menu_item__store=store_id)
        return queryset

    @action(methods=['get'], detail=True)
    def get_food_by_store_id(self, request, pk):
        try:
            store = User.objects.get(id=pk, user_role=User.STORE)
            foods = Food.objects.filter(menu_item__store=pk)

            serializer = FoodSerializer(foods, many=True)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({'error': 'Store not found.'}, status=404)


class PaymentmethodViewSet(viewsets.ViewSet, generics.ListAPIView):
    serializer_class = PaymentMethodSerializer
    queryset = PaymentMethod.objects.all()


#Cửa hàng được phép xem: Thống kê doanh thu các sản phẩm, danh mục sản phẩm theo tháng, quý và năm

class RevenueStatMonth(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        month_str = request.data.get('month')
        try:
            month = datetime.strptime(month_str, '%Y-%m')
        except:
            return Response(data={"error_msg": "Invalid month format. Please use 'YYYY-MM' format."},
                            status=status.HTTP_400_BAD_REQUEST)

        #Lấy danh sách tất cả các order detail trong tháng đó
        order_details = OrderDetail.objects.filter(order__created_date__year=month.year,
                                                   order__created_date__month=month.month)
        #Tính tổng doanh thu của cửa hàng trong tháng đó
        total_revenue = sum([order_detail.unit_price * order_detail.quantity
                             for order_detail in order_details])
        #Tạo danh sách các sản phẩm
        items = []
        for order_detail in order_details:
            item = {
                "food_id": order_detail.food.id,
                "food_name": order_detail.food.name,
                "food_price": order_detail.food.price,
                "quantity": order_detail.quantity
            }
            #Tìm kiếm danh mục của sản phẩm
            menu_item = order_detail.food.menu_item
            if menu_item:
                item["menu_item_id"] = menu_item.id
                item["menu_item_name"] = menu_item.name

            #Thêm sản phẩm vào danh sách
            items.append(item)
        #Tạo danh sách các danh mục
        menu_items = []
        for order_detail in order_details:
            menu_item = order_detail.food.menu_item
            if menu_item:
                menu_item_total = sum([order.unit_price * order.quantity
                                       for order in order_details
                                       if order.food.menu_item == menu_item])
                menu_item_dict = {
                    "menu_item_id": menu_item.id,
                    "menu_item_name": menu_item.name,
                    "total_revenue": menu_item_total
                }
                #Thêm danh mục vào danh sách
                menu_items.append(menu_item_dict)
        #Trả về kết quả
        return Response(data={
            "total_revenue": total_revenue,
            "items": items,
            "menu_items": menu_items
        }, status=status.HTTP_200_OK)


class RevenueStatsQuarter(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # quarter_str = request.data.get('quarter')
        # try:
        #     year, quarter_num = [int(x) for x in quarter_str.split('-')]
        #     quarter_start_month = 3 * (quarter_num - 1) + 1
        #     quarter_end_month = quarter_start_month + 2
        #     quarter_start_date = datetime(year=year, month=quarter_start_month, day=1)
        #     quarter_end_date = datetime(year=year, month=quarter_end_month,
        #                                 day=calendar.monthrange(year, quarter_end_month)[1])
        # except:
        #     return Response(data={"error_msg": "Invalid quarter format. Please use 'YYYY-QN' format."},
        #                     status=status.HTTP_400_BAD_REQUEST)
        revenue_stats_from_str = request.data.get('revenue_stats_from')
        revenue_stats_to_str = request.data.get('revenue_stats_to')
        try:
            revenue_stats_from = datetime.strptime(revenue_stats_from_str, '%Y-%m-%d')
            revenue_stats_to = datetime.strptime(revenue_stats_to_str, '%Y-%m-%d')
        except:
            return Response(data={"error_msg": "cannot be left blank"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Lấy danh sách tất cả các order detail trong quý đó
        order_details = OrderDetail.objects.filter(order__created_date__range=[revenue_stats_from, revenue_stats_to])

        # Tạo danh sách các sản phẩm
        items = {}
        for order_detail in order_details:
            food = order_detail.food
            menu_item = food.menu_item
            item_id = food.id
            item_name = food.name
            item_price = food.price
            quantity = order_detail.quantity

            # Tính tổng doanh thu của sản phẩm
            item_revenue = order_detail.unit_price * quantity

            # Tạo một key cho sản phẩm nếu chưa tồn tại
            if item_id not in items:
                items[item_id] = {
                    "food_id": item_id,
                    "food_name": item_name,
                    "food_price": item_price,
                    "quantity": quantity,
                    "revenue": item_revenue,
                }
            else:
                # Cập nhật số lượng và doanh thu của sản phẩm
                items[item_id]["quantity"] += quantity
                items[item_id]["revenue"] += item_revenue

            # Nếu sản phẩm thuộc vào một danh mục, thêm danh mục vào sản phẩm
            if menu_item:
                if "menu_item_id" not in items[item_id]:
                    items[item_id]["menu_item_id"] = menu_item.id
                    items[item_id]["menu_item_name"] = menu_item.name

                # Tính tổng doanh thu của danh mục
                if menu_item.id not in items:
                    items[menu_item.id] = {
                        "menu_item_id": menu_item.id,
                        "menu_item_name": menu_item.name,
                        "revenue": item_revenue,
                    }
                else:
                    items[menu_item.id]["revenue"] += item_revenue

        # Sắp xếp danh sách sản phẩm theo doanh thu giảm dần
        items_sorted = sorted(items.values(), key=(lambda x: x['revenue']), reverse=True)
        # Tính tổng doanh thu của quý
        total_revenue = sum(item['revenue'] for item in items_sorted)

        # Tạo danh sách kết quả trả về
        result = {
            # "quarter": quarter_str,
            "start_date": revenue_stats_from,
            "end_date": revenue_stats_to,
            "total_revenue": total_revenue,
            "items": items_sorted,
        }

        return Response(data=result, status=status.HTTP_200_OK)


class RevenueStatsYear(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        year_str = request.data.get('year')
        try:
            year = datetime.strptime(year_str, '%Y')
        except:
            return Response(data={"error_msg": "Invalid year format. Please use 'YYYY' format."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Lấy danh sách tất cả các order detail trong năm đó
        order_details = OrderDetail.objects.filter(order__created_date__year=year.year)

        # Tạo danh sách các sản phẩm và danh mục sản phẩm
        items = {}
        menu_items = {}
        for order_detail in order_details:
            food = order_detail.food
            menu_item = food.menu_item
            item_id = food.id
            item_name = food.name
            item_price = food.price
            quantity = order_detail.quantity

            # Tính tổng doanh thu của sản phẩm
            item_revenue = order_detail.unit_price * quantity

            # Tạo một key cho sản phẩm nếu chưa tồn tại
            if item_id not in items:
                items[item_id] = {
                    "food_id": item_id,
                    "food_name": item_name,
                    "food_price": item_price,
                    "quantity": quantity,
                    "revenue": item_revenue,
                }
            else:
                # Cập nhật số lượng và doanh thu của sản phẩm
                items[item_id]["quantity"] += quantity
                items[item_id]["revenue"] += item_revenue

            # Nếu sản phẩm thuộc vào một danh mục, thêm danh mục vào sản phẩm
            if menu_item:
                if "menu_item_id" not in items[item_id]:
                    items[item_id]["menu_item_id"] = menu_item.id
                    items[item_id]["menu_item_name"] = menu_item.name

                # Tính tổng doanh thu của danh mục
                if menu_item.id not in menu_items:
                    menu_items[menu_item.id] = {
                        "menu_item_id": menu_item.id,
                        "menu_item_name": menu_item.name,
                        "revenue": item_revenue,
                    }
                else:
                    menu_items[menu_item.id]["revenue"] += item_revenue

        # Sắp xếp danh sách sản phẩm theo doanh thu giảm dần
        items_sorted = sorted(items.values(), key=lambda x: x["revenue"], reverse=True)

        # Sắp xếp danh sách danh mục sản phẩm theo doanh thu giảm dần
        menu_items_sorted = sorted(menu_items.values(), key=lambda x: x["revenue"], reverse=True)

        # Trả về kết quả
        return Response(data={
            "items": items_sorted,
            "menu_items": menu_items_sorted,
        }, status=status.HTTP_200_OK)
