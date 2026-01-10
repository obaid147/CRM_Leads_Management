from django.test import SimpleTestCase
from django.urls import reverse, resolve
from leads.views import lead_list, lead_create

class TestLeadUrls(SimpleTestCase):

    def test_list_url_resolves(self):
        url = reverse('lead_list')
        self.assertEqual(resolve(url).func, lead_list)

    def test_create_url_resolves(self):
        url = reverse('lead_create')
        self.assertEqual(resolve(url).func, lead_create)