# notifications.py
# Notification adapter for the visitor_hostel module.
# T-11: Decouples services.py from notification.views directly.

from notification.views import visitors_hostel_notif


def send_vh_notification(from_user, to_user, notif_type):
    """
    Send a visitor-hostel notification.

    Wraps visitors_hostel_notif so that services.py is not directly
    coupled to the notification module's internal view function.

    Args:
        from_user: The User instance initiating the action.
        to_user:   The User instance receiving the notification.
        notif_type: Notification type string (e.g. 'booking_confirmation').
    """
    if to_user is None:
        return
    visitors_hostel_notif(from_user, to_user, notif_type)
