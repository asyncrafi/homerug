from celery import shared_task
from google.genai import errors as genai_errors

from .utils.gemini import generate_rug_images


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_rug_images_task(self, style, colors, material, size, description=''):
    try:
        return generate_rug_images(style, colors, material, size, description)
    except genai_errors.ServerError as exc:
        countdown = 60 * (self.request.retries + 1)
        raise self.retry(exc=exc, countdown=countdown)
