from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.utils import timezone
from families.models import Family, Membership
from checkins.models import CheckIn
from reminders.models import Reminder
from caretasks.models import CareTask
from messaging.models import Message
from emergencies.models import EmergencyAlert
from django.contrib.auth.models import User
from alerts.models import Alert

def notify_family(family, sender, kind, title, body=''):
    recipients = family.memberships.exclude(user=sender).values_list('user_id', flat=True)
    Alert.objects.bulk_create([Alert(recipient_id=user_id, kind=kind, title=title, body=body) for user_id in recipients])

def can_coordinate(membership):
    return membership and membership.role in {Membership.Role.ADMIN, Membership.Role.CAREGIVER}

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(); family = Family.objects.create(name=f'Porodica {user.username}')
            Membership.objects.create(user=user, family=family, role=Membership.Role.ADMIN)
            login(request, user); return redirect('pocetna')
    else: form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

def service_worker(request):
    return render(request, 'service-worker.js', content_type='application/javascript')

def health(request):
    return JsonResponse({'status': 'ok', 'application': 'Briga+', 'version': '0.1.0'})

@login_required
def dashboard(request):
    membership = request.user.family_memberships.select_related('family').first()
    family = membership.family if membership else None
    senior_membership = family.memberships.filter(role=Membership.Role.SENIOR).select_related('user').first() if family else None
    care_user = senior_membership.user if senior_membership and can_coordinate(membership) else request.user
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'checkin' and (membership.role == Membership.Role.SENIOR or care_user == request.user):
            CheckIn.objects.create(user=request.user, note=request.POST.get('note', '').strip()[:240])
        elif action == 'message' and family:
            body = request.POST.get('body','').strip()
            if body:
                Message.objects.create(family=family, sender=request.user, body=body)
                notify_family(family, request.user, Alert.Kind.MESSAGE, f'Nova poruka od {request.user.username}', body[:180])
        elif action == 'task' and family and can_coordinate(membership):
            title = request.POST.get('title', '').strip()
            try:
                due_at = timezone.datetime.fromisoformat(request.POST['due_at']) if request.POST.get('due_at') else None
                if due_at and timezone.is_naive(due_at): due_at = timezone.make_aware(due_at)
            except ValueError:
                due_at = None
                messages.error(request, 'Rok zadatka nije ispravan.')
            assigned_membership = family.memberships.filter(user_id=request.POST.get('assignee_id')).select_related('user').first()
            if title:
                CareTask.objects.create(family=family, title=title, assignee=assigned_membership.user if assigned_membership else request.user, due_at=due_at)
        elif action == 'task_done' and family and can_coordinate(membership): family.tasks.filter(pk=request.POST.get('task_id')).update(done=True)
        elif action == 'reminder' and family and can_coordinate(membership):
            try:
                scheduled = timezone.datetime.fromisoformat(request.POST['scheduled_for'])
                if timezone.is_naive(scheduled): scheduled = timezone.make_aware(scheduled)
                title = request.POST['title'].strip()
                if not title: raise ValueError
                kind = request.POST.get('kind', Reminder.Kind.MEDICINE)
                if kind not in Reminder.Kind.values: raise ValueError
                Reminder.objects.create(user=care_user, title=title, kind=kind, scheduled_for=scheduled, repeat_daily=bool(request.POST.get('repeat_daily')))
            except (KeyError, ValueError): messages.error(request, 'Proverite datum podsetnika.')
        elif action == 'reminder_done':
            Reminder.objects.filter(user=care_user, pk=request.POST.get('reminder_id')).update(completed_at=timezone.now())
        elif action == 'invite' and family and membership.role == Membership.Role.ADMIN:
            invited = User.objects.filter(username=request.POST.get('username', '').strip()).first()
            if invited:
                Membership.objects.get_or_create(family=family, user=invited, defaults={'role': request.POST.get('role', Membership.Role.CAREGIVER)})
                messages.success(request, 'Član porodice je dodat.')
            else: messages.error(request, 'Korisnik nije pronađen. Neka najpre napravi nalog.')
        elif action == 'sos' and family:
            EmergencyAlert.objects.create(family=family, raised_by=request.user, latitude=request.POST.get('latitude') or None, longitude=request.POST.get('longitude') or None, note=request.POST.get('note', '').strip()[:280])
            notify_family(family, request.user, Alert.Kind.SOS, f'SOS: {request.user.username} traži pomoć', 'Otvorite Briga+ za lokaciju i rutu.')
            messages.error(request, 'SOS je poslat članovima porodice.')
        elif action == 'sos_resolve' and family and can_coordinate(membership): family.emergencies.filter(pk=request.POST.get('sos_id')).update(resolved_at=timezone.now())
        elif action == 'alert_read': request.user.alerts.filter(pk=request.POST.get('alert_id')).update(read_at=timezone.now())
        return redirect('pocetna')
    return render(request, 'dashboard.html', {
        'family': family, 'membership': membership,
        'care_person': care_user, 'last_checkin': care_user.checkins.first(), 'reminders': care_user.reminders.filter(completed_at__isnull=True)[:5],
        'tasks': family.tasks.all()[:6] if family else [], 'messages': family.messages.select_related('sender').all()[:8] if family else [],
        'sos_active': family.emergencies.filter(resolved_at__isnull=True).first() if family else None,
        'members': family.memberships.select_related('user').all() if family else [],
        'alerts': request.user.alerts.filter(read_at__isnull=True)[:6],
    })
