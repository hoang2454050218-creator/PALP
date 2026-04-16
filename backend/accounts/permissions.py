from rest_framework.permissions import BasePermission

from .models import LecturerClassAssignment, ClassMembership


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_student


class IsLecturer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_lecturer


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin_user


class IsLecturerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_lecturer or request.user.is_admin_user
        )


class IsClassMember(BasePermission):
    """
    Lecturer must be assigned to the class referenced by `class_id` in the URL.
    Admins bypass this check.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_admin_user:
            return True
        class_id = (
            view.kwargs.get("class_id")
            or request.query_params.get("class_id")
        )
        if not class_id:
            return False
        return LecturerClassAssignment.objects.filter(
            lecturer=request.user, student_class_id=class_id,
        ).exists()


class IsStudentInLecturerClass(BasePermission):
    """
    Target student (from URL `student_id`) must belong to a class
    the requesting lecturer is assigned to. Admins bypass.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_admin_user:
            return True
        student_id = view.kwargs.get("student_id")
        if not student_id:
            return False
        lecturer_class_ids = LecturerClassAssignment.objects.filter(
            lecturer=request.user,
        ).values_list("student_class_id", flat=True)
        return ClassMembership.objects.filter(
            student_id=student_id,
            student_class_id__in=lecturer_class_ids,
        ).exists()


class IsOwnAlertClass(BasePermission):
    """
    Alert's student_class must be one the lecturer is assigned to.
    Admins bypass.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_admin_user:
            return True
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_admin_user:
            return True
        if not hasattr(obj, "student_class_id"):
            return False
        return LecturerClassAssignment.objects.filter(
            lecturer=request.user,
            student_class_id=obj.student_class_id,
        ).exists()
