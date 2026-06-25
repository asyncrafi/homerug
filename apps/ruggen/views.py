import logging

from django.conf import settings
from django.http import HttpResponse
from django.db.models import F
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import GeneratedRugImage, GenerationQuota, RugGeneration, RoomPlacement
from .serializers import (
    CheckoutSerializer,
    GenerateRugSerializer,
    PlaceRugSerializer,
    RoomPlacementSerializer,
    RugGenerationSerializer,
)
from .utils.gemini import generate_rug_images, place_rug_in_room
from .utils.shopify import create_draft_product, get_checkout_url, upload_image_to_shopify
from .utils.pricing import calculate_price

logger = logging.getLogger(__name__)

# Max AI generations allowed per session/IP
MAX_GENERATIONS = 3
GENERATION_LIMIT_KEY = 'rug_generation_count'

BLOCKED_MESSAGE = (
    "We're sorry you're not completely happy with your designs. "
    "Please email customercare@maiahomes.com and someone will help you further."
)


def _get_generation_count(request) -> int:
    """Return how many generations this session has used."""
    return request.session.get(GENERATION_LIMIT_KEY, 0)


def _increment_generation_count(request) -> int:
    """Increment and persist the session generation counter. Returns new count."""
    count = request.session.get(GENERATION_LIMIT_KEY, 0) + 1
    request.session[GENERATION_LIMIT_KEY] = count
    request.session.modified = True
    return count


class RugOptionsView(APIView):
    """
    GET /api/ruggen/options/
    No auth needed. Returns all options + pricing info for the frontend.
    """
    def get(self, request):
        return Response({
            'styles': [
                'Persian', 'Moroccan', 'Bohemian', 'Modern', 'Geometric',
                'Scandinavian', 'Traditional', 'Contemporary', 'Tribal', 'Abstract',
            ],
            'materials': [
                'New Zealand Wool',
                'Silk',
                'Wool',
                'Cotton',
                'Jute',
                'Synthetic',
                'Bamboo',
            ],
            'suggested_colors': [
                'navy blue', 'cream', 'terracotta', 'forest green', 'burgundy',
                'charcoal', 'ivory', 'rust', 'sage green', 'camel', 'black', 'gold',
            ],
            # Pricing info
            'pricing': {
                'base_rate_per_sqft': 39,
                'premium_rate_per_sqft': 49,
                'premium_materials': ['New Zealand Wool', 'Silk'],
                'currency': settings.CURRENCY,
                'note': 'Price calculated per square foot. Always ends in $9.',
            },
            # Size guidance (free-text input — ft or cm both accepted)
            'size_guidance': {
                'minimum': '3x3 feet (91x91 cm)',
                'unit_options': ['feet', 'ft', 'cm'],
                'examples': [
                    '3x5 feet', '4x6 feet', '5x8 feet',
                    '6x9 feet', '8x10 feet', '9x12 feet',
                    '90x150 cm', '120x180 cm', '150x240 cm',
                ],
                'hint': 'You can type any custom size, e.g. "7x11 feet" or "200x300 cm"',
            },
            'images_per_generation': 4,
            'max_generations': MAX_GENERATIONS,
            'generations_used': _get_generation_count(request),
            'generations_remaining': max(0, MAX_GENERATIONS - _get_generation_count(request)),
        })


class GenerateRugView(APIView):
    """
    POST /api/ruggen/generate/

    Request body (JSON):
    {
        "email": "user@example.com",
        "style": "Persian",
        "size": "5x8 feet",
        "material": "New Zealand Wool",
        "colors": ["navy blue", "cream", "burnt orange"],
        "description": "medallion pattern with floral border"   // optional
    }
    """
    def post(self, request):
        serializer = GenerateRugSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        email = data['email']

        quota, _ = GenerationQuota.objects.get_or_create(email=email)
        if quota.count >= MAX_GENERATIONS:
            return Response(
                {
                    'error': 'generation_limit_reached',
                    'message': BLOCKED_MESSAGE,
                    'contact': 'customercare@maiahomes.com',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        pricing = calculate_price(data['size'], data['material'])

        generation = RugGeneration.objects.create(
            style=data['style'],
            size=data['size'],
            material=data['material'],
            colors=data['colors'],
            description=data.get('description', ''),
            status='pending',
        )

        try:
            images = generate_rug_images(
                style=data['style'],
                colors=data['colors'],
                material=data['material'],
                size=data['size'],
                description=data.get('description', ''),
                num_images=4,
            )
        except Exception as exc:
            logger.exception("Rug generation failed: %s", exc)
            generation.status = 'failed'
            generation.error_message = str(exc)
            generation.save()
            return Response(
                {'error': f'Image generation failed: {exc}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        for i, img in enumerate(images):
            GeneratedRugImage.objects.create(
                generation=generation,
                index=i,
                base64_data=img['base64'],
                mime_type=img['mime_type'],
            )

        generation.status = 'generated'
        generation.save()

        quota.count = F('count') + 1
        quota.save(update_fields=['count'])
        quota.refresh_from_db()

        return Response({
            'generation_id': str(generation.id),
            'status': 'generated',
            'images': [
                {'index': img.index, 'base64_data': img.base64_data, 'mime_type': img.mime_type}
                for img in generation.rug_images.all()
            ],
            'params': {
                'style': generation.style,
                'size': generation.size,
                'material': generation.material,
                'colors': generation.colors,
                'description': generation.description,
            },
            'pricing': pricing,
            'generations_used': quota.count,
            'generations_remaining': max(0, MAX_GENERATIONS - quota.count),
            'next_step': 'POST /api/ruggen/place/ with generation_id + selected_rug_index + room_image_base64',
        }, status=status.HTTP_201_CREATED)

class GenerationDetailView(APIView):
    """
    GET /api/ruggen/<generation_id>/
    Retrieve generation status and all 4 rug images.
    """
    def get(self, request, generation_id):
        try:
            generation = RugGeneration.objects.prefetch_related('rug_images').get(id=generation_id)
        except RugGeneration.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(RugGenerationSerializer(generation).data)


class PlaceRugInRoomView(APIView):
    """
    POST /api/ruggen/place/

    Request body (JSON):
    {
        "generation_id": "uuid-from-step-1",
        "selected_rug_index": 2,
        "room_image_base64": "/9j/..."   // or data URI
    }
    """
    def post(self, request):
        serializer = PlaceRugSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        try:
            generation = RugGeneration.objects.get(id=data['generation_id'])
        except RugGeneration.DoesNotExist:
            return Response({'error': 'Generation not found'}, status=status.HTTP_404_NOT_FOUND)

        if generation.status != 'generated':
            return Response(
                {'error': f'Generation status is "{generation.status}", must be "generated"'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            rug_img = generation.rug_images.get(index=data['selected_rug_index'])
        except GeneratedRugImage.DoesNotExist:
            return Response({'error': 'Invalid rug index'}, status=status.HTTP_400_BAD_REQUEST)

        placement = RoomPlacement.objects.create(
            generation=generation,
            selected_rug_index=data['selected_rug_index'],
            room_image_base64=data['room_image_base64'],
            status='pending',
        )

        try:
            result_b64 = place_rug_in_room(
                room_image_b64=data['room_image_base64'],
                rug_image_b64=rug_img.base64_data,
            )
        except Exception as exc:
            logger.exception("Room placement failed: %s", exc)
            placement.status = 'failed'
            placement.error_message = str(exc)
            placement.save()
            return Response(
                {'error': f'Room placement failed: {exc}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        placement.result_base64 = result_b64
        placement.status = 'placed'
        placement.save()

        # Calculate price to include in placement response
        pricing = calculate_price(generation.size, generation.material)

        return Response({
            'placement_id': str(placement.id),
            'status': 'placed',
            'result_base64': result_b64,
            'mime_type': 'image/jpeg',
            'pricing': pricing,
            'next_step': 'POST /api/ruggen/checkout/ with placement_id',
        }, status=status.HTTP_201_CREATED)


class CheckoutView(APIView):
    """
    POST /api/ruggen/checkout/

    Request body (JSON):
    {
        "placement_id": "uuid-from-step-2"
    }
    """
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            placement = RoomPlacement.objects.select_related('generation').get(
                id=serializer.validated_data['placement_id']
            )
        except RoomPlacement.DoesNotExist:
            return Response({'error': 'Placement not found'}, status=status.HTTP_404_NOT_FOUND)

        if placement.status != 'placed':
            return Response(
                {'error': f'Placement status is "{placement.status}", must be "placed"'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        gen = placement.generation
        pricing = calculate_price(gen.size, gen.material)

        # If no Shopify credentials, return mock for testing
        if not settings.SHOPIFY_ADMIN_API_TOKEN:
            return Response({
                'checkout_url': 'https://maia-home-goods.myshopify.com/cart/MOCK_VARIANT:1',
                'shopify_image_url': None,
                'price': pricing['price'],
                'currency': pricing['currency'],
                'pricing_breakdown': pricing,
                'note': 'Shopify credentials not configured — mock response for testing',
            })

        shopify_url = upload_image_to_shopify(
            image_b64=placement.result_base64,
            filename=f'maia-rug-{placement.id}.jpg',
        )

        product = create_draft_product(
            image_b64=placement.result_base64,  # pass base64 directly
            style=gen.style,
            size=gen.size,
            material=gen.material,
            colors=gen.colors,
            price=pricing['price'],
        )

        checkout_url = ''
        if product:
            variant_id = product['variants'][0]['id']
            checkout_url = get_checkout_url(variant_id)
            # grab the image url from the created product
            shopify_url = product.get('images', [{}])[0].get('src', '')
            placement.shopify_product_id = str(product['id'])
            placement.shopify_variant_id = str(variant_id)

        placement.shopify_image_url = shopify_url or ''
        placement.checkout_url = checkout_url
        placement.save()

        return Response({
            'checkout_url': checkout_url,
            'shopify_image_url': shopify_url,
            'price': pricing['price'],
            'currency': pricing['currency'],
            'pricing_breakdown': pricing,
        })


# ── Debug preview views (dev only) ─────────────────────────────────────────

class RugPreviewView(APIView):
    def get(self, request, generation_id):
        try:
            generation = RugGeneration.objects.prefetch_related('rug_images').get(id=generation_id)
        except RugGeneration.DoesNotExist:
            return HttpResponse("Not found", status=404)

        pricing = calculate_price(generation.size, generation.material)

        images_html = ''.join([
            f'<div style="margin:10px;display:inline-block"><p>Rug {img.index}</p>'
            f'<img src="data:{img.mime_type};base64,{img.base64_data}" style="width:300px;border-radius:8px"></div>'
            for img in generation.rug_images.all()
        ])

        return HttpResponse(f'''
            <html><body style="background:#111;color:white;font-family:sans-serif;padding:20px">
            <h2>Generation: {generation_id}</h2>
            <h3>Style: {generation.style} | {generation.size} | {generation.material}</h3>
            <h4>Price: ${pricing["price"]} {pricing["currency"]} 
                ({pricing["sqft"]} sqft × ${pricing["rate"]}/sqft)</h4>
            {images_html}
            </body></html>
        ''')


class PlacementPreviewView(APIView):
    def get(self, request, placement_id):
        try:
            placement = RoomPlacement.objects.select_related('generation').get(id=placement_id)
        except RoomPlacement.DoesNotExist:
            return HttpResponse("Not found", status=404)

        pricing = calculate_price(placement.generation.size, placement.generation.material)

        return HttpResponse(f'''
            <html><body style="background:#111;color:white;font-family:sans-serif;padding:20px">
            <h2>Placement Result</h2>
            <h3>Status: {placement.status}</h3>
            <h4>Price: ${pricing["price"]} {pricing["currency"]}</h4>
            <img src="data:image/jpeg;base64,{placement.result_base64}" style="max-width:900px;border-radius:12px">
            </body></html>
        ''')