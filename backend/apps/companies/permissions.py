from rest_framework.permissions import BasePermission

from .selectors.company_selectors import get_company_by_id_for_user


class IsCompanyMember(BasePermission):
    """
    Permission class checking if request user is an active member of the target company.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True

        company_id = str(obj.id) if hasattr(obj, 'id') else str(obj)
        authorized_company = get_company_by_id_for_user(request.user, company_id)
        return authorized_company is not None
