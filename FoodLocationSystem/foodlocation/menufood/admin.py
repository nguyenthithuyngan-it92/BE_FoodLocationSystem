from django.contrib import admin
from .models import MenuItem, Food, User, Tag, PaymentMethod, Subcribes, Order, OrderDetail
from django.contrib.auth.models import Permission, Group
from django import forms
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.utils.html import mark_safe
from . import cloud_path
from django.urls import path
from django.template.response import TemplateResponse
from django.db.models import Count


# cập nhật trang thống kê
class FoodLocationAppAdminSite(admin.AdminSite):
    site_header = 'Trang quản lý địa điểm ăn uống'

    def get_urls(self):
        return [
           path('stats/', self.stats_view)
       ] + super().get_urls()

    def stats_view(self, request):
        orders_by_store = (
            Order.objects.filter(order_status=Order.SUCCESSED).values('store__name_store').annotate(total_orders=Count('id')).order_by('store__name_store')
        )

        sum_food_store = User.objects.filter(user_role=User.STORE) \
            .annotate(total_products=Count('menuitem_store__menuitem_food__id'))

        return TemplateResponse(request, 'admin/stats.html', {
            'count_order_store': orders_by_store,
            'sum_food_store': sum_food_store
        })


class UserAdmin(admin.ModelAdmin):
    list_display = ['pk', 'image', 'username', 'first_name', 'last_name', 'email',
                    'name_store', 'phone', 'address',
                    'is_active', 'is_staff', 'is_superuser', 'is_verify']
    search_fields = ['username', 'email', 'first_name', 'last_name', "phone", 'name_store']
    list_filter = ["user_role", "is_verify", 'is_active']
    readonly_fields = [*list_display]
    actions_on_top = False

    def image(self, user):
        if user.avatar:
            return mark_safe(
                "<img src='{cloud_path}{image_name}' width='50' height='50' />".format(cloud_path=cloud_path, image_name=user.avatar))

    def has_add_permission(self, request):
        # return False to disable the add functionality
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class SubcribesAdmin(admin.ModelAdmin):
    list_display = ['follower', 'store', 'active']
    list_filter = ["store", "follower"]
    actions_on_top = False
    readonly_fields = [*list_display]

    def has_add_permission(self, request):
        # return False to disable the add functionality
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# class FoodForm(forms.ModelForm):
#     description = forms.CharField(widget=CKEditorUploadingWidget)
#
#     class Meta:
#         model = Food
#         fields = '__all__'


# class MenuItemFoodInlineAdmin(admin.StackedInline):
#     model = Food
#     fk_name = 'menu_item'


# class TagFoodInline(admin.TabularInline):
#     model = Tag.foods.through


class TagAdmin(admin.ModelAdmin):
    # inlines = [TagFoodInline, ]
    search_fields = ['name',]
    list_display = ['pk', 'name', 'active']


class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'active']
    search_fields = ['name', 'store_id__name_store']
    list_filter = ['store', 'active']
    actions_on_top = False
    readonly_fields = [*list_display]

    def has_add_permission(self, request):
        # return False to disable the add functionality
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class UserFilter(admin.SimpleListFilter):
    title = 'user_role'
    parameter_name = 'user_role'

    def lookups(self, request, model_admin):
        return (
            ('USER', 'User'),
            ('STORE', 'Store'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'USER':
            return queryset.filter(menu_item__store__user_role=User.USER)
        if self.value() == 'STORE':
            return queryset.filter(menu_item__store__user_role=User.STORE)


class FoodAdmin(admin.ModelAdmin):
    list_display = ['img', 'name', 'menu_item', 'price', 'created_date', 'active', 'start_time', 'end_time', 'description']
    search_fields = ['name']
    # list_editable = ['name', 'menu_item', 'price', 'start_time', 'end_time']
    list_filter = ['menu_item__store', 'active']
    # form = FoodForm
    actions_on_top = False
    readonly_fields = [*list_display]

    def img(self, food):
        if food.image_food:
            return mark_safe(
                "<img src='{cloud_path}{image_name}' width='50' height='50' />".format(cloud_path=cloud_path, image_name=food.image_food))

    def has_add_permission(self, request):
        # return False to disable the add functionality
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super(FoodAdmin, self).get_queryset(request)
        return qs.filter(menu_item__store__user_role=User.STORE)


admin_site = FoodLocationAppAdminSite(name='myadmin')
admin_site.register(User, UserAdmin)
admin_site.register(Subcribes, SubcribesAdmin)
admin_site.register(MenuItem, MenuItemAdmin)
admin_site.register(Food, FoodAdmin)
admin_site.register(Tag, TagAdmin)
admin_site.register(PaymentMethod)
admin_site.register(Permission)
admin_site.register(Group)

