import enum
from django.db import models
from django.contrib.auth.models import AbstractUser
from ckeditor.fields import RichTextField
from cloudinary.models import CloudinaryField
from enum import Enum as UserEnum

# Create your models here.


class User(AbstractUser):
    avatar = CloudinaryField('avatar', default='', null=True)
    phone = models.CharField(max_length=11, unique=True)
    address = models.CharField(max_length=255, null=True)

    name_store = models.CharField(max_length=100, null=True, unique=True)
    is_verify = models.BooleanField(default=False, null=True)
    USER, STORE = range(2)
    ROLE = [
        (USER, "USER"),
        (STORE, "STORE")
    ]
    user_role = models.PositiveSmallIntegerField(choices=ROLE, default=USER)

    def __str__(self):
        return self.username


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        abstract = True


#danh mục của từng cửa hàng
class MenuItem(BaseModel):
    name = models.CharField(max_length=100)

    store = models.ForeignKey(User, related_name='menuitem_store', on_delete=models.CASCADE, limit_choices_to={'user_role': User.STORE})

    def __str__(self):
        return self.name


class Food(BaseModel):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=0)
    description = RichTextField(null=True)
    start_time = models.TimeField(null=True)
    end_time = models.TimeField(null=True)
    image_food = CloudinaryField('image_food', default='', null=True)
    # image = models.ImageField(upload_to='users/%Y/%m', null=True, default='')

    menu_item = models.ForeignKey('MenuItem', related_name='menuitem_food', on_delete=models.PROTECT)
    tags = models.ManyToManyField('Tag', related_name='foods')

    def __str__(self):
        return self.name


class Tag(BaseModel):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class PaymentMethod(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


# # tình trạng đơn hàng
#     PENDING = 'đã đặt'
#     ACCEPTED = 'đã xác nhận giao hàng'
#     SUCCESSED = 'giao thành công'


class Order(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=0)   #tổng tiền thức ăn
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=0)   #phí giao hàng

    PENDING, ACCEPTED, SUCCESSED = range(3)
    STATUS = [
        (PENDING, "PENDING"),
        (ACCEPTED, "ACCEPTED"),
        (SUCCESSED, "SUCCESSED")
    ]
    order_status = models.PositiveSmallIntegerField(choices=STATUS, default=PENDING)

    receiver_name = models.CharField(max_length=100)
    receiver_phone = models.CharField(max_length=11)
    receiver_address = models.CharField(max_length=255)

    payment_date = models.DateTimeField(auto_now=True)
    payment_status = models.BooleanField(default=False)

    paymentmethod = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    store = models.ForeignKey(User, related_name='store_order', on_delete=models.CASCADE)

    def __str__(self):
        return self.receiver_name


class OrderDetail(models.Model):
    unit_price = models.DecimalField(max_digits=10, decimal_places=0)   #tổng giá theo từng món
    quantity = models.IntegerField(default=1)

    order = models.ForeignKey(Order, on_delete=models.PROTECT)
    food = models.ForeignKey(Food, on_delete=models.PROTECT)


class ActionBase(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    food = models.ForeignKey(Food, on_delete=models.PROTECT)

    class Meta:
        abstract = True
        unique_together = ('food', 'user')


class Comment(ActionBase):
    content = models.CharField(max_length=255)
    food = models.ForeignKey(Food, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.content


class Like(ActionBase):
    liked = models.BooleanField(default=True)


class Rating(ActionBase):
    rate = models.SmallIntegerField(default=0)


# class Feedback(BaseModel):
#     content = models.TextField(null=True)
#
#     user = models.ForeignKey(User, related_name='user', on_delete=models.PROTECT)
#     food = models.ForeignKey(Food, on_delete=models.PROTECT)
#     store = models.ForeignKey(User, related_name='feedback_store', on_delete=models.PROTECT)
#     rate = models.PositiveSmallIntegerField(default=0)
#
#     class Meta:
#         unique_together = ("user", "store")


class Subcribes(BaseModel):
    follower = models.ForeignKey(User, related_name='follower', on_delete=models.CASCADE, limit_choices_to={'user_role': User.USER})
    store = models.ForeignKey(User, related_name='store', on_delete=models.CASCADE, limit_choices_to={'user_role': User.STORE})

    class Meta:
        unique_together = ("follower", "store")
