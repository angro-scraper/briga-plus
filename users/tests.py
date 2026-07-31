import json
import os
import re
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.core.management import call_command
from django.utils import timezone
from django.contrib.auth.models import User
from families.models import Membership
from users.models import AuditEvent, PilotFeedback, PrivacyConsent, UserContactProfile
from checkins.models import CheckIn
from checkins.models import DailyRoutine, HealthLog, RoutineCompletion
from reminders.models import Reminder
from caretasks.models import CareTask
from emergencies.models import EmergencyAlert
from families.models import CareDocument, CareProfile, EmergencyContact, FamilyInvite, FamilyVisit
from checkins.models import MoodEntry
from django.core.files.uploadedfile import SimpleUploadedFile
from alerts.models import Alert, NativePushDevice
from alerts.push import send_push_alert
from messaging.models import Message

class DashboardFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('mira', password='bezbedna-lozinka-123')
        self.client.force_login(self.user)
        self.client.post('/registracija/', {})
        from families.models import Family
        self.family = Family.objects.create(name='Miričina porodica')
        Membership.objects.create(user=self.user, family=self.family, role=Membership.Role.ADMIN)

    def test_checkin_and_reminder_flow(self):
        response = self.client.post('/', {'action': 'checkin'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CheckIn.objects.filter(user=self.user).count(), 1)
        response = self.client.post('/', {'action': 'reminder', 'title': 'Terapija', 'scheduled_for': '2026-08-01T09:00'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Reminder.objects.filter(user=self.user, title='Terapija').count(), 1)

    def test_health_endpoint(self):
        response = self.client.get('/zdravlje/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_service_worker_is_never_reused_without_a_fresh_check(self):
        response = self.client.get('/service-worker.js')
        self.assertEqual(response.status_code, 200)
        self.assertIn('no-cache', response['Cache-Control'])
        self.assertContains(response, "briga-plus-chat-sos-20260805")
        self.assertContains(response, 'self.skipWaiting()')

    def test_sophie_speech_requires_configured_service(self):
        response = self.client.post(
            '/sophie-govor/',
            data=json.dumps({'text': 'Poslednji unos je uredan.'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error'], 'Sophie servis još nije podešen.')

    def test_dashboard_redirects_to_briga_login(self):
        self.client.logout()
        response = self.client.get('/')
        self.assertRedirects(response, '/prijava/?next=/')

    def test_dashboard_never_uses_a_stale_page_cache(self):
        response = self.client.get('/')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertContains(response, '/static/briga-v2.css?v=20260805')
        self.assertContains(response, '/static/briga-v2.js?v=20260803')

    def test_chat_message_stays_open_and_notifies_another_family_member(self):
        caregiver = User.objects.create_user('ana_chat', password='bezbedna-lozinka-123')
        Membership.objects.create(user=caregiver, family=self.family, role=Membership.Role.CAREGIVER)

        response = self.client.post('/', {
            'action': 'message', 'return_modal': 'chat', 'body': 'Stižem za deset minuta.',
        })

        self.assertRedirects(response, '/?open=chat')
        self.assertTrue(Message.objects.filter(family=self.family, sender=self.user, body='Stižem za deset minuta.').exists())
        alert = Alert.objects.get(recipient=caregiver, kind=Alert.Kind.MESSAGE)
        self.assertEqual(alert.url, '/?open=chat')
        response = self.client.get('/?open=chat')
        self.assertContains(response, 'Stižem za deset minuta.')
        self.assertContains(response, "modal.showModal()")

    def test_chat_shows_latest_messages_and_has_fixed_mobile_composer(self):
        for number in range(55):
            Message.objects.create(
                family=self.family, sender=self.user, body=f'Poruka broj {number}',
            )

        response = self.client.get('/?open=chat')

        self.assertNotIn('Poruka broj 0', [message.body for message in response.context['chat_messages']])
        self.assertEqual(len(response.context['chat_messages']), 50)
        self.assertContains(response, 'Poruka broj 54')
        self.assertContains(response, 'class="chat-scroll"')
        self.assertContains(response, 'class="chat-composer"')
        self.assertContains(response, 'enterkeyhint="send"')

    def test_senior_can_use_same_family_chat_without_leaving_it(self):
        senior = User.objects.create_user('baka_chat', password='bezbedna-lozinka-123')
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)
        self.client.force_login(senior)

        response = self.client.post('/moj-dan/', {
            'action': 'message', 'body': 'Dobro sam, vidimo se kasnije.',
        })

        self.assertRedirects(response, '/?open=chat')
        self.assertTrue(Message.objects.filter(
            family=self.family, sender=senior, body='Dobro sam, vidimo se kasnije.',
        ).exists())
        self.assertTrue(self.user.alerts.filter(kind=Alert.Kind.MESSAGE).exists())
        response = self.client.get('/?open=chat')
        self.assertContains(response, 'id="chat"')
        self.assertContains(response, 'Dobro sam, vidimo se kasnije.')

    def test_main_application_routes_are_available_to_a_signed_in_user(self):
        for path in ('/', '/nalog/', '/politika-privatnosti/', '/uslovi-koriscenja/', '/service-worker.js', '/zdravlje/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_every_dashboard_control_opens_an_existing_dialog(self):
        family_response = self.client.get('/')
        family_html = family_response.content.decode()
        family_targets = set(re.findall(r'data-modal="([^"]+)"', family_html))
        family_dialogs = set(re.findall(r'<dialog[^>]+id="([^"]+)"', family_html))
        self.assertFalse(family_targets - family_dialogs)

        senior = User.objects.create_user('ruta_senior', password='bezbedna-lozinka-123')
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)
        self.client.force_login(senior)
        senior_response = self.client.get('/')
        senior_html = senior_response.content.decode()
        senior_targets = set(re.findall(r'data-dialog="([^"]+)"', senior_html))
        senior_dialogs = set(re.findall(r'<dialog[^>]+id="([^"]+)"', senior_html))
        self.assertFalse(senior_targets - senior_dialogs)

    def test_mobile_panels_expose_the_complete_feature_set(self):
        family_response = self.client.get('/')
        for marker in (
            'id="all-tools"', 'data-modal="chat"', 'data-modal="reminders"',
            'data-modal="tasks"', 'data-modal="contacts"', 'data-modal="documents"',
            'data-modal="visits"', 'data-modal="safety"', 'data-modal="devices"',
            'id="family-mobile-sos"', 'Pošalji GPS lokaciju i pozovi pomoć',
        ):
            self.assertContains(family_response, marker)

        senior = User.objects.create_user('kompletan_senior', password='bezbedna-lozinka-123')
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)
        self.client.force_login(senior)
        senior_response = self.client.get('/moj-dan/')
        for marker in (
            'id="senior-more"', 'id="routine-senior"', 'id="mood-senior"',
            'id="guidance-senior"', 'data-dialog="help"',
            'id="push-button-mobile"', 'id="voice-listen-mobile"',
            'fotografiju dokumenta ili PDF',
        ):
            self.assertContains(senior_response, marker)

    def test_native_phone_token_is_saved_for_the_signed_in_user(self):
        response = self.client.post(
            '/native-push-pretplata/',
            data=json.dumps({'platform': 'android', 'token': 'a' * 120}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.assertTrue(NativePushDevice.objects.filter(user=self.user, platform='android', token='a' * 120).exists())

    @patch('alerts.push._send_ios_apns', return_value='sent')
    @patch('alerts.push._send_android_fcm', return_value='sent')
    def test_alert_is_sent_to_both_native_mobile_platforms(self, send_android, send_ios):
        android = NativePushDevice.objects.create(user=self.user, platform='android', token='a' * 120)
        ios = NativePushDevice.objects.create(user=self.user, platform='ios', token='b' * 120)
        alert = Alert.objects.create(
            recipient=self.user, kind=Alert.Kind.SOS, title='SOS', body='Potrebna je pomoć.', url='/?open=alerts',
        )

        send_push_alert(alert)

        send_android.assert_called_once_with(android, alert)
        send_ios.assert_called_once_with(ios, alert)

    @patch('alerts.push._send_android_fcm', return_value='invalid')
    def test_invalid_native_token_is_removed(self, send_android):
        device = NativePushDevice.objects.create(user=self.user, platform='android', token='c' * 120)
        alert = Alert.objects.create(recipient=self.user, kind=Alert.Kind.REMINDER, title='Terapija')

        send_push_alert(alert)

        self.assertFalse(NativePushDevice.objects.filter(pk=device.pk).exists())

    def test_registration_saves_required_contact_information(self):
        response = self.client.post('/registracija/', {
            'first_name': 'Ana', 'last_name': 'Petrović', 'email': 'ana@example.com',
            'phone': '+381 64 123 4567', 'address': 'Kralja Petra 12, Beograd',
            'username': 'ana.petrovic', 'password1': 'Bezbedna-lozinka-123',
            'password2': 'Bezbedna-lozinka-123', 'privacy_consent': 'on',
        })
        self.assertRedirects(response, '/')
        user = User.objects.get(username='ana.petrovic')
        self.assertEqual(user.email, 'ana@example.com')
        self.assertEqual(user.get_full_name(), 'Ana Petrović')
        self.assertEqual(user.contact_profile.phone, '+381 64 123 4567')
        self.assertEqual(user.contact_profile.address, 'Kralja Petra 12, Beograd')

    def test_registration_rejects_duplicate_email(self):
        User.objects.create_user('postojeci', email='ana@example.com', password='Bezbedna-lozinka-123')
        response = self.client.post('/registracija/', {
            'first_name': 'Nova', 'last_name': 'Osoba', 'email': 'ANA@example.com',
            'phone': '+381641234567', 'address': 'Adresa 1', 'username': 'nova.osoba',
            'password1': 'Bezbedna-lozinka-123', 'password2': 'Bezbedna-lozinka-123', 'privacy_consent': 'on',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nalog sa ovom e-mail adresom već postoji.')

    def test_logout_uses_post_and_returns_to_login(self):
        response = self.client.post('/odjava/')
        self.assertRedirects(response, '/prijava/')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_senior_login_remembers_the_device_for_a_year(self):
        senior = User.objects.create_user('jelena', password='bezbedna-lozinka-123')
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)
        self.client.logout()

        response = self.client.post('/prijava/', {
            'username': 'jelena', 'password': 'bezbedna-lozinka-123',
        })

        self.assertRedirects(response, '/')
        self.assertGreaterEqual(self.client.session.get_expiry_age(), 60 * 60 * 24 * 364)

    def test_senior_cannot_create_or_complete_family_task(self):
        senior = User.objects.create_user('jelena', password='bezbedna-lozinka-123')
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)
        task = CareTask.objects.create(family=self.family, title='Preuzeti lekove')
        self.client.force_login(senior)
        self.client.post('/', {'action': 'task', 'title': 'Neautorizovan zadatak'})
        self.client.post('/', {'action': 'task_done', 'task_id': task.id})
        self.assertFalse(CareTask.objects.filter(family=self.family, title='Neautorizovan zadatak').exists())
        task.refresh_from_db(); self.assertFalse(task.done)

    def test_caregiver_sees_and_creates_reminder_for_senior(self):
        senior = User.objects.create_user('mama', password='bezbedna-lozinka-123')
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)
        response = self.client.post('/', {'action': 'reminder', 'title': 'Terapija', 'scheduled_for': '2026-08-01T09:00'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Reminder.objects.filter(user=senior, title='Terapija').exists())

    def test_task_can_have_family_assignee_and_deadline(self):
        caregiver = User.objects.create_user('ana', password='bezbedna-lozinka-123')
        Membership.objects.create(user=caregiver, family=self.family, role=Membership.Role.CAREGIVER)
        self.client.post('/', {
            'action': 'task', 'title': 'Preuzeti lekove', 'assignee_id': caregiver.id,
            'due_at': '2026-08-01T17:30',
        })
        task = CareTask.objects.get(family=self.family, title='Preuzeti lekove')
        self.assertEqual(task.assignee, caregiver)
        self.assertIsNotNone(task.due_at)

    def test_senior_cannot_create_reminder(self):
        senior = User.objects.create_user('jelena2', password='bezbedna-lozinka-123')
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)
        self.client.force_login(senior)
        self.client.post('/', {'action': 'reminder', 'title': 'Neovlašćen', 'scheduled_for': '2026-08-01T09:00'})
        self.assertFalse(Reminder.objects.filter(user=senior, title='Neovlašćen').exists())

    def test_caregiver_can_resolve_active_sos(self):
        caregiver = User.objects.create_user('marko', password='bezbedna-lozinka-123')
        Membership.objects.create(user=caregiver, family=self.family, role=Membership.Role.CAREGIVER)
        sos = EmergencyAlert.objects.create(family=self.family, raised_by=self.user, note='Treba mi pomoć.')
        self.client.force_login(caregiver)
        self.client.post('/', {'action': 'sos_resolve', 'sos_id': sos.id})
        sos.refresh_from_db()
        self.assertIsNotNone(sos.resolved_at)

    def test_sos_keeps_received_gps_coordinates(self):
        self.client.post('/', {
            'action': 'sos', 'latitude': '44.786568', 'longitude': '20.448922',
            'accuracy': '18.6', 'note': 'Potrebna mi je pomoć.',
        })
        sos = EmergencyAlert.objects.get(family=self.family)
        self.assertEqual(str(sos.latitude), '44.786568')
        self.assertEqual(str(sos.longitude), '20.448922')
        self.assertEqual(sos.accuracy_meters, 19)
        self.assertEqual(sos.note, 'Potrebna mi je pomoć.')

    @patch('users.views.send_push_alert', return_value={'native_sent': 1, 'web_sent': 0})
    def test_sos_alert_is_saved_and_pushed_to_every_other_family_member(self, send_push):
        caregiver = User.objects.create_user('sos_caregiver', password='bezbedna-lozinka-123')
        senior = User.objects.create_user('sos_senior', password='bezbedna-lozinka-123')
        Membership.objects.create(user=caregiver, family=self.family, role=Membership.Role.CAREGIVER)
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)

        self.client.post('/', {'action': 'sos', 'latitude': '44.8', 'longitude': '20.4'})

        alerts = Alert.objects.filter(kind=Alert.Kind.SOS).order_by('recipient_id')
        self.assertEqual(set(alerts.values_list('recipient_id', flat=True)), {caregiver.id, senior.id})
        self.assertTrue(all(alert.url == '/?open=alerts' for alert in alerts))
        self.assertEqual(send_push.call_count, 2)
        delivery_audit = AuditEvent.objects.get(event=AuditEvent.Event.SOS_UPDATED)
        self.assertEqual(delivery_audit.detail['recipients'], 2)
        self.assertEqual(delivery_audit.detail['native_sent'], 2)

    def test_coordinator_can_create_emergency_contact(self):
        self.client.post('/', {'action': 'contact', 'name': 'Ana Petrović', 'phone': '+381641234567', 'relationship': 'Ćerka', 'priority': '1'})
        contact = EmergencyContact.objects.get(family=self.family)
        self.assertEqual(contact.name, 'Ana Petrović')
        self.assertEqual(contact.phone, '+381641234567')

    def test_daily_reminder_creates_next_confirmation_slot(self):
        reminder = Reminder.objects.create(user=self.user, title='Terapija', scheduled_for=timezone.now(), repeat_daily=True)
        self.client.post('/', {'action': 'reminder_done', 'reminder_id': reminder.id})
        reminder.refresh_from_db()
        self.assertIsNotNone(reminder.completed_at)
        next_reminder = Reminder.objects.exclude(pk=reminder.pk).get(user=self.user, title='Terapija')
        self.assertTrue(next_reminder.repeat_daily)
        self.assertGreater(next_reminder.scheduled_for, timezone.now())

    def test_dashboard_prefers_family_that_has_care_person(self):
        from families.models import Family
        unrelated = Family.objects.create(name='Druga porodica')
        Membership.objects.create(user=self.user, family=unrelated, role=Membership.Role.ADMIN)
        senior = User.objects.create_user('baka', password='bezbedna-lozinka-123')
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)
        response = self.client.get('/')
        self.assertEqual(response.context['family'], self.family)
        self.assertEqual(response.context['care_person'], senior)

    def test_daily_routine_can_be_added_and_completed(self):
        senior = User.objects.create_user('rados', password='bezbedna-lozinka-123')
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)
        self.client.post('/', {'action': 'routine', 'title': 'Popiti čašu vode', 'category': 'wellbeing', 'part_of_day': 'morning'})
        routine = DailyRoutine.objects.get(user=senior, title='Popiti čašu vode')
        self.client.force_login(senior)
        self.client.post('/', {'action': 'routine_done', 'routine_id': routine.id})
        self.assertTrue(RoutineCompletion.objects.filter(routine=routine, completed_on=timezone.localdate()).exists())

    def test_health_log_and_non_urgent_help_request(self):
        senior = User.objects.create_user('zora', password='bezbedna-lozinka-123')
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)
        self.client.post('/', {'action': 'health_log', 'kind': 'pressure', 'value': '125/80', 'note': 'Dobro se osećam'})
        self.assertTrue(HealthLog.objects.filter(user=senior, kind='pressure', value='125/80').exists())
        self.client.force_login(senior)
        self.client.post('/', {'action': 'help_request', 'kind': 'call', 'note': 'Pozovite me kada možete.'})
        request = EmergencyAlert.objects.get(family=self.family, kind='call')
        self.assertEqual(request.note, 'Pozovite me kada možete.')

    def test_sos_response_can_be_acknowledged_and_marked_en_route(self):
        senior = User.objects.create_user('milena', password='bezbedna-lozinka-123')
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)
        sos = EmergencyAlert.objects.create(family=self.family, raised_by=senior)
        self.client.post('/', {'action': 'sos_acknowledge', 'sos_id': sos.id})
        self.client.post('/', {'action': 'sos_en_route', 'sos_id': sos.id})
        sos.refresh_from_db()
        self.assertEqual(sos.acknowledged_by, self.user)
        self.assertEqual(sos.responder, self.user)
        self.assertIsNotNone(sos.responder_en_route_at)
        self.assertTrue(senior.alerts.filter(title='SOS je viđen').exists())
        self.assertTrue(senior.alerts.filter(title='Pomoć je krenula').exists())

    @override_settings(BRIGA_ANDROID_APP_LINK_SHA256='AA:BB:CC')
    def test_android_app_link_file_is_available_after_certificate_setup(self):
        response = self.client.get('/.well-known/assetlinks.json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]['target']['package_name'], 'rs.brigaplus.app')
        self.assertEqual(response.json()[0]['target']['sha256_cert_fingerprints'], ['AA:BB:CC'])

    @override_settings(BRIGA_APPLE_APP_ID='TEAM123.rs.brigaplus.app')
    def test_ios_universal_link_file_is_available_after_apple_setup(self):
        response = self.client.get('/.well-known/apple-app-site-association')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['applinks']['details'][0]['appID'], 'TEAM123.rs.brigaplus.app')

    def test_pilot_feedback_is_saved_for_platform_team(self):
        self.client.post('/', {
            'action': 'pilot_feedback', 'category': 'ease', 'rating': 'ok',
            'message': 'Dugme za terapiju treba da bude veće.',
        })
        feedback = PilotFeedback.objects.get()
        self.assertEqual(feedback.user, self.user)
        self.assertEqual(feedback.family, self.family)

    def test_support_circle_can_claim_unassigned_task(self):
        task = CareTask.objects.create(family=self.family, title='Preuzeti terapiju')
        self.client.post('/', {'action': 'task_claim', 'task_id': task.id})
        task.refresh_from_db()
        self.assertEqual(task.assignee, self.user)

    def test_care_profile_mood_and_visit_flow(self):
        senior = User.objects.create_user('deda', password='bezbedna-lozinka-123')
        caregiver = User.objects.create_user('ivana', password='bezbedna-lozinka-123')
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)
        Membership.objects.create(user=caregiver, family=self.family, role=Membership.Role.CAREGIVER)
        self.client.post('/', {'action': 'care_profile', 'allergies': 'Penicilin', 'doctor_name': 'Dr Ana'})
        self.assertEqual(CareProfile.objects.get(user=senior).allergies, 'Penicilin')
        self.client.force_login(senior)
        self.client.post('/', {'action': 'mood', 'mood': 'good'})
        self.assertEqual(MoodEntry.objects.get(user=senior).mood, 'good')
        self.client.force_login(self.user)
        self.client.post('/', {'action': 'visit', 'visitor_id': caregiver.id, 'scheduled_for': '2026-08-01T10:00', 'note': 'Donosi lekove'})
        visit = FamilyVisit.objects.get(family=self.family)
        self.assertEqual(visit.visitor, caregiver)
        self.client.force_login(caregiver)
        self.client.post('/', {'action': 'visit_status', 'visit_id': visit.id, 'status': 'arrived'})
        visit.refresh_from_db()
        self.assertEqual(visit.status, 'arrived')

    def test_document_vault_is_limited_to_family(self):
        senior = User.objects.create_user('baka_dok', password='bezbedna-lozinka-123')
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)
        upload = SimpleUploadedFile('nalaz.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        self.client.post('/', {'action': 'document', 'title': 'Nalaz', 'category': 'report', 'document': upload})
        document = CareDocument.objects.get(user=senior)
        dashboard = self.client.get('/')
        self.assertContains(dashboard, f'/media/{document.document.name}')
        response = self.client.get(document.document.url)
        self.assertEqual(response.status_code, 200)
        stranger = User.objects.create_user('stranac', password='bezbedna-lozinka-123')
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(document.document.url).status_code, 404)

    def test_health_log_accepts_private_pdf_or_document_photo(self):
        senior = User.objects.create_user('baka_dnevnik', password='bezbedna-lozinka-123')
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)
        upload = SimpleUploadedFile('pritisak.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        self.client.post('/', {
            'action': 'health_log', 'kind': 'pressure', 'value': '125/80',
            'note': 'Jutarnje merenje', 'attachment': upload,
        })
        log = HealthLog.objects.get(user=senior, value='125/80')
        self.assertTrue(log.attachment.name.startswith('health_logs/'))
        self.assertEqual(self.client.get(log.attachment.url).status_code, 200)
        stranger = User.objects.create_user('stranac_dnevnik', password='bezbedna-lozinka-123')
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(log.attachment.url).status_code, 404)

    def test_cared_person_is_sent_to_a_separate_personal_panel(self):
        senior = User.objects.create_user('olga_panel', password='bezbedna-lozinka-123', first_name='Olga')
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)
        self.client.force_login(senior)
        response = self.client.get('/')
        self.assertContains(response, 'MOJ DAN')
        self.assertContains(response, 'SOS — POZOVI POMOĆ')
        self.assertContains(response, 'id="therapy"')
        self.assertContains(response, 'data-dialog="therapy"')
        self.assertContains(response, 'id="family-senior"')
        self.assertContains(response, 'data-dialog="family-senior"')

    def test_cared_person_can_add_pdf_to_personal_health_diary(self):
        senior = User.objects.create_user('gordana_panel', password='bezbedna-lozinka-123')
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)
        self.client.force_login(senior)
        upload = SimpleUploadedFile('nalaz.pdf', b'%PDF-1.4 test', content_type='application/pdf')
        response = self.client.post('/moj-dan/', {
            'action': 'health_log', 'kind': 'note', 'note': 'Nalaz je dodat.', 'attachment': upload,
        })
        self.assertRedirects(response, '/moj-dan/')
        self.assertTrue(HealthLog.objects.filter(user=senior, attachment__startswith='health_logs/').exists())

    def test_senior_can_open_simple_screen(self):
        senior = User.objects.create_user('olga', password='bezbedna-lozinka-123')
        Membership.objects.create(user=senior, family=self.family, role=Membership.Role.SENIOR)
        self.client.force_login(senior)
        response = self.client.get('/jednostavno/')
        self.assertEqual(response.status_code, 200)

    def test_admin_creates_single_use_invite_for_cared_person(self):
        response = self.client.post('/', {
            'action': 'invite_create', 'role': 'senior', 'access_level': 'basic',
            'recipient_label': 'Jelena Petrović',
        })
        self.assertEqual(response.status_code, 302)
        invite = FamilyInvite.objects.get(family=self.family)
        self.assertEqual(invite.role, Membership.Role.SENIOR)
        self.client.logout()
        response = self.client.get(invite.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        response = self.client.post(invite.get_absolute_url(), {
            'first_name': 'Jelena', 'last_name': 'Petrović', 'email': 'jelena@example.com',
            'phone': '+381641112233', 'address': 'Bulevar oslobođenja 10, Novi Sad',
            'username': 'pozvana_jelena',
            'password1': 'bezbedna-lozinka-123',
            'password2': 'bezbedna-lozinka-123',
            'privacy_consent': 'on',
        })
        self.assertRedirects(response, '/')
        joined = User.objects.get(username='pozvana_jelena')
        self.assertTrue(Membership.objects.filter(family=self.family, user=joined, role=Membership.Role.SENIOR).exists())
        self.assertEqual(joined.contact_profile.phone, '+381641112233')
        invite.refresh_from_db()
        self.assertEqual(invite.accepted_by, joined)
        self.assertTrue(PrivacyConsent.objects.filter(user=joined).exists())
        self.client.logout()
        self.assertEqual(self.client.get(invite.get_absolute_url()).status_code, 404)

    def test_admin_can_approve_full_access_for_family_member(self):
        caregiver = User.objects.create_user('porodicni_clan', password='bezbedna-lozinka-123')
        member = Membership.objects.create(
            user=caregiver, family=self.family, role=Membership.Role.CAREGIVER,
            access_level=Membership.AccessLevel.BASIC,
        )
        response = self.client.post('/', {
            'action': 'member_access', 'membership_id': member.id,
            'access_level': Membership.AccessLevel.FULL,
        })
        self.assertEqual(response.status_code, 302)
        member.refresh_from_db()
        self.assertEqual(member.access_level, Membership.AccessLevel.FULL)
        self.assertTrue(AuditEvent.objects.filter(event=AuditEvent.Event.ACCESS_CHANGED, actor=self.user).exists())

    def test_user_can_accept_privacy_policy_and_view_legal_pages(self):
        self.assertEqual(self.client.get('/politika-privatnosti/').status_code, 200)
        self.assertEqual(self.client.get('/uslovi-koriscenja/').status_code, 200)
        response = self.client.post('/nalog/', {'action': 'accept_privacy'})
        self.assertRedirects(response, '/nalog/')
        self.assertTrue(PrivacyConsent.objects.filter(user=self.user).exists())

    def test_account_deletion_requires_explicit_confirmation(self):
        response = self.client.post('/nalog/', {'action': 'delete_account', 'confirmation': 'ne'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_platform_control_center_is_staff_only(self):
        response = self.client.get('/kontrola/')
        self.assertEqual(response.status_code, 302)
        staff = User.objects.create_user('vlasnik', password='bezbedna-lozinka-123', is_staff=True)
        self.client.force_login(staff)
        response = self.client.get('/kontrola/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'BRIGA+ OPERATIVNI CENTAR')
        self.assertRedirects(self.client.get('/'), '/kontrola/')

    def test_bootstrap_owner_from_environment_is_platform_staff(self):
        with patch.dict(os.environ, {
            'BRIGA_OWNER_USERNAME': 'glavni_vlasnik',
            'BRIGA_OWNER_PASSWORD': 'bezbedna-lozinka-123',
        }, clear=False):
            call_command('bootstrap_owner')
        owner = User.objects.get(username='glavni_vlasnik')
        self.assertTrue(owner.is_staff)
        self.assertTrue(owner.is_superuser)
        self.assertTrue(owner.check_password('bezbedna-lozinka-123'))

# Create your tests here.
