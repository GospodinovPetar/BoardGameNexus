from django.test import TestCase
from django.urls import reverse


class WebTests(TestCase):
    def test_home_page_returns_200(self):
        response = self.client.get(reverse("web:index"))

        self.assertEqual(response.status_code, 200)

    def test_mission_page_returns_200(self):
        response = self.client.get(reverse("web:mission"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Our Mission")
        self.assertContains(response, "Partner Venues")
        self.assertContains(response, "Active Events")
