from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

from .encryption import EncryptedCharField


class ActiveUserManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Sinh viên"
        LECTURER = "lecturer", "Giảng viên"
        ADMIN = "admin", "Quản trị"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    student_id = EncryptedCharField(max_length=255, blank=True)
    student_id_hash = models.CharField(max_length=64, blank=True, db_index=True)
    phone = EncryptedCharField(max_length=255, blank=True)
    avatar_url = models.URLField(blank=True)
    consent_given = models.BooleanField(default=False)
    consent_given_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ActiveUserManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "palp_user"

    def save(self, **kwargs):
        if self.student_id:
            import hashlib
            raw = self.student_id
            if raw and not raw.startswith("gAAAAA"):
                self.student_id_hash = hashlib.sha256(
                    raw.encode("utf-8")
                ).hexdigest()
        super().save(**kwargs)

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_lecturer(self):
        return self.role == self.Role.LECTURER

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN

    def has_consent(self, purpose):
        from privacy.services import has_consent
        return has_consent(self, purpose)


class StudentClass(models.Model):
    name = models.CharField(max_length=50)
    academic_year = models.CharField(max_length=9)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_student_class"

    def __str__(self):
        return f"{self.name} ({self.academic_year})"


class ClassMembership(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="class_memberships")
    student_class = models.ForeignKey(StudentClass, on_delete=models.CASCADE, related_name="memberships")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_class_membership"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "student_class"],
                name="uq_membership_student_class",
            ),
        ]


class LecturerClassAssignment(models.Model):
    lecturer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="class_assignments")
    student_class = models.ForeignKey(StudentClass, on_delete=models.CASCADE, related_name="lecturer_assignments")
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "palp_lecturer_class_assignment"
        constraints = [
            models.UniqueConstraint(
                fields=["lecturer", "student_class"],
                name="uq_lecturer_class",
            ),
        ]
