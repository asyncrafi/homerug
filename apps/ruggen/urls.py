from django.urls import path
from .views import (
    CheckoutView,
    FavoriteListView,
    FavoriteRugView,
    GenerateRugView,
    GenerationDetailView,
    RugGenerationHistoryView,
    RugOptionsView,
    RugPreviewView,
)

urlpatterns = [
    # 1. Get dropdown options
    path('options/', RugOptionsView.as_view(), name='rug-options'),

    # 2. Generate 4 rug designs
    path('generate/', GenerateRugView.as_view(), name='rug-generate'),

    # 3. Favorite / saved designs
    path('favorites/', FavoriteListView.as_view(), name='rug-favorites'),
    path('<uuid:generation_id>/favorite/', FavoriteRugView.as_view(), name='rug-favorite'),

    # 4. User generation history / last generation
    path('history/', RugGenerationHistoryView.as_view(), name='rug-history'),

    # 5. Get generation detail + images
    path('<uuid:generation_id>/', GenerationDetailView.as_view(), name='rug-detail'),

    # 5. Create Shopify checkout directly from a selected generated rug
    path('checkout/', CheckoutView.as_view(), name='rug-checkout'),
]


urlpatterns += [
    path('<uuid:generation_id>/preview/', RugPreviewView.as_view(), name='rug-preview'),
    # path('placement/<uuid:placement_id>/preview/', PlacementPreviewView.as_view(), name='placement-preview'),
]