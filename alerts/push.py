import json
import logging
import time

from django.conf import settings

from .models import NativePushDevice, PushSubscription


logger = logging.getLogger(__name__)
_apns_token = {'value': '', 'created_at': 0}


def _send_android_fcm(device, alert):
    """Šalje Android obaveštenje kroz Firebase Cloud Messaging."""
    if not settings.FIREBASE_CREDENTIALS_JSON:
        return 'disabled'
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        try:
            app = firebase_admin.get_app('briga-plus')
        except ValueError:
            credential_data = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
            app = firebase_admin.initialize_app(
                credentials.Certificate(credential_data),
                name='briga-plus',
            )
        messaging.send(
            messaging.Message(
                notification=messaging.Notification(title=alert.title, body=alert.body),
                data={'url': alert.url or '/', 'kind': alert.kind},
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        sound='default',
                        channel_id='briga_vazno',
                        icon='ic_stat_briga',
                        color='#0D7A58',
                    ),
                ),
                token=device.token,
            ),
            app=app,
        )
        return 'sent'
    except (ImportError, json.JSONDecodeError, ValueError, TypeError):
        logger.exception('Firebase konfiguracija za Briga+ nije ispravna.')
        return 'failed'
    except Exception as error:
        if error.__class__.__name__ in {
            'InvalidArgumentError', 'SenderIdMismatchError', 'UnregisteredError',
        }:
            return 'invalid'
        logger.exception('FCM obaveštenje nije poslato uređaju %s.', device.pk)
        return 'failed'


def _apns_authorization_token():
    """Pravi kratkotrajni Apple JWT; privatni ključ nikada ne napušta server."""
    now = int(time.time())
    if _apns_token['value'] and now - _apns_token['created_at'] < 45 * 60:
        return _apns_token['value']
    import jwt

    token = jwt.encode(
        {'iss': settings.APNS_TEAM_ID, 'iat': now},
        settings.APNS_PRIVATE_KEY,
        algorithm='ES256',
        headers={'kid': settings.APNS_KEY_ID},
    )
    _apns_token.update(value=token, created_at=now)
    return token


def _send_ios_apns(device, alert):
    """Šalje iPhone/iPad obaveštenje direktno kroz Apple Push servis."""
    if not settings.APNS_CONFIGURED:
        return 'disabled'
    try:
        import httpx

        host = 'https://api.sandbox.push.apple.com' if settings.APNS_USE_SANDBOX else 'https://api.push.apple.com'
        with httpx.Client(http2=True, timeout=10) as client:
            response = client.post(
                f'{host}/3/device/{device.token}',
                headers={
                    'authorization': f'bearer {_apns_authorization_token()}',
                    'apns-topic': settings.APNS_BUNDLE_ID,
                    'apns-push-type': 'alert',
                    'apns-priority': '10',
                },
                json={
                    'aps': {
                        'alert': {'title': alert.title, 'body': alert.body},
                        'sound': 'default',
                        'badge': 1,
                        **({'interruption-level': 'time-sensitive'} if alert.kind == 'sos' else {}),
                    },
                    'url': alert.url or '/',
                    'kind': alert.kind,
                },
            )
        if response.status_code == 200:
            return 'sent'
        reason = response.json().get('reason', '') if response.content else ''
        if response.status_code == 410 or reason in {'BadDeviceToken', 'DeviceTokenNotForTopic', 'Unregistered'}:
            return 'invalid'
        logger.warning('APNs je odbio Briga+ obaveštenje (%s: %s).', response.status_code, reason)
        return 'failed'
    except Exception:
        logger.exception('APNs obaveštenje nije poslato uređaju %s.', device.pk)
        return 'failed'


def send_native_push_alert(alert):
    """Šalje alert svim registrovanim telefonima primaoca."""
    result_counts = {'sent': 0, 'failed': 0, 'disabled': 0, 'invalid': 0}
    for device in NativePushDevice.objects.filter(user=alert.recipient):
        if device.platform == NativePushDevice.Platform.ANDROID:
            result = _send_android_fcm(device, alert)
        else:
            result = _send_ios_apns(device, alert)
        result_counts[result] = result_counts.get(result, 0) + 1
        if result == 'invalid':
            device.delete()
    return result_counts


def send_push_alert(alert):
    """Šalje isti alert web preglednicima i native Android/iOS aplikacijama."""
    native = send_native_push_alert(alert)
    delivery = {
        'native_sent': native['sent'],
        'native_registered': sum(native.values()),
        'native_failed': native['failed'] + native['invalid'],
        'web_sent': 0,
    }
    if not settings.VAPID_PUBLIC_KEY or not settings.VAPID_PRIVATE_KEY:
        logger.info('Briga+ push kind=%s recipient=%s delivery=%s', alert.kind, alert.recipient_id, delivery)
        return delivery
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.info('Briga+ push kind=%s recipient=%s delivery=%s', alert.kind, alert.recipient_id, delivery)
        return delivery

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
            delivery['web_sent'] += 1
        except WebPushException as error:
            response = getattr(error, 'response', None)
            if response is not None and response.status_code in {404, 410}:
                subscription.delete()
    logger.info('Briga+ push kind=%s recipient=%s delivery=%s', alert.kind, alert.recipient_id, delivery)
    return delivery
