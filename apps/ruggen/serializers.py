from rest_framework import serializers
from .models import RugGeneration, GeneratedRugImage, RoomPlacement
from .utils.pricing import validate_minimum_size, parse_size_to_sqft

STYLES = [
    'Persian', 'Moroccan', 'Bohemian', 'Modern', 'Geometric',
    'Scandinavian', 'Traditional', 'Contemporary', 'Tribal', 'Abstract',
]

# Materials now include premium options
MATERIALS = [
    'New Zealand Wool',
    'Silk',
    'Wool',
    'Cotton',
    'Jute',
    'Synthetic',
    'Bamboo',
]

class GenerateRugSerializer(serializers.Serializer):
    style = serializers.ChoiceField(choices=STYLES)

    # Free-text size — accepts "5x8 feet", "5x8 ft", "150x240 cm", etc.
    size = serializers.CharField(
        max_length=50,
        help_text='e.g. "5x8 feet" or "150x240 cm". Minimum 3x3 ft.',
    )

    material = serializers.ChoiceField(choices=MATERIALS)

    email = serializers.EmailField()

    # Free-text colors — no max limit, each color up to 100 chars
    colors = serializers.ListField(
        child=serializers.CharField(max_length=100),
        min_length=1,
        help_text='List of color names, e.g. ["navy blue", "cream", "burnt orange"]',
    )

    description = serializers.CharField(max_length=500, required=False, default='', allow_blank=True)

    def validate_size(self, value):
        try:
            validate_minimum_size(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
        return value


class PlaceRugSerializer(serializers.Serializer):
    generation_id = serializers.UUIDField()
    selected_rug_index = serializers.IntegerField(min_value=0, max_value=3)
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
        fields = [
            'id', 'created_at', 'style', 'size', 'material',
            'colors', 'description', 'status', 'rug_images',
        ]

class RoomPlacementSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomPlacement
        fields = [
            'id', 'created_at', 'generation_id', 'selected_rug_index',
            'status', 'result_base64', 'checkout_url', 'shopify_image_url',
        ]