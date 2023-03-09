from django.contrib import admin
from .models import Category, Food, User
from django import forms
from ckeditor_uploader.widgets import CKEditorUploadingWidget
# Register your models here.


class UserAdmin(admin.ModelAdmin):
    list_display = ['pk', 'avatar', 'username', 'first_name', 'last_name', 'email', 'is_active']
    search_fields = ['username', 'email']


class FoodForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorUploadingWidget)

    class Meta:
        model = Food
        fields = '__all__'


class FoodAdmin(admin.ModelAdmin):
    list_display = ['pk', 'name', 'category', 'price', 'created_date', 'active']
    search_fields = ['name']
    form = FoodForm


admin.site.register(User, UserAdmin)
admin.site.register(Category)
admin.site.register(Food, FoodAdmin)

