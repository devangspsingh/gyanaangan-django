from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Event, EventRegistration, ManualParticipant
from organization.serializers import OrganizationListSerializer
from accounts.serializers import MinimalUserSerializer, PublicUserSerializer

User = get_user_model()


class EventListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for event lists"""
    organization_details = OrganizationListSerializer(source='organization', read_only=True)
    registered_count = serializers.IntegerField(read_only=True)
    is_past = serializers.BooleanField(read_only=True)
    is_ongoing = serializers.BooleanField(read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    spots_remaining = serializers.IntegerField(read_only=True)
    user_is_registered = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'slug', 'title', 'short_description', 'event_type', 'event_image',
            'start_datetime', 'end_datetime', 'is_online', 'venue_name',
            'max_participants', 'registration_fee', 'is_registration_open',
            'status', 'is_published', 'is_featured', 'organization',
            'organization_details', 'registered_count',
            'is_past', 'is_ongoing', 'is_upcoming', 'spots_remaining',
            'user_is_registered', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

    def get_user_is_registered(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.registrations.filter(
                user=request.user,
                status__in=['REGISTERED', 'CONFIRMED']
            ).exists()
        return False


class EventDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual event"""
    organization_details = OrganizationListSerializer(source='organization', read_only=True)
    registered_count = serializers.IntegerField(read_only=True)
    present_count = serializers.IntegerField(read_only=True)
    is_past = serializers.BooleanField(read_only=True)
    is_ongoing = serializers.BooleanField(read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    registration_closed = serializers.BooleanField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    spots_remaining = serializers.IntegerField(read_only=True)
    user_is_registered = serializers.SerializerMethodField()
    user_registration = serializers.SerializerMethodField()
    can_user_register = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'slug', 'organization', 'organization_details', 'title',
            'description', 'short_description', 'event_type', 'event_image',
            'start_datetime', 'end_datetime', 'registration_deadline',
            'is_online', 'venue_name', 'venue_address', 'google_maps_link',
            'meeting_link', 'max_participants', 'registration_fee',
            'is_registration_open', 'prizes', 'rules', 'eligibility_criteria',
            'schedule', 'tags', 'contact_person', 'contact_email', 'contact_phone',
            'status', 'is_published', 'is_featured', 'created_by',
            'view_count', 'registered_count', 'present_count',
            'is_past', 'is_ongoing', 'is_upcoming', 'registration_closed',
            'is_full', 'spots_remaining', 'user_is_registered', 'user_registration',
            'can_user_register', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'view_count', 'created_at', 'updated_at', 'created_by']

    def get_user_is_registered(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.registrations.filter(
                user=request.user,
                status__in=['REGISTERED', 'CONFIRMED']
            ).exists()
        return False

    def get_user_registration(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                registration = obj.registrations.get(
                    user=request.user,
                    status__in=['REGISTERED', 'CONFIRMED']
                )
                return EventRegistrationSerializer(registration).data
            except EventRegistration.DoesNotExist:
                return None
        return None

    def get_can_user_register(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_register(request.user)
        return False


class EventCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating events"""
    
    class Meta:
        model = Event
        fields = [
            'id', 'organization', 'title', 'description', 'short_description',
            'event_type', 'event_image', 'start_datetime', 'end_datetime',
            'registration_deadline', 'is_online', 'venue_name', 'venue_address',
            'google_maps_link', 'meeting_link', 'max_participants',
            'registration_fee', 'is_registration_open', 'prizes', 'rules',
            'eligibility_criteria', 'schedule', 'tags', 'contact_person',
            'contact_email', 'contact_phone', 'status', 'is_published',
            'is_featured', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Set created_by from request user
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

    def validate(self, data):
        # Validate datetime fields
        start_datetime = data.get('start_datetime')
        end_datetime = data.get('end_datetime')
        registration_deadline = data.get('registration_deadline')
        
        if start_datetime and end_datetime:
            if end_datetime <= start_datetime:
                raise serializers.ValidationError(
                    "End datetime must be after start datetime."
                )
        
        if registration_deadline and start_datetime:
            if registration_deadline > start_datetime:
                raise serializers.ValidationError(
                    "Registration deadline must be before event start."
                )
        
        # Validate online event has meeting link
        is_online = data.get('is_online', False)
        meeting_link = data.get('meeting_link')
        
        if is_online and not meeting_link:
            raise serializers.ValidationError(
                "Meeting link is required for online events."
            )
        
        # Validate offline event has venue details
        if not is_online:
            venue_name = data.get('venue_name')
            if not venue_name:
                raise serializers.ValidationError(
                    "Venue name is required for offline events."
                )
        
        return data


class EventRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for event registrations"""
    user_details = PublicUserSerializer(source='user', read_only=True)
    event_details = EventListSerializer(source='event', read_only=True)
    marked_by_details = MinimalUserSerializer(source='marked_present_by', read_only=True)
    
    class Meta:
        model = EventRegistration
        fields = [
            'id', 'event', 'event_details', 'user', 'user_details',
            'registration_number', 'status', 'attendance_status',
            'additional_info', 'marked_present_by', 'marked_by_details',
            'marked_present_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'registration_number', 'marked_present_by',
            'marked_present_at', 'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        # Set user from request
        validated_data['user'] = self.context['request'].user
        
        # Check if event is full
        event = validated_data['event']
        if event.is_full:
            validated_data['status'] = 'WAITLIST'
        else:
            validated_data['status'] = 'REGISTERED'
        
        return super().create(validated_data)

    def validate_event(self, value):
        user = self.context['request'].user
        
        # Check if already registered
        if value.registrations.filter(
            user=user,
            status__in=['REGISTERED', 'CONFIRMED']
        ).exists():
            raise serializers.ValidationError(
                "You are already registered for this event."
            )
        
        # Check if registration is open
        if not value.is_registration_open or value.registration_closed:
            raise serializers.ValidationError(
                "Registration is closed for this event."
            )
        
        # Check if event is published
        if not value.is_published:
            raise serializers.ValidationError(
                "This event is not available for registration."
            )
        
        return value


class ManualParticipantSerializer(serializers.ModelSerializer):
    """Serializer for manually added participants"""
    added_by_details = MinimalUserSerializer(source='added_by', read_only=True)
    event_details = EventListSerializer(source='event', read_only=True)
    
    class Meta:
        model = ManualParticipant
        fields = [
            'id', 'event', 'event_details', 'name', 'email', 'phone',
            'organization_name', 'designation', 'attendance_status',
            'added_by', 'added_by_details', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'added_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Set added_by from request user
        validated_data['added_by'] = self.context['request'].user
        return super().create(validated_data)


class BulkManualParticipantSerializer(serializers.Serializer):
    """Serializer for bulk adding manual participants"""
    participants = ManualParticipantSerializer(many=True)
    
    def create(self, validated_data):
        participants_data = validated_data.get('participants', [])
        event = self.context.get('event')
        request_user = self.context.get('request').user
        
        participants = []
        for participant_data in participants_data:
            participant_data['event'] = event
            participant_data['added_by'] = request_user
            participants.append(ManualParticipant(**participant_data))
        
        # Bulk create
        created_participants = ManualParticipant.objects.bulk_create(participants)
        return created_participants


class AttendanceVerificationSerializer(serializers.ModelSerializer):
    """
    Public serializer for attendance verification.
    Shows user attended an event with minimal user info.
    """
    user_details = PublicUserSerializer(source='user', read_only=True)
    event_details = EventDetailSerializer(source='event', read_only=True)
    
    class Meta:
        model = EventRegistration
        fields = [
            'id', 'registration_number', 'user_details', 'event_details',
            'attendance_status', 'marked_present_at', 'created_at'
        ]
        read_only_fields = ['id', 'registration_number', 'attendance_status', 
                           'marked_present_at', 'created_at']
