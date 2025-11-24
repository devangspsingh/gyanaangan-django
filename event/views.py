from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from .models import Event, EventRegistration, ManualParticipant
from .serializers import (
    EventListSerializer,
    EventDetailSerializer,
    EventCreateUpdateSerializer,
    EventRegistrationSerializer,
    ManualParticipantSerializer,
    BulkManualParticipantSerializer
)
from organization.permissions import IsOrganizationAdmin, IsOrganizationMember


class EventViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing events.
    Provides CRUD operations and custom actions.
    """
    queryset = Event.objects.filter(is_published=True)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'list':
            return EventListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return EventCreateUpdateSerializer
        return EventDetailSerializer

    def get_permissions(self):
        """
        Custom permissions based on action
        """
        if self.action in ['create']:
            return [permissions.IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsOrganizationAdmin()]
        return [permissions.IsAuthenticatedOrReadOnly()]

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Allow org members to see unpublished events of their org
        if self.request.user.is_authenticated:
            user_org_ids = self.request.user.organization_memberships.filter(
                is_active=True
            ).values_list('organization_id', flat=True)
            
            queryset = Event.objects.filter(
                Q(is_published=True) | Q(organization_id__in=user_org_ids)
            )
        
        # Filter by search query
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(short_description__icontains=search)
            )
        
        # Filter by event type
        event_type = self.request.query_params.get('type', None)
        if event_type:
            queryset = queryset.filter(event_type=event_type.upper())
        
        # Filter by organization
        organization = self.request.query_params.get('organization', None)
        if organization:
            queryset = queryset.filter(organization__slug=organization)
        
        # Filter by status
        event_status = self.request.query_params.get('status', None)
        if event_status:
            queryset = queryset.filter(status=event_status.upper())
        
        # Filter by time (upcoming, ongoing, past)
        time_filter = self.request.query_params.get('time', None)
        now = timezone.now()
        if time_filter == 'upcoming':
            queryset = queryset.filter(start_datetime__gt=now)
        elif time_filter == 'ongoing':
            queryset = queryset.filter(start_datetime__lte=now, end_datetime__gte=now)
        elif time_filter == 'past':
            queryset = queryset.filter(end_datetime__lt=now)
        
        # Filter by featured
        featured = self.request.query_params.get('featured', None)
        if featured:
            queryset = queryset.filter(is_featured=featured.lower() == 'true')
        
        # Filter by registration open
        registration_open = self.request.query_params.get('registration_open', None)
        if registration_open:
            queryset = queryset.filter(is_registration_open=registration_open.lower() == 'true')
        
        return queryset.distinct()

    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to increment view count"""
        instance = self.get_object()
        # Increment view count
        Event.objects.filter(pk=instance.pk).update(view_count=instance.view_count + 1)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def register(self, request, slug=None):
        """Register for an event"""
        event = self.get_object()
        
        serializer = EventRegistrationSerializer(
            data={'event': event.id, 'additional_info': request.data.get('additional_info', {})},
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def cancel_registration(self, request, slug=None):
        """Cancel event registration"""
        event = self.get_object()
        
        try:
            registration = event.registrations.get(
                user=request.user,
                status__in=['REGISTERED', 'CONFIRMED']
            )
            registration.status = 'CANCELLED'
            registration.save()
            return Response({'message': 'Registration cancelled successfully'})
        except EventRegistration.DoesNotExist:
            return Response(
                {'error': 'You are not registered for this event'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsOrganizationMember])
    def registrations(self, request, slug=None):
        """Get all registrations for an event (organization members only)"""
        event = self.get_object()
        registrations = event.registrations.all()
        
        # Filter by status
        reg_status = request.query_params.get('status', None)
        if reg_status:
            registrations = registrations.filter(status=reg_status.upper())
        
        # Filter by attendance status
        attendance_status = request.query_params.get('attendance', None)
        if attendance_status:
            registrations = registrations.filter(attendance_status=attendance_status.upper())
        
        serializer = EventRegistrationSerializer(registrations, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOrganizationMember])
    def mark_attendance(self, request, slug=None):
        """Mark attendance for registrations"""
        event = self.get_object()
        registration_ids = request.data.get('registration_ids', [])
        attendance_status = request.data.get('attendance_status', 'PRESENT')
        
        if not registration_ids:
            return Response(
                {'error': 'registration_ids are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        registrations = event.registrations.filter(id__in=registration_ids)
        
        if attendance_status == 'PRESENT':
            for reg in registrations:
                reg.mark_present(request.user)
        else:
            registrations.update(attendance_status='ABSENT')
        
        return Response({'message': f'Marked {registrations.count()} registrations as {attendance_status}'})

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsOrganizationMember])
    def manual_participants(self, request, slug=None):
        """Get all manual participants for an event"""
        event = self.get_object()
        participants = event.manual_participants.all()
        serializer = ManualParticipantSerializer(participants, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOrganizationMember])
    def add_manual_participant(self, request, slug=None):
        """Add a manual participant to the event"""
        event = self.get_object()
        
        serializer = ManualParticipantSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save(event=event)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOrganizationMember])
    def bulk_add_participants(self, request, slug=None):
        """Bulk add manual participants"""
        event = self.get_object()
        
        serializer = BulkManualParticipantSerializer(
            data=request.data,
            context={'request': request, 'event': event}
        )
        
        if serializer.is_valid():
            participants = serializer.save()
            return Response(
                {'message': f'Added {len(participants)} participants successfully'},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsOrganizationMember])
    def dashboard(self, request, slug=None):
        """Get event dashboard statistics"""
        event = self.get_object()
        
        total_registrations = event.registrations.filter(status__in=['REGISTERED', 'CONFIRMED']).count()
        total_manual = event.manual_participants.count()
        present_registrations = event.registrations.filter(attendance_status='PRESENT').count()
        present_manual = event.manual_participants.filter(attendance_status='PRESENT').count()
        
        dashboard_data = {
            'event_details': EventDetailSerializer(event, context={'request': request}).data,
            'total_participants': total_registrations + total_manual,
            'total_registrations': total_registrations,
            'total_manual_participants': total_manual,
            'present_count': present_registrations + present_manual,
            'absent_count': total_registrations + total_manual - (present_registrations + present_manual),
            'waitlist_count': event.registrations.filter(status='WAITLIST').count(),
            'spots_remaining': event.spots_remaining,
        }
        
        return Response(dashboard_data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOrganizationAdmin])
    def publish(self, request, slug=None):
        """Publish an event"""
        event = self.get_object()
        event.is_published = True
        event.status = 'PUBLISHED'
        event.save()
        return Response({'message': 'Event published successfully'})

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny], url_path='verify-attendance')
    def verify_attendance(self, request):
        """
        Publicly accessible endpoint to verify event attendance.
        URL: /api/events/verify-attendance/?registration_id=XXX
        """
        from .serializers import AttendanceVerificationSerializer
        
        registration_id = request.query_params.get('registration_id')
        
        if not registration_id:
            return Response(
                {'error': 'registration_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            registration = EventRegistration.objects.select_related(
                'event', 'event__organization', 'user', 'user__profile'
            ).get(
                registration_number=registration_id,
                attendance_status='PRESENT'
            )
            
            # Check if user's profile is public
            if hasattr(registration.user, 'profile') and not registration.user.profile.is_profile_public:
                return Response(
                    {'error': 'This attendance record is private'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = AttendanceVerificationSerializer(registration)
            return Response(serializer.data)
            
        except EventRegistration.DoesNotExist:
            return Response(
                {'error': 'Attendance record not found or user was not marked present'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOrganizationAdmin])
    def unpublish(self, request, slug=None):
        """Unpublish an event"""
        event = self.get_object()
        event.is_published = False
        event.status = 'DRAFT'
        event.save()
        return Response({'message': 'Event unpublished successfully'})


class MyRegistrationsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user's event registrations.
    Read-only view of user's registered events.
    """
    serializer_class = EventRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return EventRegistration.objects.filter(
            user=self.request.user
        ).select_related('event', 'event__organization')

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get user's upcoming event registrations"""
        registrations = self.get_queryset().filter(
            event__start_datetime__gt=timezone.now(),
            status__in=['REGISTERED', 'CONFIRMED']
        )
        serializer = self.get_serializer(registrations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def past(self, request):
        """Get user's past event registrations"""
        registrations = self.get_queryset().filter(
            event__end_datetime__lt=timezone.now(),
            status__in=['REGISTERED', 'CONFIRMED']
        )
        serializer = self.get_serializer(registrations, many=True)
        return Response(serializer.data)
