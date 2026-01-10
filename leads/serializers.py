from rest_framework import serializers
from leads.models import Lead

class LeadSerializer(serializers.ModelSerializer):
    latest_comment = serializers.CharField(read_only=True)

    class Meta:
        model = Lead
        fields = ['id', 'name', 'email', 'phone', 'latest_comment']