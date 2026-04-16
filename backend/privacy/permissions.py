from rest_framework.permissions import BasePermission


class HasConsent(BasePermission):
    message = "Bạn cần đồng ý thu thập dữ liệu trước khi sử dụng tính năng này."

    def has_permission(self, request, view):
        purpose = getattr(view, "required_consent", None)
        if not purpose:
            return True

        if not request.user.is_authenticated:
            return False

        if not request.user.is_student:
            return True

        from .services import has_consent
        return has_consent(request.user, purpose)
