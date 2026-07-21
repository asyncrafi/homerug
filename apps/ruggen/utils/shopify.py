import requests
from django.conf import settings


def _headers():
    return {
        'X-Shopify-Access-Token': settings.SHOPIFY_ADMIN_API_TOKEN,
        'Content-Type': 'application/json',
    }


def _base():
    return f"https://{settings.SHOPIFY_STORE_DOMAIN}/admin/api/{settings.SHOPIFY_API_VERSION}"


def upload_image_to_shopify(image_b64: str, filename: str = 'generated-rug.jpg') -> str | None:
    resp = requests.post(
        f"{_base()}/files.json",
        json={'file': {'attachment': image_b64, 'filename': filename, 'content_type': 'image/jpeg'}},
        headers=_headers(), timeout=30,
    )
    if resp.status_code in (200, 201):
        return resp.json().get('file', {}).get('public_url')
    return None


def create_draft_product(image_b64: str, style: str, size: str, material: str, colors: list, price: float) -> dict | None:
    payload = {
        'product': {
            'title': f"Custom AI Rug — {style} | {size} | {material}",
            'body_html': f"<p>AI-generated custom rug. Style: {style}, Size: {size}, Material: {material}, Colors: {', '.join(colors)}</p>",
            'vendor': '1001 Knots',
            'product_type': 'Rug',
            'status': 'active',
            'variants': [{'price': str(price), 'requires_shipping': True}],
            'images': [{'attachment': image_b64, 'filename': 'custom-rug.jpg'}],
            'tags': f'ai-generated,{style},{material},custom-rug',
        }
    }
    resp = requests.post(f"{_base()}/products.json", json=payload, headers=_headers(), timeout=30)
    print(f"[SHOPIFY] status={resp.status_code} body={resp.text[:500]}")  # ← add this
    if resp.status_code in (200, 201):
        return resp.json().get('product')
    return None

def get_checkout_url(variant_id: int, quantity: int = 1) -> str:
    return f"https://{settings.SHOPIFY_STORE_DOMAIN}/cart/{variant_id}:{max(quantity, 1)}"
