import json

from django.conf import settings

from .models import PushSubscription


def send_push_alert(alert):
    """Šalje web-push kada su VAPID ključevi podešeni; neuspele pretplate briše."""
    if not settings.VAPID_PUBLIC_KEY or not settings.VAPID_PRIVATE_KEY:
        return
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        return

    payload = json.dumps({'title': alert.title, 'body': alert.body, 'url': alert.url or '/'})
    for subscription in PushSubscription.objects.filter(user=alert.recipient):
        try:
            webpush(
                subscription_info={
                    'endpoint': subscription.endpoint,
                    'keys': {'p256dh': subscription.p256dh, 'auth': subscription.auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={'sub': settings.VAPID_SUBJECT},
            )
        except WebPushException as error:
            response = getattr(error, 'response', None)
            if response is not None and response.status_code in {404, 410}:
                subscription.delete()
