from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.ruggen.models import GeneratedRugImage, RugGeneration
from apps.ruggen.utils.gemini import get_aspect_ratio_for_size


class RugGenerationUtilityTests(TestCase):
    def test_get_aspect_ratio_for_size_uses_ratio(self):
        self.assertEqual(get_aspect_ratio_for_size('2.5x6 ft'), '5:12')
        self.assertEqual(get_aspect_ratio_for_size('5x8 ft'), '5:8')


class RugGenerationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_checkout_accepts_quantity(self):
        generation = RugGeneration.objects.create(
            style='Modern',
            size='5x8 feet',
            material='Hand-Knotted New Zealand Wool',
            colors=['navy blue'],
            status='generated',
        )
        GeneratedRugImage.objects.create(generation=generation, index=0, base64_data='abc', mime_type='image/jpeg')

        response = self.client.post(reverse('rug-checkout'), {
            'generation_id': str(generation.id),
            'selected_rug_index': 0,
            'quantity': 3,
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['quantity'], 3)

    def test_toggle_favorite_and_list(self):
        generation = RugGeneration.objects.create(
            style='Moroccan',
            size='4x6 feet',
            material='Hand Tufted New Zealand Wool',
            colors=['cream'],
            status='generated',
        )

        response = self.client.post(reverse('rug-favorite', args=[generation.id]), {'is_favorite': True}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(RugGeneration.objects.get(id=generation.id).is_favorite)

        list_response = self.client.get(reverse('rug-favorites'), {'email': 'user@example.com'})
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()['results'][0]['id'], str(generation.id))

    def test_history_endpoint_returns_latest_generation(self):
        RugGeneration.objects.create(
            email='user@example.com',
            style='Persian',
            size='4x6 feet',
            material='Hand Tufted New Zealand Wool',
            colors=['navy blue'],
            status='generated',
        )
        latest = RugGeneration.objects.create(
            email='user@example.com',
            style='Modern',
            size='5x8 feet',
            material='Hand-Knotted New Zealand Wool',
            colors=['cream'],
            status='generated',
        )

        response = self.client.get(reverse('rug-history'), {'email': 'user@example.com'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 2)
        self.assertEqual(response.json()['last_generation']['id'], str(latest.id))

    def test_history_and_favorites_require_email(self):
        response = self.client.get(reverse('rug-favorites'))
        self.assertEqual(response.status_code, 400)

        response = self.client.get(reverse('rug-history'))
        self.assertEqual(response.status_code, 400)
