

from rest_framework import permissions
from django.shortcuts import get_object_or_404
# Replace 'yourapp' with your actual app name
from django.apps import apps 

class IsOrganizationAdmin(permissions.BasePermission):
    """
    Permission class to check if user is an admin of the organization.
    Safe for both Detail Views and Nested List Views.
    """
    message = "You must be an admin of this organization to perform this action."

    def has_permission(self, request, view):
        # 1. Basic Auth Check
        if not (request.user and request.user.is_authenticated):
            return False

        # 2. Handle List/Nested Views (The Fix)
        # Check if organization ID is in the URL (e.g., /organizations/<pk>/members/)
        # Adjust 'pk' or 'organization_pk' based on your URL conf
        org_pk = view.kwargs.get('pk') or view.kwargs.get('organization_pk')

        if org_pk:
            # Dynamically get model to prevent circular imports
            Organization = apps.get_model('yourapp', 'Organization') 
            try:
                # We check permissions immediately against the ID in the URL
                organization = Organization.objects.get(pk=org_pk)
                
                # If the view is for an Organization object itself (Detail view),
                # we can defer to has_object_permission to avoid double DB hits.
                # But for nested routes (members list), we MUST check here.
                if view.basename == 'members': # Example: check view name if possible
                     return organization.is_admin(request.user)
                
                # Safer default: Check it now. 
                return organization.is_admin(request.user)
            except Organization.DoesNotExist:
                # If org doesn't exist, return False (403) or let the view handle 404
                return False 

        return True

    def has_object_permission(self, request, view, obj):
        # This handles Detail views (GET /organizations/1/)
        if hasattr(obj, 'organization'):
            organization = obj.organization
        else:
            organization = obj
        
        return organization.is_admin(request.user)


class IsOrganizationMember(permissions.BasePermission):
    """
    Permission class to check if user is a member of the organization.
    """
    message = "You must be a member of this organization to perform this action."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
            
        # Optional: Add similar logic here if you want to prevent 
        # random users from seeing the member list (Privacy)
        return True

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'organization'):
            organization = obj.organization
        else:
            organization = obj
        
        return organization.has_member(request.user)


class HasOrganizationPermission(permissions.BasePermission):
    """
    Permission class to check specific organization permissions.
    Usage: Add permission_required attribute to the view.
    """
    message = "You do not have the required permission to perform this action."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        permission_key = getattr(view, 'permission_required', None)
        if not permission_key:
            return False
        
        if hasattr(obj, 'organization'):
            organization = obj.organization
        else:
            organization = obj
        
        # Improved error handling (specific Exception)
        try:
            member = organization.members.get(user=request.user, is_active=True)
            return member.has_permission(permission_key)
        except getattr(organization.members.model, 'DoesNotExist', Exception):
            return False