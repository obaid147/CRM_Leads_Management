from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from leads.models import Lead

class LeadListViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.client.login(username="staff", password="pass")

        Lead.objects.create(name="Test Lead", email="lead@example.com")

    def test_lead_list_status_code(self):
        """Page loads successfully"""
        response = self.client.get(reverse('lead_list'))
        self.assertEqual(response.status_code, 200)

    def test_lead_list_template(self):
        """Correct template is used"""
        response = self.client.get(reverse('lead_list'))
        self.assertTemplateUsed(response, "leads/lead_list.html")

    def test_lead_list_contains_lead(self):
        """Lead appears in table"""
        response = self.client.get(reverse('lead_list'))
        self.assertContains(response, "Test Lead")

class LeadCreateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="pass", is_superuser=True)

    def test_create_lead_redirects(self):
        """Superuser should create lead successfully"""
        self.client.login(username="admin", password="pass")

        response = self.client.post(reverse('lead_create'), {
            'name': 'New Lead',
            'email': 'new@example.com',
            'phone': '123'
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Lead.objects.count(), 1)