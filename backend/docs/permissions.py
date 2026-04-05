from rest_framework.permissions import BasePermission
from .services import can_view, can_edit


class CanViewDocument(BasePermission):
    def has_object_permission(self, request, view, obj):
        return can_view(request.user, obj)


class CanEditDocument(BasePermission):
    def has_object_permission(self, request, view, obj):
        return can_edit(request.user, obj)
