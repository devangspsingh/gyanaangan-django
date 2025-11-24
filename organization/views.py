from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from .models import Organization, OrganizationMember, OrganizationGallery
from .serializers import (
    OrganizationListSerializer,
    OrganizationDetailSerializer,
    OrganizationCreateUpdateSerializer,
    OrganizationMemberSerializer,
    OrganizationGallerySerializer
)
from .permissions import IsOrganizationAdmin, IsOrganizationMember


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing organizations.
    Provides CRUD operations and custom actions.
    """
    queryset = Organization.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'list':
            # if self.request.user.is_authenticated:
            #     from .serializers import OrganizationListAuthenticatedSerializer
            #     return OrganizationListAuthenticatedSerializer
            return OrganizationListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return OrganizationCreateUpdateSerializer
        return OrganizationDetailSerializer

    def get_permissions(self):
        """
        Custom permissions based on action.
        Explicitly defines permissions for groups of actions to ensure security.
        """
        # 1. Admin Only Actions
        # These actions require the user to be an ADMIN of the organization
        admin_actions = [
            'update', 
            'partial_update', 
            'destroy', 
            'members',       # <--- Explicitly added here
            'add_member', 
            'update_member', 
            'remove_member'
        ]
        if self.action in admin_actions:
            return [permissions.IsAuthenticated(), IsOrganizationAdmin()]

        # 2. Member Only Actions
        # These actions require the user to be a MEMBER of the organization
        member_actions = [
            'add_gallery_image', 
            'remove_gallery_image'
        ]
        if self.action in member_actions:
            return [permissions.IsAuthenticated(), IsOrganizationMember()]

        # 3. Authenticated Only Actions (General)
        if self.action in ['create']:
            return [permissions.IsAuthenticated()]

        # 4. Public/Read-Only Actions
        # 'list', 'retrieve', 'gallery', 'events', 'stats'
        # 'stats' has internal logic checks, but 'IsAuthenticatedOrReadOnly' is a safe default for GETs
        return [permissions.IsAuthenticatedOrReadOnly()]

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by search query
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        
        # Filter by verified status
        verified = self.request.query_params.get('verified', None)
        if verified is not None:
            queryset = queryset.filter(is_verified=verified.lower() == 'true')
        
        # Filter by user's organizations
        my_orgs = self.request.query_params.get('my_organizations', None)
        if my_orgs and self.request.user.is_authenticated:
            queryset = queryset.filter(
                members__user=self.request.user,
                members__is_active=True
            ).distinct()
        
        return queryset

    # --- Actions ---

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def check_user_permissions(self, request, slug=None):
        """
        Check current user's permissions for this organization.
        Returns role, permissions, and admin status.
        This endpoint is separate to avoid leaking permission data in public APIs.
        """
        if not request.user.is_authenticated:
            return Response({
                'is_member': False,
                'is_admin': False,
                'role': None,
                'permissions': {},
            })
        organization = self.get_object()
        
        try:
            member = organization.members.get(user=request.user, is_active=True)
            return Response({
                'is_member': True,
                'is_admin': member.role == 'ADMIN',
                'role': member.role,
                'permissions': member.permissions,
            })
        except OrganizationMember.DoesNotExist:
            return Response({
                'is_member': False,
                'is_admin': False,
                'role': None,
                'permissions': {},
            })

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsOrganizationAdmin])
    def members(self, request, slug=None):
        """Get all members of an organization (admin only)"""
        organization = self.get_object()
        members = organization.members.filter(is_active=True)
        
        role = request.query_params.get('role', None)
        if role:
            members = members.filter(role=role.upper())
        
        serializer = OrganizationMemberSerializer(members, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_member(self, request, slug=None):
        """Add a new member to the organization"""
        organization = self.get_object()
        
        serializer = OrganizationMemberSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(organization=organization)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'])
    def update_member(self, request, slug=None):
        """Update a member's role or permissions"""
        organization = self.get_object()
        member_id = request.data.get('member_id')
        
        if not member_id:
            return Response({'error': 'member_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        member = get_object_or_404(OrganizationMember, id=member_id, organization=organization)
        
        serializer = OrganizationMemberSerializer(
            member,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def remove_member(self, request, slug=None):
        """Remove a member from the organization"""
        organization = self.get_object()
        member_id = request.data.get('member_id')
        
        if not member_id:
            return Response({'error': 'member_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        member = get_object_or_404(OrganizationMember, id=member_id, organization=organization)
        
        if member.role == 'ADMIN':
            active_admins = OrganizationMember.objects.filter(
                organization=organization,
                role='ADMIN',
                is_active=True
            ).count()
            
            if active_admins <= 1:
                return Response(
                    {'error': 'Cannot remove the last admin of the organization'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        member.is_active = False
        member.save()
        
        return Response({'message': 'Member removed successfully'})

    @action(detail=True, methods=['get'])
    def gallery(self, request, slug=None):
        """Get organization gallery images"""
        organization = self.get_object()
        gallery = organization.gallery_images.all()
        serializer = OrganizationGallerySerializer(gallery, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_gallery_image(self, request, slug=None):
        """Add an image to organization gallery"""
        organization = self.get_object()
        
        serializer = OrganizationGallerySerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(organization=organization)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def remove_gallery_image(self, request, slug=None):
        """Remove an image from organization gallery"""
        organization = self.get_object()
        image_id = request.query_params.get('image_id')
        
        if not image_id:
            return Response({'error': 'image_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        image = get_object_or_404(OrganizationGallery, id=image_id, organization=organization)
        image.delete()
        
        return Response({'message': 'Gallery image removed successfully'})

    @action(detail=True, methods=['get'])
    def events(self, request, slug=None):
        """Get all events by this organization"""
        organization = self.get_object()
        from event.serializers import EventListSerializer
        
        events = organization.events.filter(is_published=True)
        
        event_status = request.query_params.get('status', None)
        if event_status:
            events = events.filter(status=event_status.upper())
        
        serializer = EventListSerializer(events, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def stats(self, request, slug=None):
        """Get organization statistics"""
        organization = self.get_object()
        
        # Explicit check here is good, but relying on permission class is better.
        # Currently, get_permissions returns ReadOnly for this, so this manual check is vital.
        if not request.user.is_authenticated or not organization.has_member(request.user):
            return Response(
                {'error': 'Only organization members can view stats'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        stats = {
            'total_members': organization.member_count,
            'total_admins': organization.admin_count,
            'total_events': organization.events.count(),
            'published_events': organization.events.filter(is_published=True).count(),
            'upcoming_events': organization.events.filter(
                is_published=True,
                start_datetime__gt=timezone.now()
            ).count(),
            'total_participants': sum(
                event.registered_count for event in organization.events.all()
            ),
        }
        
        return Response(stats)