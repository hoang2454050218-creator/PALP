from django.conf import settings
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import User, StudentClass, ClassMembership
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserSerializer,
    UserCreateSerializer,
    StudentClassSerializer,
    ConsentSerializer,
)
from .permissions import IsLecturerOrAdmin, IsClassMember
from palp.throttles import LoginThrottle, RegisterThrottle

IS_SECURE = not getattr(settings, "DEBUG", True)
COOKIE_SAMESITE = "Strict" if IS_SECURE else "Lax"


def _set_auth_cookies(response, access, refresh):
    access_max_age = int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())
    refresh_max_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())

    response.set_cookie(
        "palp_access",
        access,
        max_age=access_max_age,
        httponly=True,
        secure=IS_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )
    response.set_cookie(
        "palp_refresh",
        refresh,
        max_age=refresh_max_age,
        httponly=True,
        secure=IS_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/api/auth/",
    )


def _clear_auth_cookies(response):
    response.delete_cookie("palp_access", path="/")
    response.delete_cookie("palp_refresh", path="/api/auth/")


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = (LoginThrottle,)

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            _set_auth_cookies(
                response,
                response.data["access"],
                response.data["refresh"],
            )
        return response


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = (AllowAny,)
    throttle_classes = (RegisterThrottle,)


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        refresh_token = (
            request.data.get("refresh")
            or request.COOKIES.get("palp_refresh")
        )
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass

        response = Response(
            {"detail": "Đăng xuất thành công."},
            status=status.HTTP_200_OK,
        )
        _clear_auth_cookies(response)
        return response


class TokenRefreshCookieView(APIView):
    """Refresh using the HttpOnly cookie instead of request body."""

    authentication_classes = ()
    permission_classes = (AllowAny,)

    def post(self, request):
        refresh_token = (
            request.data.get("refresh")
            or request.COOKIES.get("palp_refresh")
        )
        if not refresh_token:
            return Response(
                {"detail": "No refresh token provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            new_access = str(token.access_token)
            new_refresh = str(token) if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS") else refresh_token

            response = Response({"access": new_access, "refresh": new_refresh})
            _set_auth_cookies(response, new_access, new_refresh)
            return response
        except TokenError:
            response = Response(
                {"detail": "Token không hợp lệ hoặc đã hết hạn."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            _clear_auth_cookies(response)
            return response


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


class ConsentView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ConsentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.consent_given = serializer.validated_data["consent_given"]
        request.user.consent_given_at = timezone.now() if serializer.validated_data["consent_given"] else None
        request.user.save(update_fields=["consent_given", "consent_given_at"])
        return Response(UserSerializer(request.user).data)


class StudentClassListView(generics.ListCreateAPIView):
    queryset = StudentClass.objects.all()
    serializer_class = StudentClassSerializer
    permission_classes = (IsLecturerOrAdmin,)


class ClassStudentsView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsLecturerOrAdmin, IsClassMember)

    def get_queryset(self):
        class_id = self.kwargs["class_id"]
        return User.objects.filter(
            class_memberships__student_class_id=class_id,
            role=User.Role.STUDENT,
        )


class HealthCheckView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        return Response({"status": "ok"}, status=status.HTTP_200_OK)
