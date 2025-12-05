from rest_framework import permissions
from tracking.models import Visitor

class IsVisitorAllowed(permissions.BasePermission):
    """
    Permission check to block 'force_login' (if anonymous) or 'block' visitors.
    Expects 'X-Visitor-Id' header from the client.
    """

    def has_permission(self, request, view):
        # 1. Blocked visitors are explicitly blocked regardless of authentication?
        #    Usually, if you log in, you are a User. 
        #    But the User might be associated with a blocked Visitor ID (device).
        #    Let's handle the Header logic first.
        
        visitor_id = request.headers.get('X-Visitor-Id')
        
        if not visitor_id:
            # If no visitor ID is provided, strictly speaking we might want to allow 
            # (fallback) or block. For now, we allow, assuming normal auth checks will handle weak users.
            # But the requirement is to "Block correct securing".
            return True

        try:
            visitor = Visitor.objects.get(visitor_id=visitor_id)
            
            if visitor.access_status == 'block':
                return False
            
            if visitor.access_status == 'force_login':
                # If they are authenticated, they are fine.
                if request.user and request.user.is_authenticated:
                    return True
                # Otherwise, block access (require login)
                return False
                
        except Visitor.DoesNotExist:
            pass

        return True
