from rest_framework import serializers
from .models import RugGeneration, GeneratedRugImage, RoomPlacement

STYLES = ['Persian', 'Moroccan', 'Bohemian', 'Modern', 'Geometric',
          'Scandinavian', 'Traditional', 'Contemporary', 'Tribal', 'Abstract']
MATERIALS = ['wool', 'cotton', 'jute', 'synthetic', 'silk', 'bamboo']
SIZES = ['2x3 feet', '3x5 feet', '4x6 feet', '5x8 feet', '6x9 feet', '8x10 feet', '9x12 feet', 'Runner (2x8 feet)']


class GenerateRugSerializer(serializers.Serializer):
    style = serializers.ChoiceField(choices=STYLES)
    size = serializers.ChoiceField(choices=SIZES)
    material = serializers.ChoiceField(choices=MATERIALS)
    colors = serializers.ListField(child=serializers.CharField(max_length=50), min_length=1, max_length=5)
    description = serializers.CharField(max_length=500, required=False, default='')


class PlaceRugSerializer(serializers.Serializer):
    generation_id = serializers.UUIDField()
    selected_rug_index = serializers.IntegerField(min_value=0, max_value=3)
    # Room image as base64 string (frontend sends after encoding)
    room_image_base64 = serializers.CharField()

    def validate_room_image_base64(self, value):
        # Strip data URI prefix if present e.g. "data:image/jpeg;base64,..."
        if ',' in value:
            value = value.split(',', 1)[1]
        return value


class CheckoutSerializer(serializers.Serializer):
    placement_id = serializers.UUIDField()


class GeneratedRugImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedRugImage
        fields = ['index', 'base64_data', 'mime_type']


class RugGenerationSerializer(serializers.ModelSerializer):
    rug_images = GeneratedRugImageSerializer(many=True, read_only=True)

    class Meta:
        model = RugGeneration
        fields = ['id', 'created_at', 'style', 'size', 'material', 'colors', 'description', 'status', 'rug_images']


class RoomPlacementSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomPlacement
        fields = ['id', 'created_at', 'generation_id', 'selected_rug_index', 'status', 'result_base64', 'checkout_url', 'shopify_image_url']
