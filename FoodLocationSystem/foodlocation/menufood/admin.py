from django.contrib import admin
from .models import MenuItem, Food, User, Tag, PaymentMethod, Subcribes
from django.contrib.auth.models import Permission, Group
from django import forms
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from django.utils.html import mark_safe


# cập nhật trang thống kê
class FoodLocationAppAdminSite(admin.AdminSite):
    site_header = 'Trang quản lý địa điểm ăn uống'


admin_site = FoodLocationAppAdminSite(name='myadmin')


class UserAdmin(admin.ModelAdmin):
    list_display = ['pk', 'avatar', 'username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    list_filter = ["id", "username", "first_name", "last_name", "is_staff"]
    readonly_fields = ['image']

    def image(self, user):
        if user:
            return mark_safe(
                "<img src='/static/{url}' width='120' />".format(url=user.image.name, alt=user.first_name))


class SubcribesAdmin(admin.ModelAdmin):
    list_display = ['follower_id', 'active']


class FoodForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorUploadingWidget)

    class Meta:
        model = Food
        fields = '__all__'


class MenuItemFoodInlineAdmin(admin.StackedInline):
    model = Food
    fk_name = 'menu_item'


class TagFoodInline(admin.TabularInline):
    model = Tag.foods.through


class TagAdmin(admin.ModelAdmin):
    inlines = [TagFoodInline, ]
    search_fields = ['name']
    # list_display = ['pk', 'name']


class MenuItemAdmin(admin.ModelAdmin):
    search_fields = ['name']
    inlines = [MenuItemFoodInlineAdmin, ]


class FoodAdmin(admin.ModelAdmin):
    list_display = ['pk', 'name', 'menu_item', 'price', 'created_date', 'active', 'start_time', 'end_time']
    search_fields = ['name']
    # list_editable = ['name', 'menu_item', 'price', 'start_time', 'end_time']
    list_filter = ['name', 'menu_item', 'price']
    form = FoodForm


admin_site.register(User, UserAdmin)
admin_site.register(Subcribes, SubcribesAdmin)
admin_site.register(MenuItem, MenuItemAdmin)
admin_site.register(Food, FoodAdmin)
admin_site.register(Tag, TagAdmin)
admin_site.register(PaymentMethod)
admin_site.register(Permission)
admin_site.register(Group)

