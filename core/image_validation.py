from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


def validate_product_image(upload):
    """Admit only small, decodable photographs with matching type and extension."""
    formats = {'JPEG': ({'.jpg', '.jpeg'}, 'image/jpeg'), 'PNG': ({'.png'}, 'image/png'), 'WEBP': ({'.webp'}, 'image/webp')}
    if upload.size > 5 * 1024 * 1024:
        raise ValidationError('La imagen no debe superar 5 MiB.')
    try:
        upload.seek(0)
        with Image.open(upload) as image:
            allowed = formats.get(image.format)
            if not allowed or Path(upload.name).suffix.lower() not in allowed[0]:
                raise ValidationError('Usá una fotografía JPEG, PNG o WebP con la extensión correcta.')
            if getattr(upload, 'content_type', None) not in (None, allowed[1]):
                raise ValidationError('El tipo de archivo no coincide con la imagen.')
            if image.width * image.height > 20_000_000:
                raise ValidationError('La imagen supera el límite de 20 megapíxeles.')
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValidationError('El archivo no es una imagen válida.') from exc
    finally:
        upload.seek(0)
