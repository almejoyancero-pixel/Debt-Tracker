"""
Context processors for making data available to all templates
"""
from .models import Notification


def unread_notifications(request):
    """
    Add unread notifications count to all template contexts.
    This allows the notification badge to appear in the navbar on all pages.
    
    The badge shows unread notifications count.
    Pending debts are handled through 'debt_added' notifications.
    """
    if request.user.is_authenticated:
        # Count unread notifications (includes debt_added notifications)
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        
        return {
            'unread_notifications_count': unread_count
        }
    return {
        'unread_notifications_count': 0
    }
