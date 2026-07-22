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
    RoomPlacementSerializer,
    RugGenerationSerializer,
)
from .tasks import generate_rug_images_task
from .utils.shopify import create_draft_product, get_checkout_url, upload_image_to_shopify
from .utils.pricing import calculate_price

logger = logging.getLogger(__name__)

# Max AI generations allowed per email account.
MAX_GENERATIONS = 5
EXEMPT_EMAILS = {
    'sivmey.hok@gmail.com',
    'info@maiahomes.com',
}

BLOCKED_MESSAGE = (
    "We're sorry you're not completely happy with your designs. "
    "Please email customercare@maiahomes.com and someone will help you further."
)


def _is_exempt_email(email: str) -> bool:
    """Return True for emails that are exempt from generation limits."""
    return email.strip().lower() in EXEMPT_EMAILS


class RugOptionsView(APIView):
    """
    GET /api/ruggen/options/
    No auth needed. Returns all options + pricing info for the frontend.
    """
    def get(self, request):
        email = request.query_params.get('email')
        if email:
            quota = GenerationQuota.objects.filter(email=email).first()
            used = quota.count if quota else 0
            if _is_exempt_email(email):
                max_generations = None
                generations_remaining = None
            else:
                max_generations = MAX_GENERATIONS
                generations_remaining = max(0, MAX_GENERATIONS - used)
        else:
            used = 0
            max_generations = MAX_GENERATIONS
            generations_remaining = MAX_GENERATIONS

        return Response({
            'styles': [
                'Persian', 'Moroccan', 'Bohemian', 'Modern', 'Geometric',
                'Scandinavian', 'Traditional', 'Contemporary', 'Tribal', 'Abstract',
            ],
            'materials': [
                'Moroccan Shaggy Wool',
                'Hand Tufted New Zealand Wool',
                'Hand-Knotted New Zealand Wool',
                'Hand-Knotted Silk',
                'Printed Synthetic',
            ],
            'shapes': ['rectangular', 'round'],
            'suggested_colors': [
                'navy blue', 'cream', 'terracotta', 'forest green', 'burgundy',
                'charcoal', 'ivory', 'rust', 'sage green', 'camel', 'black', 'gold',
            ],
            # Pricing info
            'pricing': {
                'currency': settings.CURRENCY,
                'note': 'Price calculated per square foot and rounded up to .99.',
            },
            # Size guidance (free-text input — ft or cm both accepted)
            'size_guidance': {
                'minimum': '2x2 feet (61x61 cm)',
                'unit_options': ['feet', 'ft', 'cm'],
                'examples': [
                    '2x6 feet', '3x5 feet', '4x6 feet', '5x8 feet',
                    '6x9 feet', '8x10 feet', '9x12 feet',
                    '60x180 cm', '90x150 cm', '150x240 cm',
                ],
                'hint': 'You can type any custom size, e.g. "7x11 feet" or "200x300 cm"',
            },
            'images_per_generation': 4,
            'max_generations': max_generations,
            'generations_used': used,
            'generations_remaining': generations_remaining,
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
        if not _is_exempt_email(email) and quota.count >= MAX_GENERATIONS:
            return Response(
                {
                    'error': 'generation_limit_reached',
                    'message': BLOCKED_MESSAGE,
                    'contact': 'customercare@maiahomes.com',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        pricing = calculate_price(data['size'], data['material'], shape=data.get('shape', 'rectangular'))

        generation = RugGeneration.objects.create(
            email=email,
            style=data['style'],
            size=data['size'],
            material=data['material'],
            shape=data.get('shape', 'rectangular'),
            colors=data['colors'],
            description=data.get('description', ''),
            status='pending',
        )

        generate_rug_images_task.delay(
            str(generation.id),
            style=data['style'],
            colors=data['colors'],
            material=data['material'],
            size=data['size'],
            description=data.get('description', ''),
            shape=data.get('shape', 'rectangular'),
        )

        used = quota.count
        remaining = None if _is_exempt_email(email) else max(0, MAX_GENERATIONS - used)

        return Response({
            'generation_id': str(generation.id),
            'status': 'pending',
            'poll_url': f'/api/ruggen/{generation.id}/',
            'params': {
                'style': generation.style,
                'size': generation.size,
                'material': generation.material,
                'shape': generation.shape,
                'colors': generation.colors,
                'description': generation.description,
            },
            'pricing': pricing,
            'generations_used': used,
            'generations_remaining': remaining,
        }, status=status.HTTP_202_ACCEPTED)

class FavoriteRugView(APIView):
    def post(self, request, generation_id):
        try:
            generation = RugGeneration.objects.get(id=generation_id)
        except RugGeneration.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        is_favorite = request.data.get('is_favorite', True)
        generation.is_favorite = bool(is_favorite)
        generation.save(update_fields=['is_favorite'])
        return Response(RugGenerationSerializer(generation).data)


class FavoriteListView(APIView):
    def get(self, request):
        email = request.query_params.get('email', '').strip().lower()
        if not email:
            return Response({'error': 'email query param is required'}, status=status.HTTP_400_BAD_REQUEST)

        generations = RugGeneration.objects.filter(
            is_favorite=True,
            email__iexact=email,
        ).prefetch_related('rug_images').order_by('-created_at')
        return Response({
            'count': generations.count(),
            'results': RugGenerationSerializer(generations, many=True).data,
        })


class RugGenerationHistoryView(APIView):
    """
    GET /api/ruggen/history/?email=user@example.com
    Return a user's recent generations plus the latest one.
    """
    def get(self, request):
        email = request.query_params.get('email', '').strip().lower()
        if not email:
            return Response({'error': 'email query param is required'}, status=status.HTTP_400_BAD_REQUEST)

        generations = RugGeneration.objects.filter(email__iexact=email).prefetch_related('rug_images').order_by('-created_at')
        serializer = RugGenerationSerializer(generations, many=True)
        last_generation = serializer.data[0] if serializer.data else None

        return Response({
            'count': generations.count(),
            'last_generation': last_generation,
            'results': serializer.data,
        })


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


# class PlaceRugInRoomView(APIView):
#    """
#    POST /api/ruggen/place/
#
#    Request body (JSON):
#    {
#        "generation_id": "uuid-from-step-1",
#        "selected_rug_index": 2,
#        "room_image_base64": "/9j/..."   // or data URI
#    }
#    """
#    def post(self, request):
#        serializer = PlaceRugSerializer(data=request.data)
#        if not serializer.is_valid():
#            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#
#        data = serializer.validated_data
#
#        try:
#            generation = RugGeneration.objects.get(id=data['generation_id'])
#        except RugGeneration.DoesNotExist:
#            return Response({'error': 'Generation not found'}, status=status.HTTP_404_NOT_FOUND)
#
#        if generation.status != 'generated':
#            return Response(
#                {'error': f'Generation status is "{generation.status}", must be "generated"'},
#                status=status.HTTP_400_BAD_REQUEST,
#            )
#
#        try:
#            rug_img = generation.rug_images.get(index=data['selected_rug_index'])
#        except GeneratedRugImage.DoesNotExist:
#            return Response({'error': 'Invalid rug index'}, status=status.HTTP_400_BAD_REQUEST)
#
#        placement = RoomPlacement.objects.create(
#            generation=generation,
#            selected_rug_index=data['selected_rug_index'],
#            room_image_base64=data['room_image_base64'],
#            status='pending',
#        )
#
#        try:
#            result_b64 = place_rug_in_room(
#                room_image_b64=data['room_image_base64'],
#                rug_image_b64=rug_img.base64_data,
#            )
#        except Exception as exc:
#            logger.exception("Room placement failed: %s", exc)
#            placement.status = 'failed'
#            placement.error_message = str(exc)
#            placement.save()
#            return Response(
#                {'error': f'Room placement failed: {exc}'},
#                status=status.HTTP_502_BAD_GATEWAY,
#            )
#
#        placement.result_base64 = result_b64
#        placement.status = 'placed'
#        placement.save()
#
#        # Calculate price to include in placement response
#        pricing = calculate_price(generation.size, generation.material)
#
#        return Response({
#            'placement_id': str(placement.id),
#            'status': 'placed',
#            'result_base64': result_b64,
#            'mime_type': 'image/jpeg',
#            'pricing': pricing,
#            'next_step': 'POST /api/ruggen/checkout/ with placement_id',
#        }, status=status.HTTP_201_CREATED)
#

class CheckoutView(APIView):
    """
    POST /api/ruggen/checkout/

    Request body (JSON):
    {
        "generation_id": "uuid-from-generate-step",
        "selected_rug_index": 2
    }

    Optional backwards-compatibility:
    {
        "placement_id": "uuid-from-old-placement-step"
    }
    """
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        if data.get('placement_id'):
            try:
                placement = RoomPlacement.objects.select_related('generation').get(
                    id=data['placement_id']
                )
            except RoomPlacement.DoesNotExist:
                return Response({'error': 'Placement not found'}, status=status.HTTP_404_NOT_FOUND)

            if placement.status != 'placed':
                return Response(
                    {'error': f'Placement status is "{placement.status}", must be "placed"'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return self._checkout_from_placement(placement)

        if data.get('items'):
            return self._checkout_from_items(data['items'])

        try:
            generation = RugGeneration.objects.prefetch_related('rug_images').get(
                id=data['generation_id']
            )
        except RugGeneration.DoesNotExist:
            return Response({'error': 'Generation not found'}, status=status.HTTP_404_NOT_FOUND)

        if generation.status != 'generated':
            return Response(
                {'error': f'Generation status is "{generation.status}", must be "generated"'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return self._checkout_from_generation(
            generation,
            data['selected_rug_index'],
            quantity=data.get('quantity', 1),
        )
    # Backwards-compatible checkout path if a placement already exists.
    def _checkout_from_placement(self, placement):
        gen = placement.generation
        pricing = calculate_price(gen.size, gen.material, shape=gen.shape)

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
            image_b64=placement.result_base64,
            style=gen.style,
            size=gen.size,
            material=gen.material,
            colors=gen.colors,
            price=pricing['price'],
        )

        checkout_url = ''
        if product:
            variant_id = product['variants'][0]['id']
            checkout_url = get_checkout_url(variant_id, quantity=1)
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

    def _checkout_from_generation(self, generation, selected_rug_index, quantity=1):
        try:
            rug_img = generation.rug_images.get(index=selected_rug_index)
        except GeneratedRugImage.DoesNotExist:
            return Response({'error': 'Invalid rug index'}, status=status.HTTP_400_BAD_REQUEST)

        pricing = calculate_price(generation.size, generation.material, shape=generation.shape)

        if not settings.SHOPIFY_ADMIN_API_TOKEN:
            return Response({
                'checkout_url': 'https://maia-home-goods.myshopify.com/cart/MOCK_VARIANT:1',
                'shopify_image_url': None,
                'price': pricing['price'],
                'currency': pricing['currency'],
                'pricing_breakdown': pricing,
                'note': 'Shopify credentials not configured — mock response for testing',
                'generation_id': str(generation.id),
                'selected_rug_index': selected_rug_index,
                'quantity': quantity,
            })

        shopify_url = upload_image_to_shopify(
            image_b64=rug_img.base64_data,
            filename=f'maia-rug-{generation.id}-{rug_img.index}.jpg',
        )

        product = create_draft_product(
            image_b64=rug_img.base64_data,
            style=generation.style,
            size=generation.size,
            material=generation.material,
            colors=generation.colors,
            price=pricing['price'],
        )

        checkout_url = ''
        if product:
            variant_id = product['variants'][0]['id']
            checkout_url = get_checkout_url(variant_id, quantity=quantity)
            shopify_url = product.get('images', [{}])[0].get('src', '')

        return Response({
            'checkout_url': checkout_url,
            'shopify_image_url': shopify_url,
            'price': pricing['price'],
            'currency': pricing['currency'],
            'pricing_breakdown': pricing,
            'generation_id': str(generation.id),
            'selected_rug_index': selected_rug_index,
            'quantity': quantity,
        })

    def _checkout_from_items(self, items):
        results = []
        for item in items:
            generation = RugGeneration.objects.prefetch_related('rug_images').filter(id=item['generation_id']).first()
            if not generation:
                return Response({'error': 'Generation not found'}, status=status.HTTP_404_NOT_FOUND)
            if generation.status != 'generated':
                return Response(
                    {'error': f'Generation status is "{generation.status}", must be "generated"'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            results.append({
                'generation_id': str(generation.id),
                'selected_rug_index': item.get('selected_rug_index', 0),
                'quantity': item.get('quantity', 1),
                'style': generation.style,
                'size': generation.size,
                'material': generation.material,
                'shape': generation.shape,
            })

        return Response({
            'message': 'Multi-design checkout request accepted',
            'items': results,
            'count': len(results),
        })

# ── Debug preview views (dev only) ─────────────────────────────────────────

class RugPreviewView(APIView):
    def get(self, request, generation_id):
        if not settings.DEBUG:
            return HttpResponse(status=404)

        try:
            generation = RugGeneration.objects.prefetch_related('rug_images').get(id=generation_id)
        except RugGeneration.DoesNotExist:
            return HttpResponse("Not found", status=404)

        pricing = calculate_price(generation.size, generation.material, shape=generation.shape)

        images_html = ''.join([
            f'<div style="margin:10px;display:inline-block"><p>Rug {img.index}</p>'
            f'<img src="data:{img.mime_type};base64,{img.base64_data}" style="width:300px;border-radius:8px"></div>'
            for img in generation.rug_images.all()
        ])

        return HttpResponse(f'''
            <html><body style="background:#111;color:white;font-family:sans-serif;padding:20px">
            <h2>Generation: {generation_id}</h2>
            <h3>Style: {generation.style} | {generation.size} | {generation.material}</h3>
            {images_html}
            <h4>Price: ${pricing["price"]} {pricing["currency"]} 
                ({pricing["sqft"]} sqft × ${pricing["rate"]}/sqft)</h4>
            </body></html>
        ''')


class PlacementPreviewView(APIView):
    def get(self, request, placement_id):
        try:
            placement = RoomPlacement.objects.select_related('generation').get(id=placement_id)
        except RoomPlacement.DoesNotExist:
            return HttpResponse("Not found", status=404)

        pricing = calculate_price(placement.generation.size, placement.generation.material, shape=placement.generation.shape)

        return HttpResponse(f'''
            <html><body style="background:#111;color:white;font-family:sans-serif;padding:20px">
            <h2>Placement Result</h2>
            <h3>Status: {placement.status}</h3>
            <h4>Price: ${pricing["price"]} {pricing["currency"]}</h4>
            <img src="data:image/jpeg;base64,{placement.result_base64}" style="max-width:900px;border-radius:12px">
            </body></html>
        ''')