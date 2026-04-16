from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, StudentClass, ClassMembership, LecturerClassAssignment


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "student_id", "is_active", "is_deleted")
    list_filter = ("role", "is_active", "is_deleted")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("PALP", {"fields": ("role", "student_id", "phone", "consent_given", "consent_given_at")}),
        ("Soft Delete", {"fields": ("is_deleted", "deleted_at")}),
    )
    readonly_fields = ("deleted_at",)


@admin.register(StudentClass)
class StudentClassAdmin(admin.ModelAdmin):
    list_display = ("name", "academic_year", "created_at")


@admin.register(ClassMembership)
class ClassMembershipAdmin(admin.ModelAdmin):
    list_display = ("student", "student_class", "joined_at")


@admin.register(LecturerClassAssignment)
class LecturerClassAssignmentAdmin(admin.ModelAdmin):
    list_display = ("lecturer", "student_class", "assigned_at")
