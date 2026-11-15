"""Vistas de autenticación, perfil y logout (JWT)."""

from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from drf_spectacular.utils import extend_schema

from .serializers import RegisterSerializer, ProfileSerializer, LogoutSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/

    Permite registrar nuevos clientes. El rol se asigna siempre como CLIENTE
    desde el servidor; nunca se acepta un rol enviado por el cliente.
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class ProfileView(generics.RetrieveUpdateAPIView):
    """GET /api/auth/profile/

    Devuelve los datos del usuario autenticado. No permite consultar el
    perfil privado de otros usuarios ni expone la contraseña.
    """

    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    """POST /api/auth/logout/

    Revoca el refresh token añadiéndolo a la blacklist (token_blacklist).
    Nota: revocar el refresh token no invalida automáticamente un access
    token que aún no haya expirado.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=LogoutSerializer, responses={205: None, 400: None, 403: None})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data['refresh'])
            if str(token.get(api_settings.USER_ID_CLAIM)) != str(request.user.pk):
                return Response(status=status.HTTP_403_FORBIDDEN)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except TokenError:
            return Response(status=status.HTTP_400_BAD_REQUEST)


# Reutilizamos TokenObtainPairView y TokenRefreshView de simplejwt.
# Por defecto solo devuelven 'access' y 'refresh', sin incluir la
# contraseña ni información sensible.
CustomTokenObtainPairView = TokenObtainPairView
CustomTokenRefreshView = TokenRefreshView
