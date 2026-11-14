from unittest.mock import patch
import os
import subprocess
import sys
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.test import override_settings
from PIL import Image
from rest_framework.test import APIClient

from config.cloudinary_storage import CloudinaryMediaStorage
from core.models import Category, Product
from core.serializers import ProductSerializer


class DeploymentTests(SimpleTestCase):
    def test_public_health(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok', 'service': 'api'})

    def test_documentation_pages_are_public(self):
        self.assertEqual(self.client.get('/api/docs/').status_code, 200)
        self.assertEqual(self.client.get('/api/redoc/').status_code, 200)

    @patch('config.cloudinary_storage.cloudinary_url')
    @patch('config.cloudinary_storage.cloudinary.uploader.upload')
    def test_media_storage_uses_sdk_and_https(self, upload, build_url):
        upload.return_value = {'public_id': 'productos/test-id', 'format': 'png'}
        build_url.return_value = ('https://res.cloudinary.com/test/image/upload/productos/test-id.png', {})
        storage = CloudinaryMediaStorage()
        name = storage.save('original.png', ContentFile(b'test'))
        self.assertEqual(name, 'productos/test-id.png')
        self.assertTrue(storage.url(name).startswith('https://'))
        self.assertFalse(upload.call_args.kwargs['overwrite'])

    @patch('config.cloudinary_storage.urlopen')
    @patch('config.cloudinary_storage.cloudinary_url')
    def test_media_reads_are_bounded(self, build_url, open_url):
        build_url.return_value = ('https://res.cloudinary.com/demo/image/upload/productos/foto.png', {})
        open_url.return_value.__enter__.return_value.read.return_value = b'x' * (5 * 1024 * 1024 + 1)
        with self.assertRaises(ValueError):
            CloudinaryMediaStorage().open('productos/foto.png')

    @override_settings(STORAGES={'default': {'BACKEND': 'config.cloudinary_storage.CloudinaryMediaStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
    @patch('config.cloudinary_storage.cloudinary_url')
    def test_product_serializer_returns_media_url(self, build_url):
        build_url.return_value = ('https://res.cloudinary.com/demo/image/upload/productos/foto.png', {})
        product = Product(nombre='Prueba', precio='1.00', imagen='productos/foto.png')
        self.assertEqual(ProductSerializer(product).data['imagen_url'], build_url.return_value[0])

    def test_production_settings_fail_closed(self):
        code = "import dotenv; dotenv.load_dotenv=lambda *a, **k: False; import config.settings"
        env = os.environ.copy()
        env.update({'CASCARA_ENV': 'production', 'CASCARA_DB_MODE': 'postgresql', 'DJANGO_SECRET_KEY': 'x' * 64,
                    'DJANGO_DEBUG': 'False', 'DJANGO_ALLOWED_HOSTS': 'api.example.test',
                    'DJANGO_CSRF_TRUSTED_ORIGINS': 'https://api.example.test',
                    'DJANGO_CORS_ALLOWED_ORIGINS': 'https://web.example.test',
                    'DATABASE_URL': 'postgresql://test:test@127.0.0.1:5432/test',
                    'CLOUDINARY_URL': 'cloudinary://test:test@demo',
                    'AUTH_REDIS_URL': 'redis://127.0.0.1:6379/0', 'AUTH_TRUSTED_PROXIES': '10.0.0.0/24'})
        def run(values):
            return subprocess.run([sys.executable, '-B', '-c', code], env={**env, **values}, capture_output=True).returncode
        self.assertEqual(run({}), 0)
        for values in ({'DJANGO_DEBUG': 'True'}, {'DJANGO_SECRET_KEY': ''}, {'DJANGO_ALLOWED_HOSTS': '*'}, {'CLOUDINARY_URL': ''},
                       {'DATABASE_URL': ''}, {'DATABASE_URL': 'sqlite:///test.sqlite3'}, {'DJANGO_CORS_ALLOWED_ORIGINS': 'http://example.test'},
                       {'DJANGO_CSRF_TRUSTED_ORIGINS': 'http://api.example.test'}, {'CASCARA_DB_MODE': 'sqlite'},
                       {'CASCARA_ENV': 'development', 'RAILWAY_PROJECT_ID': 'test'}, {'AUTH_REDIS_URL': ''},
                       {'AUTH_TRUSTED_PROXIES': ''}, {'AUTH_TRUSTED_PROXIES': '0.0.0.0/0'}):
            with self.subTest(values=values):
                self.assertNotEqual(run(values), 0)


@override_settings(STORAGES={'default': {'BACKEND': 'config.cloudinary_storage.CloudinaryMediaStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class CloudinaryUploadTests(TestCase):
    @patch('config.cloudinary_storage.cloudinary_url')
    @patch('config.cloudinary_storage.cloudinary.uploader.upload')
    def test_authorized_product_upload_uses_storage_and_returns_url(self, upload, build_url):
        upload.return_value = {'public_id': 'productos/foto-test', 'format': 'png'}
        build_url.return_value = ('https://res.cloudinary.com/demo/image/upload/productos/foto-test.png', {})
        output = BytesIO()
        Image.new('RGB', (2, 2), 'red').save(output, format='PNG')
        photo = SimpleUploadedFile('foto.png', output.getvalue(), content_type='image/png')
        category = Category.objects.create(nombre='Prueba')
        admin = get_user_model().objects.create_user('admin_prueba', role='ADMIN')
        client = APIClient()
        client.force_authenticate(admin)
        response = client.post('/api/productos/', {'nombre': 'Producto', 'categoria': category.pk, 'precio': '10.00', 'imagen': photo}, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['imagen_url'], build_url.return_value[0])
        self.assertEqual(Product.objects.get(pk=response.data['id']).imagen.name, 'productos/foto-test.png')
        self.assertEqual(upload.call_count, 1)
