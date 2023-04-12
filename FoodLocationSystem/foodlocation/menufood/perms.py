from rest_framework import permissions


class OrderOwner(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, order):
        return request.user and request.user == order.user