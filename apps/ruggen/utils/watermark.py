from PIL import Image, ImageDraw, ImageFont


def apply_watermark(pil_img: Image.Image, text: str = 'Maia Homes') -> Image.Image:
    img = pil_img.copy().convert('RGBA')
    overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    font_size = img.width // 14
    font = _load_font(font_size)

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = img.width - tw - 20
    y = img.height - th - 20

    draw.text((x + 2, y + 2), text, font=font, fill=(0, 0, 0, 110))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 175))

    return Image.alpha_composite(img, overlay).convert('RGB')


def _load_font(size: int):
    paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        'C:/Windows/Fonts/arialbd.ttf',  # Windows fallback
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()
