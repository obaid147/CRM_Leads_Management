from .api_views import LeadListAPIView
from django.urls import path

urlpatterns = [
     # API Endpoints
    path('', LeadListAPIView.as_view(), name='api_lead_list'), # leads/  --> inherits from crm/urls.py
]