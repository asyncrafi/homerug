import uuid
from django.db import models


class RugGeneration(models.Model):
    """Step 1: AI generates 4 rug designs from params."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    email = models.EmailField(blank=True, null=True)  # Optional for logged-in users, required for anonymous users

    # User params
    style = models.CharField(max_length=100)
    size = models.CharField(max_length=50)
    material = models.CharField(max_length=100)
    colors = models.JSONField(default=list)
    description = models.TextField(blank=True)

    STATUS = [
        ('pending', 'Pending'),
        ('generated', 'Generated'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f"RugGen {self.id} | {self.style} | {self.status}"


class GeneratedRugImage(models.Model):
    """One of the 4 rug images produced in Step 1."""

    generation = models.ForeignKey(
        RugGeneration, on_delete=models.CASCADE, related_name='rug_images'
    )
    index = models.IntegerField()
    base64_data = models.TextField()
    mime_type = models.CharField(max_length=30, default='image/jpeg')

    class Meta:
        ordering = ['index']


class RoomPlacement(models.Model):
    """Step 2: User uploads room photo → AI places selected rug in the room."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    generation = models.ForeignKey(
        RugGeneration, on_delete=models.CASCADE, related_name='placements'
    )
    selected_rug_index = models.IntegerField()

    # Room photo stored as base64 (or file path for prod)
    room_image_base64 = models.TextField()

    STATUS = [
        ('pending', 'Pending'),
        ('placed', 'Placed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    error_message = models.TextField(blank=True)

    # Result: room with rug placed in it
    result_base64 = models.TextField(blank=True)

    # Shopify checkout
    shopify_product_id = models.CharField(max_length=100, blank=True)
    shopify_variant_id = models.CharField(max_length=100, blank=True)
    shopify_image_url = models.URLField(blank=True)
    checkout_url = models.URLField(blank=True)

    def __str__(self):
        return f"Placement {self.id} | {self.status}"
    

class GenerationQuota(models.Model):
    email = models.EmailField(unique=True, blank=True, null=True)
    count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ruggen_generation_quota'

    def __str__(self):
        return f"{self.email} | {self.count}/3"