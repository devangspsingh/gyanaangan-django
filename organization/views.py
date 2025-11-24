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
            return OrganizationListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return OrganizationCreateUpdateSerializer
        return OrganizationDetailSerializer

    def get_permissions(self):
        """
        Custom permissions based on action
        """
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsOrganizationAdmin()]
        elif self.action in ['create']:
            return [permissions.IsAuthenticated()]
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

    @action(detail=True, methods=['get'])
    def members(self, request, slug=None):
        """Get all members of an organization"""
        organization = self.get_object()
        members = organization.members.filter(is_active=True)
        
        # Filter by role if specified
        role = request.query_params.get('role', None)
        if role:
            members = members.filter(role=role.upper())
        
        serializer = OrganizationMemberSerializer(members, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOrganizationAdmin])
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

    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAuthenticated, IsOrganizationAdmin])
    def update_member(self, request, slug=None):
        """Update a member's role or permissions"""
        organization = self.get_object()
        member_id = request.data.get('member_id')
        
        if not member_id:
            return Response(
                {'error': 'member_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        member = get_object_or_404(
            OrganizationMember,
            id=member_id,
            organization=organization
        )
        
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

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOrganizationAdmin])
    def remove_member(self, request, slug=None):
        """Remove a member from the organization"""
        organization = self.get_object()
        member_id = request.data.get('member_id')
        
        if not member_id:
            return Response(
                {'error': 'member_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        member = get_object_or_404(
            OrganizationMember,
            id=member_id,
            organization=organization
        )
        
        # Check if trying to remove the last admin
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

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOrganizationMember])
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

    @action(detail=True, methods=['delete'], permission_classes=[permissions.IsAuthenticated, IsOrganizationMember])
    def remove_gallery_image(self, request, slug=None):
        """Remove an image from organization gallery"""
        organization = self.get_object()
        image_id = request.query_params.get('image_id')
        
        if not image_id:
            return Response(
                {'error': 'image_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        image = get_object_or_404(
            OrganizationGallery,
            id=image_id,
            organization=organization
        )
        image.delete()
        
        return Response({'message': 'Gallery image removed successfully'})

    @action(detail=True, methods=['get'])
    def events(self, request, slug=None):
        """Get all events by this organization"""
        organization = self.get_object()
        from event.serializers import EventListSerializer
        
        events = organization.events.filter(is_published=True)
        
        # Filter by status
        event_status = request.query_params.get('status', None)
        if event_status:
            events = events.filter(status=event_status.upper())
        
        serializer = EventListSerializer(events, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def stats(self, request, slug=None):
        """Get organization statistics"""
        organization = self.get_object()
        
        # Check if user is a member
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
