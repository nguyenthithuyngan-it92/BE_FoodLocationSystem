from rest_framework import serializers
from .models import Food, User, MenuItem, Order, OrderDetail


class FoodSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField(source='image')

    def get_image(self, food):
        if food.image:
            request = self.context.get('request')
            return request.build_absolute_uri('/static/%s' % food.image.name) if request else ''

    class Meta:
        model = Food
        fields = ['id', 'name', 'created_date', 'price','active', 'start_time', 'end_time', 'description', 'image', 'menu_item']


class FoodDetailsSerializer(FoodSerializer):
    # tags = TagSerializer(many=True)

    class Meta:
        model = FoodSerializer.Meta.model
        fields = FoodSerializer.Meta.fields


class UserSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField(source='avatar')

    def get_image(self, user):
        if user.avatar:
            request = self.context.get('request')
            return request.build_absolute_uri('/static/%s' % user.avatar.name) if request else ''

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(user.password)
        user.save()

        return user

    class Meta:
        model = User
        fields = '__all__'
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
        fields = ['id', 'name_store', 'is_active', 'address', 'is_verify', 'menu_count']


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = '__all__'


class OrderDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDetail
        fields = '__all__'
        
    
