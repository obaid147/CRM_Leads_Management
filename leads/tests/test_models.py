from django.test import TestCase
from leads.models import Lead
from django.contrib.auth.models import User

class LeadModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='staff', 
            password='pass', 
            is_staff=True)
        self.lead = Lead.objects.create(
            name="John Doe",
            email="john@example.com",
            phone="1234567890",
            status="new",
            assigned_to=self.user
        )

    def test_lead_str(self):
        """Test string representation of Lead"""
        self.assertEqual(str(self.lead), "John Doe")
    
    def test_status_default(self):
        """Status should be NEW by default"""
        lead = Lead.objects.create(
            name="A",
            email="a@example.com"
        )
        self.assertEqual(lead.status, "new")
    
    def test_assigned_to(self):
        """Lead should be assigned to the correct user"""
        self.assertEqual(self.lead.assigned_to.username, "staff")