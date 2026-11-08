from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APITestCase

from users.serializers import RegisterSerializer


User = get_user_model()


class RegistroEmailTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(username='existente', email='  Cliente@Ejemplo.com  ')

    def registrar(self, email, username='nuevo'):
        return self.client.post('/api/auth/register/', {
            'username': username,
            'email': email,
            'password': 'ClaveSegura99!',
            'password_confirm': 'ClaveSegura99!',
        }, format='json')

    def test_registro_exitoso_con_email_normalizado(self):
        response = self.registrar('  nuevo@example.com  ')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.get(username='nuevo').email, 'nuevo@example.com')
        self.assertNotIn('password', response.data)

    def test_email_duplicado_y_variantes_se_rechazan(self):
        for email in ('  Cliente@Ejemplo.com  ', 'cliente@ejemplo.com', '  CLIENTE@EJEMPLO.COM  '):
            with self.subTest(email=email):
                response = self.registrar(email)
                self.assertEqual(response.status_code, 400)
                self.assertIn('email', response.data)
                self.assertFalse(User.objects.filter(username='nuevo').exists())

    def test_conflicto_de_unicidad_en_guardado_devuelve_400(self):
        # Simula que otra solicitud insertó el email después de la validación.
        with patch.object(RegisterSerializer, 'validate_email', side_effect=lambda value: value):
            response = self.registrar('cliente@ejemplo.com')
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)
        self.assertFalse(User.objects.filter(username='nuevo').exists())


class RestriccionEmailTests(TestCase):
    def test_la_base_impide_variantes_con_espacios_y_mayusculas(self):
        User.objects.create_user(username='primero', email='  Cliente@ejemplo.com ')
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(username='segundo', email='cliente@EJEMPLO.COM')

    def test_varios_usuarios_sin_email_se_conservan(self):
        User.objects.create_user(username='sin_email_1', email='')
        User.objects.create_user(username='sin_email_2', email='')
        User.objects.create_user(username='sin_email_3', email='   ')
        User.objects.create_user(username='sin_email_4', email='   ')
        self.assertEqual(User.objects.filter(username__startswith='sin_email_').count(), 4)
