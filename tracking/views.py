from rest_framework import viewsets, status, permissions, mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from .models import Visitor, Session, Event
from .serializers import (
    VisitorSerializer, 
    SessionSerializer, 
    EventSerializer, 
    EventCreateSerializer
)

class TrackEventView(APIView):
    """
    Public endpoint to track events from the frontend.
    Does NOT require authentication (handles anonymous users via visitor_id).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = EventCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            visitor_id_str = data.get('visitor_id')
            
            # Decode extra info if present
            encoded_info = data.get('encoded_info')
            decoded_device_data = {}
            if encoded_info:
                try:
                    import base64
                    import json
                    # padding fix if needed, though robust clients usually are fine
                    decoded_bytes = base64.b64decode(encoded_info)
                    decoded_device_data = json.loads(decoded_bytes.decode('utf-8'))
                except Exception as e:
                    print(f"Analytics: Failed to decode encoded_info: {e}")

            # Extract details from decoded data or fallback to direct fields
            # Prioritize decoded data for OS/Browser as frontend parser might be better or specific
            os_val = decoded_device_data.get('os_name') or decoded_device_data.get('parsed_os') or data.get('os')
            browser_val = decoded_device_data.get('browser_name') or decoded_device_data.get('parsed_browser') or data.get('browser')
            
            device_model = decoded_device_data.get('device_model')
            device_brand = decoded_device_data.get('device_vendor')
            os_version = decoded_device_data.get('os_version')
            device_type = decoded_device_data.get('device_type') or data.get('device_type')
            
            # 1. Get or Create Visitor
            visitor, created = Visitor.objects.get_or_create(
                visitor_id=visitor_id_str,
                defaults={
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'ip_address': self.get_client_ip(request),
                    'device_type': device_type, 
                    'os': os_val,
                    'browser': browser_val,
                    'device_model': device_model,
                    'device_brand': device_brand,
                    'os_version': os_version,
                }
            )
            
            # Update last_seen if existing
            if not created:
                visitor.last_seen = timezone.now()
                # Update details if they were missing or generic
                if not visitor.os and os_val: visitor.os = os_val
                if not visitor.browser and browser_val: visitor.browser = browser_val
                if not visitor.device_model and device_model: visitor.device_model = device_model
                if not visitor.device_brand and device_brand: visitor.device_brand = device_brand
                if not visitor.os_version and os_version: visitor.os_version = os_version
                visitor.save()

            # 1.5 Link Authenticated User to Visitor (Known Device)
            if request.user.is_authenticated:
                from .models import UserVisitor
                UserVisitor.objects.update_or_create(
                    user=request.user,
                    visitor=visitor,
                    defaults={'last_used_at': timezone.now()}
                )

            # 2. Get or Create Active Session

            # 2. Get or Create Active Session
            # Simple logic: Find most recent active session for this visitor. 
            # If older than 30 mins, create new.
            session = Session.objects.filter(visitor=visitor, is_active=True).order_by('-last_activity').first()
            
            if session:
                # Check timeout (e.g., 30 mins)
                if (timezone.now() - session.last_activity).seconds > 1800:
                    session.is_active = False
                    session.save()
                    session = None
            
            if not session:
                session = Session.objects.create(
                    visitor=visitor,
                    user=request.user if request.user.is_authenticated else None,
                    referrer=data.get('metadata', {}).get('referrer', '')
                )
            else:
                # Update session activity and link user if they just logged in
                session.last_activity = timezone.now()
                if request.user.is_authenticated and not session.user:
                    session.user = request.user
                session.save()

            # 3. Log Event
            Event.objects.create(
                session=session,
                event_type=data.get('event_type'),
                url=data.get('url'),
                target_resource=data.get('target_resource'),
                metadata=data.get('metadata')
            )

            return Response({"status": "success"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
        return ip

class VisitorStatusView(APIView):
    """
    Public endpoint to check visitor status (Block/Force Login).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, visitor_id):
        if not visitor_id:
            return Response({"error": "Visitor ID required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            visitor = Visitor.objects.get(visitor_id=visitor_id)
            return Response({"status": visitor.access_status})
        except Visitor.DoesNotExist:
            # New visitor implies 'allow' by default
            return Response({"status": "allow"})

class AnalyticsBaseViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAdminUser]

class VisitorViewSet(mixins.UpdateModelMixin, AnalyticsBaseViewSet):
    queryset = Visitor.objects.all().order_by('-last_seen')
    serializer_class = VisitorSerializer
    filterset_fields = ['visitor_id', 'device_type']

class SessionViewSet(AnalyticsBaseViewSet):
    queryset = Session.objects.all().order_by('-start_time')
    serializer_class = SessionSerializer
    filterset_fields = ['is_active']

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

# ...

class EventViewSet(AnalyticsBaseViewSet):
    queryset = Event.objects.all().order_by('-timestamp')
    serializer_class = EventSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = {
        'event_type': ['exact'],
        'session__user': ['exact', 'isnull'],
        'session__visitor__visitor_id': ['exact'],
    }
    search_fields = ['url', 'target_resource', 'session__user__username', 'session__visitor__ip_address', 'session__visitor__visitor_id']
