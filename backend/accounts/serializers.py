from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, StudentClass, ClassMembership


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["full_name"] = user.get_full_name()
        return token


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id", "username", "email", "first_name", "last_name",
            "role", "student_id", "phone", "avatar_url",
            "consent_given", "consent_given_at", "created_at",
        )
        read_only_fields = ("id", "created_at")


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = (
            "username", "email", "password", "first_name", "last_name",
            "student_id", "phone",
        )

    def create(self, validated_data):
        validated_data["role"] = User.Role.STUDENT
        return User.objects.create_user(**validated_data)


class StudentClassSerializer(serializers.ModelSerializer):
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = StudentClass
        fields = ("id", "name", "academic_year", "student_count", "created_at")

    def get_student_count(self, obj):
        return obj.memberships.count()


class ClassMembershipSerializer(serializers.ModelSerializer):
    student = UserSerializer(read_only=True)

    class Meta:
        model = ClassMembership
        fields = ("id", "student", "student_class", "joined_at")


class ConsentSerializer(serializers.Serializer):
    consent_given = serializers.BooleanField()
