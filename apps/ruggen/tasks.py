from celery import shared_task
from django.db.models import F
from google.genai import errors as genai_errors

from .models import GeneratedRugImage, GenerationQuota, RugGeneration
from .utils.gemini import generate_rug_images


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_rug_images_task(self, generation_id, style, colors, material, size, description=''):
    try:
        images = generate_rug_images(style, colors, material, size, description)
    except genai_errors.ServerError as exc:
        countdown = 60 * (self.request.retries + 1)
        raise self.retry(exc=exc, countdown=countdown)
    except Exception as exc:
        RugGeneration.objects.filter(id=generation_id).update(status='failed', error_message=str(exc))
        return

    try:
        generation = RugGeneration.objects.get(id=generation_id)
    except RugGeneration.DoesNotExist:
        return

    for i, img in enumerate(images):
        GeneratedRugImage.objects.create(
            generation=generation,
            index=i,
            base64_data=img['base64'],
            mime_type=img['mime_type'],
        )

    generation.status = 'generated' if images else 'failed'
    generation.save()

    if images:
        GenerationQuota.objects.filter(email=generation.email).update(count=F('count') + 1)
