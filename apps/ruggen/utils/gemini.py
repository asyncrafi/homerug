"""
utils/gemini.py

generate_rug_images()
    Gemini 3.1 Flash Image ("Nano Banana 2") -> generates rug product images from
    style/color/material params.

    Imagen 4 is deprecated and shuts down 2026-08-17, so generation now goes through
    client.models.generate_content() instead of client.models.generate_images().

    Gemini image models reject candidate_count > 1, so we can't ask for N images in
    one call -- each call returns exactly one image, and we loop until we have
    `num_images` images that pass QC.

    QC validation (_validate_rug_image) rejects anything that isn't a clean top-down
    flat-lay rug on a white background before it's watermarked or counted toward the
    result -- this is what stops off-topic generations (angled room shots, unrelated
    objects) from ever reaching a client.

Room-placement stage has been removed. This module now only does generation.
"""
import base64
import json
import logging
import math
import re
from io import BytesIO
from typing import List, Tuple

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
def _generate_content_with_retry(client, model, contents, config):
    return client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )


# ─────────────────────────────────────────────
# QC validation — runs on every raw image before it's ever watermarked
# or shown to a user. Rejects anything that isn't a top-down flat rug.
# ─────────────────────────────────────────────

RUG_VALIDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "is_valid": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["is_valid", "reason"],
}


def _validate_rug_image(client, image_bytes: bytes) -> Tuple[bool, str]:
    """Reject anything that isn't a single top-down flat-lay rug on white background."""
    prompt = (
        "Look at this image. Answer strictly: is this a single rectangular "
        "area rug, photographed from directly overhead (bird's eye, ~90 degrees), "
        "lying flat, on a plain white/seamless background, with no room, no "
        "furniture, no people, and no unrelated objects (fruit, animals, etc)? "
        "It must fill most of the frame and show a clear rug pattern. "
        "If it shows any angle other than top-down, any room context, or "
        "anything that isn't a rug, is_valid must be false."
    )
    try:
        response = _generate_content_with_retry(
            client,
            settings.GEMINI_VALIDATION_MODEL,
            [types.Content(role='user', parts=[
                types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'),
                types.Part.from_text(text=prompt),
            ])],
            types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=RUG_VALIDATION_SCHEMA,
            ),
        )
        result = json.loads(response.text)
        return bool(result['is_valid']), result.get('reason', '')
    except Exception as e:
        # If the validator itself fails, don't let a bad image slip through silently
        logger.warning("Rug validation call failed, rejecting image: %s", e)
        return False, 'validation_error'


# ─────────────────────────────────────────────
# Rug Design Generation
# ─────────────────────────────────────────────
def get_aspect_ratio_for_size(size: str) -> str:
    """Convert a size like '2.5x6 ft' into a Gemini-friendly aspect ratio string."""
    nums = re.findall(r"[\d]+(?:\.[\d]+)?", size)
    if len(nums) < 2:
        return '1:1'

    width = float(nums[0])
    height = float(nums[1])
    if width <= 0 or height <= 0:
        return '1:1'

    width_scaled = int(round(width * 1000))
    height_scaled = int(round(height * 1000))
    gcd = math.gcd(width_scaled, height_scaled)
    return f"{width_scaled // gcd}:{height_scaled // gcd}"


def build_rug_prompt(style: str, colors: List[str], material: str, size: str, description: str = '', shape: str = 'rectangular') -> str:
    colors_str = ', '.join(colors) if colors else 'neutral tones'
    desc = f' Design detail: {description}.' if description.strip() else ''
    shape_descriptor = 'round' if shape == 'round' else 'rectangular'
    prompt_shape = 'a round rug' if shape == 'round' else 'a rectangular rug'
    return (
        f"Create {prompt_shape} in a {style} style, size {size}, made of {material}, "
        f"lying completely flat and fully unfolded on the floor, photographed from directly overhead "
        f"at a 90-degree bird's eye angle. Color palette: {colors_str}.{desc} "
        f"The rug must be {shape_descriptor}, flat, and fill most of the frame edge to edge, showing its full pattern. "
        f"Use a {shape_descriptor} silhouette, not a rectangle if round shape is requested. "
        f"Plain seamless white background. No camera equipment, no tripods, no stands, no studio gear visible. "
        f"No bags, pouches, wallets, cushions, or rolled/folded textiles — this is a full-size flat floor rug only. "
        f"No people, no furniture, no room, no props. Clean e-commerce catalog photo, sharp focus, even lighting."
    )


def _generate_single_rug_image(client, prompt: str, aspect_ratio: str = '1:1') -> bytes:
    """
    One API call = one image. Gemini image models (2.5 and 3.x) reject
    candidate_count > 1 with a 400 error, so batching happens by looping
    this call, not by asking for more candidates in one request.
    """
    response = _generate_content_with_retry(
        client,
        settings.GEMINI_IMAGEN_MODEL,
        [types.Content(role='user', parts=[types.Part.from_text(text=prompt)])],
        types.GenerateContentConfig(
            response_modalities=['IMAGE'],
            image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
        ),
    )

    candidates = getattr(response, 'candidates', None)
    if not candidates:
        raise ValueError("No candidates returned (likely RAI-filtered)")

    for part in candidates[0].content.parts:
        if part.inline_data is not None:
            return part.inline_data.data

    raise ValueError("Model returned no image data")


def generate_rug_images(
    style: str,
    colors: List[str],
    material: str,
    size: str,
    description: str = '',
    shape: str = 'rectangular',
    num_images: int = 4,
) -> List[dict]:
    client = _client()
    aspect_ratio = get_aspect_ratio_for_size(size)
    prompt = build_rug_prompt(style, colors, material, size, description, shape)

    logger.info("Generating %d rug images | style=%s material=%s", num_images, style, material)

    results = []
    attempts = 0
    # Generous budget: QC rejection means some attempts won't count, so allow
    # more attempts than images needed rather than failing the whole batch.
    max_attempts = num_images * 3

    while len(results) < num_images and attempts < max_attempts:
        attempts += 1

        try:
            raw_bytes = _generate_single_rug_image(client, prompt, aspect_ratio)
        except genai_errors.ServerError as e:
            logger.error("Nano Banana unavailable after retries: %s", e)
            raise
        except ValueError as e:
            logger.warning("Attempt %d/%d produced no usable image: %s", attempts, max_attempts, e)
            continue

        is_valid, reason = _validate_rug_image(client, raw_bytes)
        if not is_valid:
            logger.warning("Rejected non-rug image on attempt %d/%d: %s", attempts, max_attempts, reason)
            continue

        pil_img = Image.open(BytesIO(raw_bytes))
        watermarked = apply_watermark(pil_img, settings.WATERMARK_TEXT)

        buf = BytesIO()
        watermarked.save(buf, 'JPEG', quality=90)
        b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        results.append({'base64': b64, 'mime_type': 'image/jpeg'})

    if len(results) < num_images:
        logger.warning(
            "Only got %d/%d valid rug images after %d attempts",
            len(results), num_images, attempts,
        )

    return results
