from rest_framework import serializers
from .models import Visitor, Session, Event

class VisitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visitor
        fields = '__all__'
        read_only_fields = ('visitor_id', 'ip_address', 'device_type', 'os', 'browser') # Removed access_status to allow admin updates

class SessionSerializer(serializers.ModelSerializer):
    visitor = VisitorSerializer(read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = Session
        fields = '__all__'

class EventSerializer(serializers.ModelSerializer):
    session = SessionSerializer(read_only=True)
    class Meta:
        model = Event
        fields = '__all__'

class EventCreateSerializer(serializers.Serializer):
    """
    Serializer to receive tracking data from frontend.
    Handles Visitor creation (if needed) and Event logging.
    """
    visitor_id = serializers.CharField(max_length=255, required=True)
    event_type = serializers.ChoiceField(choices=Event.EVENT_TYPES, default='custom')
    url = serializers.URLField(required=False, allow_blank=True)
    target_resource = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)
    
    # Device info (optional, passed from frontend or extracted from UA)
    device_type = serializers.CharField(required=False, allow_blank=True)
    os = serializers.CharField(required=False, allow_blank=True)
    browser = serializers.CharField(required=False, allow_blank=True)
    
    # Encoded info from frontend (Base64 JSON)
    encoded_info = serializers.CharField(required=False, allow_blank=True)
