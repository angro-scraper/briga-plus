import os
from unittest.mock import patch

from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
from django.contrib.auth.models import User
from families.models import Membership
from checkins.models import CheckIn
from checkins.models import DailyRoutine, HealthLog, RoutineCompletion
from reminders.models import Reminder
from caretasks.models import CareTask
from emergencies.models import EmergencyAlert
from families.models import CareDocument, CareProfile, EmergencyContact, FamilyInvite, FamilyVisit
from checkins.models import MoodEntry
from django.core.files.uploadedfile import SimpleUploadedFile

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

    def test_dashboard_redirects_to_briga_login(self):
        self.client.logout()
        response = self.client.get('/')
        self.assertRedirects(response, '/prijava/?next=/')

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
            'note': 'Potrebna mi je pomoć.',
        })
        sos = EmergencyAlert.objects.get(family=self.family)
        self.assertEqual(str(sos.latitude), '44.786568')
        self.assertEqual(str(sos.longitude), '20.448922')
        self.assertEqual(sos.note, 'Potrebna mi je pomoć.')

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
        response = self.client.get(document.document.url)
        self.assertEqual(response.status_code, 200)
        stranger = User.objects.create_user('stranac', password='bezbedna-lozinka-123')
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(document.document.url).status_code, 404)

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
            'username': 'pozvana_jelena',
            'password1': 'bezbedna-lozinka-123',
            'password2': 'bezbedna-lozinka-123',
        })
        self.assertRedirects(response, '/')
        joined = User.objects.get(username='pozvana_jelena')
        self.assertTrue(Membership.objects.filter(family=self.family, user=joined, role=Membership.Role.SENIOR).exists())
        invite.refresh_from_db()
        self.assertEqual(invite.accepted_by, joined)
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

    def test_platform_control_center_is_staff_only(self):
        response = self.client.get('/kontrola/')
        self.assertEqual(response.status_code, 302)
        staff = User.objects.create_user('vlasnik', password='bezbedna-lozinka-123', is_staff=True)
        self.client.force_login(staff)
        response = self.client.get('/kontrola/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'BRIGA+ OPERATIVNI CENTAR')

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
