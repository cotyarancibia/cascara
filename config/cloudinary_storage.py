"""Django media storage backed by Cloudinary's official Python SDK."""
from pathlib import PurePosixPath
from urllib.request import urlopen
from uuid import uuid4

import cloudinary.api
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class CloudinaryMediaStorage(Storage):
    def get_available_name(self, name, max_length=None):
        extension = PurePosixPath(name).suffix.lower()
        name = f'productos/{uuid4().hex}{extension}'
        if max_length and len(name) > max_length:
            raise ValueError('El nombre de imagen excede el máximo permitido.')
        return name

    def _save(self, name, content):
        path = PurePosixPath(name)
        result = cloudinary.uploader.upload(content, public_id=str(path.with_suffix('')), resource_type='image', overwrite=False, use_filename=False)
        return f"{result['public_id']}.{result['format']}"

    def url(self, name):
        path = PurePosixPath(name)
        return cloudinary_url(str(path.with_suffix('')), format=path.suffix.lstrip('.'), secure=True)[0]

    def _open(self, name, mode='rb'):
        if mode != 'rb':
            raise ValueError('Solo se admite lectura binaria de imágenes.')
        with urlopen(self.url(name), timeout=10) as response:
            data = response.read(5 * 1024 * 1024 + 1)
        if len(data) > 5 * 1024 * 1024:
            raise ValueError('La imagen almacenada supera el límite de tamaño.')
        return ContentFile(data, name=PurePosixPath(name).name)

    def exists(self, name):
        try:
            cloudinary.api.resource(str(PurePosixPath(name).with_suffix('')), resource_type='image')
            return True
        except cloudinary.api.NotFound:
            return False

    def delete(self, name):
        cloudinary.uploader.destroy(str(PurePosixPath(name).with_suffix('')), resource_type='image')
