from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from families.models import Membership
from checkins.models import CheckIn
from reminders.models import Reminder
from caretasks.models import CareTask
from emergencies.models import EmergencyAlert
from families.models import EmergencyContact

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

# Create your tests here.
