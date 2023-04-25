from rest_framework import serializers
from .models import Food, User, MenuItem, Order, OrderDetail, Tag, PaymentMethod, Comment, Subcribes, Rating


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


class FoodSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField(source='image')
    tags = TagSerializer(many=True)

    def get_image(self, food):
        if food.image:
            request = self.context.get('request')
            return request.build_absolute_uri('/static/%s' % food.image.name) if request else ''

    class Meta:
        model = Food
        fields = ['id', 'name', 'price', 'start_time', 'end_time', 'description', 'image', 'menu_item', 'tags']


class FoodDetailsSerializer(FoodSerializer):
    tags = TagSerializer(many=True)

    class Meta:
        model = FoodSerializer.Meta.model
        fields = FoodSerializer.Meta.fields + ['content', 'tags']


class AuthorizedFoodDetailsSerializer(FoodDetailsSerializer):
    liked = serializers.SerializerMethodField()
    rate = serializers.SerializerMethodField()

    def get_liked(self, food):
        request = self.context.get('request')
        if request:
            return food.like_set.filter(user=request.user, liked=True).exists()

    def get_rate(self, food):
        request = self.context.get('request')
        if request:
            r = food.rating_set.filter(user=request.user).first()
            return r.rate if r else 0

    class Meta:
        model = FoodSerializer.Meta.model
        fields = FoodSerializer.Meta.fields + ['liked', 'rate']


class UserSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField(source='avatar')

    def get_image(self, user):
        if user.avatar:
            request = self.context.get('request')
            return request.build_absolute_uri('/static/%s' % user.avatar.name) if request else ''

    def create(self, validated_data):
        data = validated_data.copy()
        user = User(**data)
        user.set_password(user.password)
        user.save()

        return user

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'avatar', 'email', 'phone', 'image',
                  'name_store', 'address', 'user_role']
        extra_kwargs = {
            'avatar': {'write_only': True},
            'password': {'write_only': True}
        }


class MenuItemSerializer(serializers.ModelSerializer):
    food_count = serializers.SerializerMethodField()

    def get_food_count(self, menu):
        return menu.food_count

    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'active', 'store', 'food_count']


class StoreSerializer(serializers.ModelSerializer):
    menu_count = serializers.SerializerMethodField()

    def get_menu_count(self, store):
        return store.menu_count

    class Meta:
        model = User
        fields = ['id', 'name_store', 'is_active', 'address', 'is_verify', 'menu_count', 'user_role']


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = '__all__'


class OrderDetailSerializer(serializers.ModelSerializer):
    food = FoodSerializer(many=False, read_only=True)

    class Meta:
        model = OrderDetail
        fields = ['id', 'unit_price', 'quantity', 'food']


class OrderSerializer(serializers.ModelSerializer):
    order_details = OrderDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'created_date', 'amount', 'delivery_fee', 'order_status', 'receiver_name',
                  'receiver_phone', 'receiver_address', 'payment_date', 'payment_status',
                  'paymentmethod', 'user', 'store', 'order_details']


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Comment
        fields = ["id", "content", "created_date", "user"]


# class ReviewSerializer(serializers.ModelSerializer):
#     food_id = serializers.IntegerField()
#     store_id = serializers.IntegerField()
#     rating = serializers.IntegerField(min_value=1, max_value=5, default=0)
#
#     class Meta:
#         model = Rating
#         fields = '__all__'


class SubcribeSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Subcribes
        fields = ['id', 'follower', 'store', 'created_date']