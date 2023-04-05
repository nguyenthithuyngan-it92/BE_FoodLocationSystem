from rest_framework import permissions


class FeedbackOwner(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, feedback):
        return request.user and request.user == feedback.user