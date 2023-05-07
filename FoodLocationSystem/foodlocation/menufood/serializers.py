from rest_framework import serializers
from . import cloud_path
from .models import Food, User, MenuItem, Order, OrderDetail, Tag, PaymentMethod, Comment, Subcribes, Rating


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


class UserSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField(source='avatar')

    def get_image(self, user):
        if user.avatar:
            return '{cloud_path}{image_name}'.format(cloud_path=cloud_path, image_name=user.avatar)

    def create(self, validated_data):
        data = validated_data.copy()
        user = User(**data)
        user.set_password(user.password)
        user.save()

        return user

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'avatar', 'email', 'phone', 'image',
                  'name_store', 'address', 'user_role', 'is_verify', 'is_superuser']
        extra_kwargs = {
            'avatar': {'write_only': True},
            'password': {'write_only': True}
        }


class MenuItemSerializer2(serializers.ModelSerializer):
    store = UserSerializer()

    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'active', 'store']


class FoodSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField(source='image_food')
    tags = TagSerializer(many=True, read_only=True)
    menu_item = MenuItemSerializer2()

    def get_image(self, food):
        if food.image_food:
            return '{cloud_path}{image_name}'.format(cloud_path=cloud_path, image_name=food.image_food)

    class Meta:
        model = Food
        fields = ['id', 'name', 'price', 'active', 'start_time', 'end_time', 'description', 'image', 'image_food', 'menu_item', 'tags']
        extra_kwargs = {
            'image_food': {'write_only': True},
        }


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


class MenuItemSerializer(serializers.ModelSerializer):
    food_count = serializers.SerializerMethodField()
    store = UserSerializer()

    def get_food_count(self, menu):
        return menu.food_count

    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'active', 'store', 'food_count']


class StoreSerializer(serializers.ModelSerializer):
    menu_count = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField(source='avatar')

    def get_image(self, user):
        if user.avatar:
            return '{cloud_path}{image_name}'.format(cloud_path=cloud_path, image_name=user.avatar)

    def get_menu_count(self, store):
        return store.menu_count

    class Meta:
        model = User
        fields = ['id', 'name_store', 'avatar', 'image', 'is_active', 'address', 'email', 'phone', 'is_verify', 'menu_count', 'user_role']


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
        fields = ['id', 'content', 'created_date', 'user']


class SubcribeSerializer(serializers.ModelSerializer):
    follower = UserSerializer()

    class Meta:
        model = Subcribes
        fields = ['id', 'follower', 'store', 'created_date']