"""
utils/gemini.py

Stage 1 — generate_rug_images()
    Gemini Imagen 3 → generates 4 rug product images from style/color/material params.

Stage 2 — place_rug_in_room()
    Gemini 2.0 Flash (vision + image editing) → takes room photo + rug image,
    composites the rug into the room realistically.
"""
import base64
import logging
from io import BytesIO
from typing import List

from django.conf import settings
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from PIL import Image
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log,
)

from .watermark import apply_watermark

logger = logging.getLogger(__name__)


def _client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)


# Retry only on transient server-side errors, not on bad requests (400s)
RETRYABLE_ERRORS = (genai_errors.ServerError,)


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(RETRYABLE_ERRORS),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def _generate_images_with_retry(client, model, prompt, config):
    return client.models.generate_images(model=model, prompt=prompt, config=config)


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(RETRYABLE_ERRORS),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def _generate_content_with_retry(client, model, contents, config):
    return client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )


# ─────────────────────────────────────────────
# STAGE 1 — Rug Design Generation
# ─────────────────────────────────────────────
def build_rug_prompt(style: str, colors: List[str], material: str, size: str, description: str = '') -> str:
    colors_str = ', '.join(colors) if colors else 'neutral tones'
    desc = f' Design detail: {description}.' if description else ''
    return (
        f"A high-quality e-commerce product photograph of a {style} style area rug, "
        f"size {size}, made of {material}. "
        f"Color palette: {colors_str}.{desc} "
        f"Top-down overhead flat lay view, camera directly above, no angle or perspective. "
        f"Rug only, on a seamless white background, no other objects or subjects in frame. "
        f"Sharp focus, studio lighting, photorealistic, professional product photography."
    )

def generate_rug_images(
    style: str,
    colors: List[str],
    material: str,
    size: str,
    description: str = '',
    num_images: int = 4,
) -> List[dict]:
    client = _client()
    prompt = build_rug_prompt(style, colors, material, size, description)

    logger.info("Generating %d rug images | style=%s material=%s", num_images, style, material)

    try:
        response = _generate_images_with_retry(
            client,
            settings.GEMINI_IMAGEN_MODEL,
            prompt,
            types.GenerateImagesConfig(
                number_of_images=num_images,
                aspect_ratio='1:1',
                output_mime_type='image/jpeg',
                person_generation='DONT_ALLOW',   # <-- key fix, blocks humans at generation level
            ),
        )
    except genai_errors.ServerError as e:
        logger.error("Imagen unavailable after retries: %s", e)
        raise

    results = []
    for img_data in response.generated_images:
        pil_img = Image.open(BytesIO(img_data.image.image_bytes))
        watermarked = apply_watermark(pil_img, settings.WATERMARK_TEXT)

        buf = BytesIO()
        watermarked.save(buf, 'JPEG', quality=90)
        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        results.append({'base64': b64, 'mime_type': 'image/jpeg'})

    return results

# ─────────────────────────────────────────────
# STAGE 2 — Place Rug in Room
# ─────────────────────────────────────────────

def place_rug_in_room(room_image_b64: str, rug_image_b64: str) -> str:
    """
    Takes room photo + rug image (both base64).
    Uses Gemini 2.0 Flash multimodal to composite the rug into the room.
    Returns base64 of the result image.
    """
    client = _client()

    room_bytes = base64.b64decode(room_image_b64)
    rug_bytes = base64.b64decode(rug_image_b64)

    prompt = (
        "You are an interior design visualization AI. "
        "I have provided two images:\n"
        "1. A room photo (the user's actual room)\n"
        "2. A rug product photo (flat lay on white background)\n\n"
        "Your task: Generate a new image that shows the room with the rug naturally placed on the floor. "
        "The rug should:\n"
        "- Be positioned realistically on the floor in the center/main area\n"
        "- Match the perspective and angle of the room photo\n"
        "- Have realistic shadows and lighting that match the room\n"
        "- Look like the rug is actually in the room, not photoshopped\n"
        "- Maintain the rug's colors, pattern, and design accurately\n"
        "Output only the final room image with the rug placed in it."
    )

    room_part = types.Part.from_bytes(data=room_bytes, mime_type='image/jpeg')
    rug_part = types.Part.from_bytes(data=rug_bytes, mime_type='image/jpeg')

    logger.info("Placing rug in room via Gemini vision...")

    try:
        response = _generate_content_with_retry(
            client,
            settings.GEMINI_VISION_MODEL,
            [
                types.Content(
                    role='user',
                    parts=[
                        types.Part.from_text(text="Room photo:"),
                        room_part,
                        types.Part.from_text(text="Rug to place in the room:"),
                        rug_part,
                        types.Part.from_text(text=prompt),
                    ],
                )
            ],
            types.GenerateContentConfig(
                response_modalities=['IMAGE', 'TEXT'],
            ),
        )
    except genai_errors.ServerError as e:
        logger.error("Room placement unavailable after retries: %s", e)
        raise

    # Extract image from response
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            result_b64 = base64.b64encode(part.inline_data.data).decode('utf-8')
            logger.info("Room placement image generated successfully")
            return result_b64

    raise ValueError("Gemini did not return an image for room placement. Try gemini-2.0-flash-preview-image-generation model.")
