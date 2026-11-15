from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from users.serializers import RegisterSerializer


class AuthRegressionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        get_user_model().objects.create_user('cliente', 'cliente@example.com', 'clave-ficticia-2384')

    def register(self, username, email):
        data = {'username': username, 'email': email, 'password': 'clave-ficticia-2384', 'password_confirm': 'clave-ficticia-2384'}
        return self.client.post('/api/auth/register/', data, format='json')

    def test_registro_y_duplicados(self):
        self.assertEqual(self.register('nuevo', 'nuevo@example.com').status_code, 201)
        self.assertEqual(self.register('nuevo', 'otro@example.com').status_code, 400)
        self.assertEqual(self.register('otro', 'NUEVO@example.com').status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username='otro').exists())

    def test_carrera_username_se_convierte_en_error_400(self):
        with patch('rest_framework.validators.UniqueValidator.__call__'), patch.object(RegisterSerializer, 'validate_username', side_effect=lambda value: value):
            response = self.register('cliente', 'distinto@example.com')
        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.data)

    def test_login_refresh_y_logout(self):
        bad = self.client.post('/api/auth/login/', {'username': 'cliente', 'password': 'incorrecta'}, format='json')
        unknown = self.client.post('/api/auth/login/', {'username': 'inexistente', 'password': 'incorrecta'}, format='json')
        self.assertEqual((bad.status_code, unknown.status_code), (401, 401))
        self.assertEqual(bad.data, unknown.data)
        self.assertNotIn('incorrecta', str(bad.data))
        ok = self.client.post('/api/auth/login/', {'username': 'cliente', 'password': 'clave-ficticia-2384'}, format='json')
        self.assertEqual(ok.status_code, 200)
        refreshed = self.client.post('/api/auth/refresh/', {'refresh': ok.data['refresh']}, format='json')
        self.assertEqual(refreshed.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refreshed.data['access']}")
        logout = self.client.post('/api/auth/logout/', {'refresh': refreshed.data['refresh']}, format='json')
        self.assertEqual(logout.status_code, 205)
        self.client.credentials()
        self.assertEqual(self.client.post('/api/auth/refresh/', {'refresh': refreshed.data['refresh']}, format='json').status_code, 401)
