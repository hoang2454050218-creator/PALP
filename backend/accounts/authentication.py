from rest_framework_simplejwt.authentication import JWTAuthentication


class CookieJWTAuthentication(JWTAuthentication):
    """
    Reads JWT from HttpOnly cookie first, falls back to Authorization header.
    """

    COOKIE_NAME = "palp_access"

    def authenticate(self, request):
        raw_token = request.COOKIES.get(self.COOKIE_NAME)
        if raw_token:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token

        return super().authenticate(request)
