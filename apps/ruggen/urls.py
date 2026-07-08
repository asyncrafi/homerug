from django.urls import path
from .views import (
    CheckoutView,
    GenerateRugView,
    GenerationDetailView,
    RugOptionsView,
    RugPreviewView,
)

urlpatterns = [
    # 1. Get dropdown options
    path('options/', RugOptionsView.as_view(), name='rug-options'),

    # 2. Generate 4 rug designs
    path('generate/', GenerateRugView.as_view(), name='rug-generate'),

    # 3. Get generation detail + images
    path('<uuid:generation_id>/', GenerationDetailView.as_view(), name='rug-detail'),

    # 4. Create Shopify checkout directly from a selected generated rug
    path('checkout/', CheckoutView.as_view(), name='rug-checkout'),
]


urlpatterns += [
    path('<uuid:generation_id>/preview/', RugPreviewView.as_view(), name='rug-preview'),
    # path('placement/<uuid:placement_id>/preview/', PlacementPreviewView.as_view(), name='placement-preview'),
]