from rest_framework import permissions


class IsOrganizationAdmin(permissions.BasePermission):
    """
    Permission class to check if user is an admin of the organization.
    """
    message = "You must be an admin of this organization to perform this action."

    def has_object_permission(self, request, view, obj):
        # obj is the organization
        if hasattr(obj, 'organization'):
            # If obj is a related object (e.g., Event), check the organization
            organization = obj.organization
        else:
            organization = obj
        
        return organization.is_admin(request.user)


class IsOrganizationMember(permissions.BasePermission):
    """
    Permission class to check if user is a member of the organization.
    """
    message = "You must be a member of this organization to perform this action."

    def has_object_permission(self, request, view, obj):
        # obj is the organization
        if hasattr(obj, 'organization'):
            # If obj is a related object, check the organization
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

    def has_object_permission(self, request, view, obj):
        # Get the required permission from the view
        permission_key = getattr(view, 'permission_required', None)
        if not permission_key:
            return False
        
        # obj is the organization
        if hasattr(obj, 'organization'):
            organization = obj.organization
        else:
            organization = obj
        
        # Get user's membership
        try:
            member = organization.members.get(user=request.user, is_active=True)
            return member.has_permission(permission_key)
        except:
            return False
