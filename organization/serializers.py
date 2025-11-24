from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Organization, OrganizationMember, OrganizationGallery
from accounts.serializers import MinimalUserSerializer, PublicUserSerializer

User = get_user_model()


class OrganizationGallerySerializer(serializers.ModelSerializer):
    """Serializer for organization gallery images"""
    uploaded_by_details = MinimalUserSerializer(source='uploaded_by', read_only=True)
    
    class Meta:
        model = OrganizationGallery
        fields = [
            'id', 'organization', 'image', 'caption', 'display_order',
            'uploaded_by', 'uploaded_by_details', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'uploaded_by']

    def create(self, validated_data):
        # Set uploaded_by from request user
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)


class OrganizationMemberSerializer(serializers.ModelSerializer):
    """Serializer for organization members"""
    user_details = PublicUserSerializer(source='user', read_only=True)
    invited_by_details = MinimalUserSerializer(source='invited_by', read_only=True)
    
    class Meta:
        model = OrganizationMember
        fields = [
            'id', 'organization', 'user', 'user_details', 'role', 'permissions',
            'invited_by', 'invited_by_details', 'joined_at', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'joined_at', 'created_at', 'updated_at', 'invited_by']

    def create(self, validated_data):
        # Set invited_by from request user
        validated_data['invited_by'] = self.context['request'].user
        
        # Set default permissions based on role if not provided
        if 'permissions' not in validated_data or not validated_data['permissions']:
            role = validated_data.get('role', 'MEMBER')
            validated_data['permissions'] = OrganizationMember.get_default_permissions(role)
        
        return super().create(validated_data)

    def validate(self, data):
        # Ensure organization has at least one admin
        if self.instance and 'is_active' in data:
            if not data['is_active'] and self.instance.role == 'ADMIN':
                active_admins = OrganizationMember.objects.filter(
                    organization=self.instance.organization,
                    role='ADMIN',
                    is_active=True
                ).exclude(pk=self.instance.pk).count()
                
                if active_admins == 0:
                    raise serializers.ValidationError(
                        "Cannot deactivate the last admin of the organization."
                    )
        return data


class OrganizationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for organization lists - public data only, NO user-specific data"""
    member_count = serializers.IntegerField(read_only=True)
    event_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'logo', 'cover_image', 'description',
            'is_verified', 'is_active',
            'member_count', 'event_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

    def get_event_count(self, obj):
        return obj.events.filter(is_published=True).count()


class OrganizationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for organization - public data only, NO user-specific data"""
    gallery_images = OrganizationGallerySerializer(many=True, read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    admin_count = serializers.IntegerField(read_only=True)
    event_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'slug', 'description', 'logo', 'cover_image',
            'contact_email', 'contact_phone', 'website', 'social_links',
            'is_verified', 'is_active',
            'gallery_images', 'member_count', 'admin_count',
            'event_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

    def get_event_count(self, obj):
        return obj.events.filter(is_published=True).count()


class OrganizationCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating organizations"""
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'description', 'logo', 'cover_image',
            'contact_email', 'contact_phone', 'website', 'social_links',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Set created_by from request user
        validated_data['created_by'] = self.context['request'].user
        organization = super().create(validated_data)
        
        # Automatically add creator as admin
        OrganizationMember.objects.create(
            organization=organization,
            user=self.context['request'].user,
            role='ADMIN',
            permissions=OrganizationMember.get_default_permissions('ADMIN'),
            invited_by=self.context['request'].user
        )
        
        return organization

    def validate_name(self, value):
        # Check for duplicate names during update
        if self.instance:
            if Organization.objects.filter(name=value).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError("An organization with this name already exists.")
        return value
