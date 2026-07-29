from django.test import TestCase
from django.contrib.auth.models import User
from families.models import Membership
from checkins.models import CheckIn
from reminders.models import Reminder
from caretasks.models import CareTask

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

# Create your tests here.
