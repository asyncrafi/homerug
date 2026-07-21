from rest_framework import serializers
from .models import RugGeneration, GeneratedRugImage, RoomPlacement
from .utils.pricing import validate_minimum_size, parse_size_to_sqft

STYLES = [
    'Persian', 'Moroccan', 'Bohemian', 'Modern', 'Geometric',
    'Scandinavian', 'Traditional', 'Contemporary', 'Tribal', 'Abstract',
]

# Materials now include premium options only.
MATERIALS = [
    'Moroccan Shaggy Wool',
    'Hand Tufted New Zealand Wool',
    'Hand-Knotted New Zealand Wool',
    'Hand-Knotted Silk',
    'Printed Synthetic',
]
SHAPES = ['rectangular', 'round']


class GenerateRugSerializer(serializers.Serializer):
    style = serializers.ChoiceField(choices=STYLES)

    # Free-text size — accepts "5x8 feet", "5x8 ft", "150x240 cm", etc.
    size = serializers.CharField(
        max_length=50,
        help_text='e.g. "5x8 feet" or "150x240 cm". Minimum 2x2 ft.',
    )

    material = serializers.ChoiceField(choices=MATERIALS)
    shape = serializers.ChoiceField(choices=SHAPES, required=False, default='rectangular')

    email = serializers.EmailField()

    # Free-text colors — no max limit, each color up to 100 chars
    colors = serializers.ListField(
        child=serializers.CharField(max_length=100),
        min_length=1,
        help_text='List of color names, e.g. ["navy blue", "cream", "burnt orange"]',
    )

    description = serializers.CharField(max_length=500, required=False, default='', allow_blank=True)

    def validate_size(self, value):
        # Basic check — full validation in validate() where we have shape
        if not value or not value.strip():
            raise serializers.ValidationError('Size cannot be empty.')
        return value

    def validate(self, data):
        # Now we have all fields including shape
        try:
            validate_minimum_size(data['size'], shape=data.get('shape', 'rectangular'))
        except ValueError as e:
            raise serializers.ValidationError({'size': str(e)})
        return data


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
    placement_id = serializers.UUIDField(required=False)
    generation_id = serializers.UUIDField(required=False)
    selected_rug_index = serializers.IntegerField(min_value=0, max_value=3, required=False)
    quantity = serializers.IntegerField(min_value=1, max_value=20, required=False, default=1)

    def validate(self, data):
        if data.get('placement_id'):
            return data
        if data.get('generation_id') is not None and data.get('selected_rug_index') is not None:
            return data
        raise serializers.ValidationError(
            'Provide placement_id or generation_id and selected_rug_index.'
        )


class GeneratedRugImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedRugImage
        fields = ['index', 'base64_data', 'mime_type']


class RugGenerationSerializer(serializers.ModelSerializer):
    rug_images = GeneratedRugImageSerializer(many=True, read_only=True)

    class Meta:
        model = RugGeneration
        fields = [
            'id', 'created_at', 'style', 'size', 'material', 'shape',
            'colors', 'description', 'status', 'is_favorite', 'rug_images',
        ]

class RoomPlacementSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomPlacement
        fields = [
            'id', 'created_at', 'generation_id', 'selected_rug_index',
            'status', 'result_base64', 'checkout_url', 'shopify_image_url',
        ]