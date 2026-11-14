from unittest.mock import patch
import ipaddress

from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import override_settings
from redis.exceptions import ConnectionError as RedisConnectionError
from rest_framework.test import APITestCase

from users.serializers import RegisterSerializer
from users.throttles import LoginOriginThrottle


@override_settings(AUTH_THROTTLE_ENABLED=True)
class AuthThrottleTests(APITestCase):
    def setUp(self):
        caches['auth_throttle'].clear()
        self.user = get_user_model().objects.create_user('cliente', 'cliente@example.com', 'clave-ficticia-2384')

    def tearDown(self):
        caches['auth_throttle'].clear()

    def login(self, username='cliente', password='incorrecta', **extra):
        return self.client.post('/api/auth/login/', {'username': username, 'password': password}, format='json', **extra)

    def register(self, username, email, **extra):
        data = {'username': username, 'email': email, 'password': 'clave-ficticia-2384', 'password_confirm': 'clave-ficticia-2384'}
        return self.client.post('/api/auth/register/', data, format='json', **extra)

    def test_login_refresh_y_credenciales_invalidas_uniformes(self):
        bad = self.login()
        unknown = self.login(username='inexistente')
        self.assertEqual((bad.status_code, unknown.status_code), (401, 401))
        self.assertEqual(bad.data, unknown.data)
        self.assertNotIn('incorrecta', str(bad.data))
        ok = self.login(password='clave-ficticia-2384')
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(self.client.post('/api/auth/refresh/', {'refresh': ok.data['refresh']}, format='json').status_code, 200)

    def test_limite_por_origen_y_cuenta_sin_bloqueo_global(self):
        for _ in range(8):
            self.assertEqual(self.login().status_code, 401)
        blocked = self.login()
        self.assertEqual(blocked.status_code, 429)
        self.assertIn('Retry-After', blocked)
        self.assertNotIn('incorrecta', str(blocked.data))
        self.assertEqual(self.login(username='otra').status_code, 401)
        self.assertEqual(self.login(REMOTE_ADDR='192.0.2.12').status_code, 401)
        self.assertEqual(self.login(HTTP_X_FORWARDED_FOR='192.0.2.99').status_code, 429)

    def test_registro_normal_duplicados_y_limite(self):
        self.assertEqual(self.register('nuevo', 'nuevo@example.com').status_code, 201)
        self.assertEqual(self.register('nuevo', 'otro@example.com').status_code, 400)
        self.assertEqual(self.register('otro', 'NUEVO@example.com').status_code, 400)
        self.assertEqual(self.register('tercero', 'tercero@example.com').status_code, 201)
        self.assertEqual(self.register('cuarto', 'cuarto@example.com').status_code, 201)
        self.assertEqual(self.register('quinto', 'quinto@example.com').status_code, 429)
        self.assertFalse(get_user_model().objects.filter(username='quinto').exists())

    def test_limite_por_origen_tambien_frena_distintas_cuentas(self):
        with patch.object(LoginOriginThrottle, 'rate', '2/min'):
            self.assertEqual(self.login(username='primero').status_code, 401)
            self.assertEqual(self.login(username='segundo').status_code, 401)
            self.assertEqual(self.login(username='tercero').status_code, 429)

    def test_carrera_username_se_convierte_en_error_400(self):
        with patch('rest_framework.validators.UniqueValidator.__call__'), patch.object(RegisterSerializer, 'validate_username', side_effect=lambda value: value):
            response = self.register('cliente', 'distinto@example.com')
        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.data)

    def test_cierre_seguro_si_cache_falla(self):
        with patch.object(caches['auth_throttle'], 'get', side_effect=RedisConnectionError('no disponible')):
            self.assertEqual(self.login().status_code, 503)

    @override_settings(IS_PRODUCTION=True, AUTH_TRUSTED_PROXIES=[ipaddress.ip_network('10.0.0.0/24')])
    def test_solo_proxy_confiable_puede_indicar_ip(self):
        self.assertEqual(self.login(REMOTE_ADDR='192.0.2.1', HTTP_X_REAL_IP='192.0.2.2').status_code, 503)
        self.assertEqual(self.login(REMOTE_ADDR='10.0.0.1', HTTP_X_REAL_IP='192.0.2.2').status_code, 401)
        self.assertEqual(self.login(REMOTE_ADDR='10.0.0.1', HTTP_X_REAL_IP='invalida').status_code, 503)
