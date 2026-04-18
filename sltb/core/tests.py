from django.test import TestCase
from django.urls import reverse

# Create your tests here.

class MaintenanceChatbotTests(TestCase):
    def test_returns_brake_recommendations_for_brake_issue(self):
        response = self.client.post(
            reverse('maintenance_chatbot'),
            {'issue': 'The brake pedal feels spongy and braking distance increased.'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['category'], 'Brake System Issue')
        self.assertTrue(any('brake fluid' in item.lower() for item in payload['recommendations']))

    def test_returns_general_recommendations_for_unknown_issue(self):
        response = self.client.post(
            reverse('maintenance_chatbot'),
            {'issue': 'There is a strange sound from under the seat.'},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['category'], 'General Diagnostic Suggestion')
        self.assertEqual(len(payload['recommendations']), 4)