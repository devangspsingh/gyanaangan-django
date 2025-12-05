from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import Visitor, Session, Event

class DashboardStatsView(APIView):
    """
    Returns aggregated stats for the admin dashboard.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        now = timezone.now()
        last_30_days = now - timedelta(days=30)
        
        # 1. Key Metrics
        total_visitors = Visitor.objects.count()
        total_sessions = Session.objects.count()
        total_events = Event.objects.count()
        active_sessions = Session.objects.filter(is_active=True).count()
        
        # 2. Charts Data (e.g., Visitors by OS)
        # Using top 5 to keep it clean
        visitors_by_os = Visitor.objects.values('os').annotate(count=Count('id')).order_by('-count')[:5]
        visitors_by_browser = Visitor.objects.values('browser').annotate(count=Count('id')).order_by('-count')[:5]
        visitors_by_device = Visitor.objects.values('device_type').annotate(count=Count('id')).order_by('-count')[:5]
        
        # 3. Activity over time (Last 30 days sessions)
        # Simple daily count (requires more complex query or multiple queries for sqlite compatibility, keeping it simple for now)
        # For a hackathon/MVP level, just returning total is fine, or we can do a loop if dataset is small.
        # Let's return raw aggregated data
        
        data = {
            "counts": {
                "total_visitors": total_visitors,
                "total_sessions": total_sessions,
                "total_events": total_events,
                "active_sessions": active_sessions,
                "unique_ips": Visitor.objects.values('ip_address').distinct().count(),
                "unique_users": Session.objects.filter(user__isnull=False).values('user').distinct().count(),
            },
            "charts": {
                "os": list(visitors_by_os),
                "browser": list(visitors_by_browser),
                "device": list(visitors_by_device),
            }
        }
        
        return Response(data)
