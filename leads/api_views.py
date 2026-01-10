# DRF imports
from rest_framework import generics, permissions
from rest_framework.response import Response

# Django ORM imports
from django.db.models import OuterRef, Subquery, Q

# models and serializer
from .models import Lead, FollowUp
from .serializers import LeadSerializer

class LeadListAPIView(generics.ListAPIView):
    serializer_class = LeadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Lead.objects.filter(is_deleted=False).order_by('-id')

        # Search Functionality
        query = self.request.GET.get('q', '')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(email__icontains=query) |
                Q(phone__icontains=query)
            )
        
        """
        Same search behavior as our existing lead_list view
        """

        # Status Filter
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
    
        # Annotate with latest follow-up comment
        latest_followup = FollowUp.objects.filter(
            lead = OuterRef('pk')
        ).order_by('-created_at').values('comment')[:1]

        queryset = queryset.annotate(
            latest_comment=Subquery(latest_followup.values('comment')[:1])
        )
        
        return queryset
    