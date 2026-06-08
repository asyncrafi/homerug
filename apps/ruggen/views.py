import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import GeneratedRugImage, RugGeneration, RoomPlacement
from .serializers import (
    CheckoutSerializer,
    GenerateRugSerializer,
    PlaceRugSerializer,
    RoomPlacementSerializer,
    RugGenerationSerializer,
)
from .utils.gemini import generate_rug_images, place_rug_in_room
from .utils.shopify import create_draft_product, get_checkout_url, upload_image_to_shopify

logger = logging.getLogger(__name__)


class RugOptionsView(APIView):
    """
    GET /api/rugs/options/
    No auth needed. Returns all dropdown options for the frontend.
    """
    def get(self, request):
        return Response({
            'styles': [
                'Persian', 'Moroccan', 'Bohemian', 'Modern', 'Geometric',
                'Scandinavian', 'Traditional', 'Contemporary', 'Tribal', 'Abstract',
            ],
            'sizes': [
                '2x3 feet', '3x5 feet', '4x6 feet', '5x8 feet',
                '6x9 feet', '8x10 feet', '9x12 feet', 'Runner (2x8 feet)',
            ],
            'materials': ['wool', 'cotton', 'jute', 'synthetic', 'silk', 'bamboo'],
            'suggested_colors': [
                'navy blue', 'cream', 'terracotta', 'forest green', 'burgundy',
                'charcoal', 'ivory', 'rust', 'sage green', 'camel', 'black', 'gold',
            ],
            'price_per_rug': settings.PRICE_PER_RUG,
            'currency': settings.CURRENCY,
            'images_per_generation': 4,
        })


class GenerateRugView(APIView):
    """
    POST /api/rugs/generate/

    Request body (JSON):
    {
        "style": "Persian",
        "size": "5x8 feet",
        "material": "wool",
        "colors": ["navy blue", "cream", "terracotta"],
        "description": "medallion pattern with floral border"   // optional
    }

    Response:
    {
        "generation_id": "uuid",
        "status": "generated",
        "images": [
            {"index": 0, "base64_data": "/9j/...", "mime_type": "image/jpeg"},
            {"index": 1, ...},
            {"index": 2, ...},
            {"index": 3, ...}
        ],
        "params": {...},
        "next_step": "POST /api/rugs/place/ with generation_id + selected_rug_index + room_image_base64"
    }
    """
    def post(self, request):
        serializer = GenerateRugSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

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
            'next_step': 'POST /api/rugs/place/ with generation_id + selected_rug_index + room_image_base64',
        }, status=status.HTTP_201_CREATED)


class GenerationDetailView(APIView):
    """
    GET /api/rugs/<generation_id>/
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
    POST /api/rugs/place/

    Request body (JSON):
    {
        "generation_id": "uuid-from-step-1",
        "selected_rug_index": 2,          // 0-3, which of the 4 rugs
        "room_image_base64": "/9j/..."    // base64 of user's room photo
                                          // OR "data:image/jpeg;base64,/9j/..." (data URI also accepted)
    }

    Response:
    {
        "placement_id": "uuid",
        "status": "placed",
        "result_base64": "/9j/...",    // room photo with rug placed in it
        "mime_type": "image/jpeg",
        "next_step": "POST /api/rugs/checkout/ with placement_id"
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

        return Response({
            'placement_id': str(placement.id),
            'status': 'placed',
            'result_base64': result_b64,
            'mime_type': 'image/jpeg',
            'next_step': 'POST /api/rugs/checkout/ with placement_id',
        }, status=status.HTTP_201_CREATED)


class CheckoutView(APIView):
    """
    POST /api/rugs/checkout/

    Request body (JSON):
    {
        "placement_id": "uuid-from-step-2"
    }

    Response:
    {
        "checkout_url": "https://malahomes.myshopify.com/cart/...",
        "shopify_image_url": "https://cdn.shopify.com/...",
        "price": 29.99,
        "currency": "USD"
    }

    NOTE: If Shopify credentials are not configured, returns mock checkout data for testing.
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

        # If no Shopify credentials, return mock for testing
        if not settings.SHOPIFY_ADMIN_API_TOKEN:
            return Response({
                'checkout_url': 'https://malahomes.myshopify.com/cart/MOCK_VARIANT:1',
                'shopify_image_url': None,
                'price': settings.PRICE_PER_RUG,
                'currency': settings.CURRENCY,
                'note': 'Shopify credentials not configured — mock response for testing',
            })

        gen = placement.generation
        shopify_url = upload_image_to_shopify(
            image_b64=placement.result_base64,
            filename=f'maia-rug-{placement.id}.jpg',
        )

        product = create_draft_product(
            image_url=shopify_url or '',
            style=gen.style,
            size=gen.size,
            material=gen.material,
            colors=gen.colors,
            price=settings.PRICE_PER_RUG,
        )

        checkout_url = ''
        if product:
            variant_id = product['variants'][0]['id']
            checkout_url = get_checkout_url(variant_id)
            placement.shopify_product_id = str(product['id'])
            placement.shopify_variant_id = str(variant_id)

        placement.shopify_image_url = shopify_url or ''
        placement.checkout_url = checkout_url
        placement.save()

        return Response({
            'checkout_url': checkout_url,
            'shopify_image_url': shopify_url,
            'price': settings.PRICE_PER_RUG,
            'currency': settings.CURRENCY,
        })
    



from django.http import HttpResponse

class RugPreviewView(APIView):
    def get(self, request, generation_id):
        try:
            generation = RugGeneration.objects.prefetch_related('rug_images').get(id=generation_id)
        except RugGeneration.DoesNotExist:
            return HttpResponse("Not found", status=404)
        
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
            </body></html>
        ''')
    

class PlacementPreviewView(APIView):
    def get(self, request, placement_id):
        try:
            placement = RoomPlacement.objects.get(id=placement_id)
        except RoomPlacement.DoesNotExist:
            return HttpResponse("Not found", status=404)
        
        return HttpResponse(f'''
            <html><body style="background:#111;color:white;font-family:sans-serif;padding:20px">
            <h2>Placement Result</h2>
            <h3>Status: {placement.status}</h3>
            <img src="data:image/jpeg;base64,{placement.result_base64}" style="max-width:900px;border-radius:12px">
            </body></html>
        ''')