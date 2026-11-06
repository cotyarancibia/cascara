"""Serializers de autenticación y perfil de usuario."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer para el registro de nuevos clientes.

    El rol se asigna siempre desde el servidor como CLIENTE. Nunca se
    acepta el rol desde el cliente, impidiendo autopromoción a ADMIN o
    VENDEDOR.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password',
            'password_confirm',
            'telefono',
            'direccion',
        ]
        extra_kwargs = {
            'email': {'required': True},
        }

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "Este nombre de usuario ya está en uso."
            )
        return value

    def validate(self, data):
        if data.get('password') != data.pop('password_confirm'):
            raise serializers.ValidationError(
                {"password_confirm": "Las contraseñas no coinciden."}
            )
        user = User(username=data.get('username', ''), email=data.get('email', ''))
        try:
            validate_password(data['password'], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': list(exc.messages)})
        return data

    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            telefono=validated_data.get('telefono', ''),
            direccion=validated_data.get('direccion', ''),
            role=User.Role.CLIENTE,
        )
        # Guardar la contraseña mediante el mecanismo seguro de Django (hash),
        # nunca como texto plano.
        user.set_password(validated_data['password'])
        user.save()
        return user


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer del perfil del usuario autenticado.

    No expone la contraseña ni información sensible.
    """

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'role',
            'telefono',
            'direccion',
        ]
        read_only_fields = fields


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)
