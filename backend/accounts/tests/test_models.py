import pytest
from django.db import IntegrityError

from accounts.models import User, StudentClass, ClassMembership, LecturerClassAssignment

pytestmark = pytest.mark.django_db


class TestUserRoleProperties:
    def test_student_role_flags(self, student):
        assert student.is_student is True
        assert student.is_lecturer is False
        assert student.is_admin_user is False

    def test_lecturer_role_flags(self, lecturer):
        assert lecturer.is_lecturer is True
        assert lecturer.is_student is False
        assert lecturer.is_admin_user is False

    def test_admin_role_flags(self, admin_user):
        assert admin_user.is_admin_user is True
        assert admin_user.is_student is False
        assert admin_user.is_lecturer is False


class TestUserStudentIdIndex:
    def test_student_id_field_is_indexed(self):
        hash_field = User._meta.get_field("student_id_hash")
        assert hash_field.db_index is True


class TestStudentClassStr:
    def test_str_representation(self, student_class):
        assert str(student_class) == "SBVL-01 (2025-2026)"


class TestClassMembershipUniqueTogether:
    def test_duplicate_membership_raises(self, student, student_class):
        ClassMembership.objects.create(student=student, student_class=student_class)
        with pytest.raises(IntegrityError):
            ClassMembership.objects.create(student=student, student_class=student_class)


class TestLecturerClassAssignmentUniqueTogether:
    def test_duplicate_assignment_raises(self, lecturer, student_class):
        LecturerClassAssignment.objects.create(lecturer=lecturer, student_class=student_class)
        with pytest.raises(IntegrityError):
            LecturerClassAssignment.objects.create(lecturer=lecturer, student_class=student_class)
