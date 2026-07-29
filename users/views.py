import json
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from alerts.models import Alert, PushSubscription
from alerts.push import send_push_alert
from caretasks.models import CareTask
from checkins.models import CheckIn
from emergencies.models import EmergencyAlert
from families.models import EmergencyContact, Family, Membership
from messaging.models import Message, VoiceMessage
from reminders.models import Reminder


def notify_family(family, sender, kind, title, body='', url='/'):
    recipients = family.memberships.exclude(user=sender).values_list('user_id', flat=True)
    alerts = Alert.objects.bulk_create([
        Alert(recipient_id=user_id, kind=kind, title=title, body=body, url=url) for user_id in recipients
    ])
    for alert in alerts:
        send_push_alert(alert)


def can_coordinate(membership):
    return membership and membership.role in {Membership.Role.ADMIN, Membership.Role.CAREGIVER}


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            family = Family.objects.create(name=f'Porodica {user.username}')
            Membership.objects.create(user=user, family=family, role=Membership.Role.ADMIN)
            login(request, user)
            return redirect('pocetna')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


def service_worker(request):
    return render(request, 'service-worker.js', content_type='application/javascript')


def health(request):
    return JsonResponse({'status': 'ok', 'application': 'Briga+', 'version': '0.2.0'})


@login_required
def protected_media(request, path):
    reminder = Reminder.objects.filter(package_photo=path).select_related('user').first()
    voice = VoiceMessage.objects.filter(audio=path).select_related('family').first()
    if reminder:
        family_ids = request.user.family_memberships.values_list('family_id', flat=True)
        allowed = reminder.user_id == request.user.id or Membership.objects.filter(family_id__in=family_ids, user=reminder.user).exists()
    elif voice:
        allowed = voice.family.memberships.filter(user=request.user).exists()
    else:
        allowed = False
    if not allowed:
        raise Http404
    try:
        return FileResponse(open(settings.MEDIA_ROOT / path, 'rb'))
    except OSError as error:
        raise Http404 from error


@require_POST
@login_required
def push_subscribe(request):
    try:
        subscription = json.loads(request.body.decode('utf-8'))
        endpoint = subscription['endpoint']
        keys = subscription['keys']
        p256dh, auth = keys['p256dh'], keys['auth']
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Neispravna push pretplata.'}, status=400)
    if not settings.VAPID_PUBLIC_KEY:
        return JsonResponse({'ok': False, 'error': 'Push obaveštenja još nisu podešena.'}, status=503)
    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={'user': request.user, 'p256dh': p256dh, 'auth': auth},
    )
    return JsonResponse({'ok': True})


@login_required
def dashboard(request):
    memberships = request.user.family_memberships.select_related('family')
    membership = memberships.filter(family__memberships__role=Membership.Role.SENIOR).distinct().first() or memberships.first()
    family = membership.family if membership else None
    senior_membership = family.memberships.filter(role=Membership.Role.SENIOR).select_related('user').first() if family else None
    care_user = senior_membership.user if senior_membership and can_coordinate(membership) else request.user

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'checkin' and (membership.role == Membership.Role.SENIOR or care_user == request.user):
            note = request.POST.get('note', '').strip()[:240]
            CheckIn.objects.create(user=request.user, note=note)
            if family:
                notify_family(family, request.user, Alert.Kind.CHECKIN, f'Potvrda: {request.user.username} je dobro', note)
        elif action == 'message' and family:
            body = request.POST.get('body', '').strip()
            if body:
                Message.objects.create(family=family, sender=request.user, body=body)
                notify_family(family, request.user, Alert.Kind.MESSAGE, f'Nova poruka od {request.user.username}', body[:180])
        elif action == 'voice_message' and family:
            audio = request.FILES.get('audio')
            if audio and audio.size <= 12 * 1024 * 1024 and audio.content_type.startswith('audio/'):
                VoiceMessage.objects.create(family=family, sender=request.user, audio=audio)
                notify_family(family, request.user, Alert.Kind.MESSAGE, f'Glasovna poruka od {request.user.username}', 'Otvorite Briga+ i preslušajte poruku.')
            else:
                messages.error(request, 'Glasovna poruka mora biti audio zapis manji od 12 MB.')
        elif action == 'task' and family and can_coordinate(membership):
            title = request.POST.get('title', '').strip()
            try:
                due_at = timezone.datetime.fromisoformat(request.POST['due_at']) if request.POST.get('due_at') else None
                if due_at and timezone.is_naive(due_at):
                    due_at = timezone.make_aware(due_at)
            except ValueError:
                due_at = None
                messages.error(request, 'Rok zadatka nije ispravan.')
            assigned = family.memberships.filter(user_id=request.POST.get('assignee_id')).select_related('user').first()
            if title:
                CareTask.objects.create(family=family, title=title, assignee=assigned.user if assigned else request.user, due_at=due_at)
        elif action == 'task_done' and family and can_coordinate(membership):
            family.tasks.filter(pk=request.POST.get('task_id')).update(done=True)
        elif action == 'reminder' and family and can_coordinate(membership):
            try:
                scheduled = timezone.datetime.fromisoformat(request.POST['scheduled_for'])
                if timezone.is_naive(scheduled):
                    scheduled = timezone.make_aware(scheduled)
                title = request.POST['title'].strip()
                kind = request.POST.get('kind', Reminder.Kind.MEDICINE)
                package_photo = request.FILES.get('package_photo')
                if not title or kind not in Reminder.Kind.values:
                    raise ValueError
                if package_photo and (package_photo.size > 5 * 1024 * 1024 or not package_photo.content_type.startswith('image/')):
                    raise ValueError
                Reminder.objects.create(
                    user=care_user, title=title, kind=kind, scheduled_for=scheduled,
                    repeat_daily=bool(request.POST.get('repeat_daily')),
                    dosage=request.POST.get('dosage', '').strip()[:120],
                    instructions=request.POST.get('instructions', '').strip()[:300],
                    package_photo=package_photo,
                )
            except (KeyError, ValueError):
                messages.error(request, 'Proverite podatke terapije i fotografiju pakovanja.')
        elif action == 'reminder_done':
            reminder = Reminder.objects.filter(user=care_user, pk=request.POST.get('reminder_id')).first()
            if reminder and not reminder.completed_at:
                reminder.completed_at = timezone.now()
                reminder.save(update_fields=['completed_at'])
                if reminder.repeat_daily:
                    next_time = reminder.scheduled_for + timedelta(days=1)
                    while next_time <= timezone.now():
                        next_time += timedelta(days=1)
                    Reminder.objects.create(
                        user=reminder.user, title=reminder.title, kind=reminder.kind, scheduled_for=next_time,
                        repeat_daily=True, dosage=reminder.dosage, instructions=reminder.instructions,
                        package_photo=reminder.package_photo.name,
                    )
                if family:
                    notify_family(family, request.user, Alert.Kind.REMINDER, f'Potvrđeno: {reminder.title}', f'{request.user.username} je potvrdio/la stavku terapije.')
        elif action == 'contact' and family and can_coordinate(membership):
            name, phone = request.POST.get('name', '').strip(), request.POST.get('phone', '').strip()
            if name and phone:
                try:
                    priority = min(max(int(request.POST.get('priority', 1) or 1), 1), 9)
                except ValueError:
                    priority = 1
                EmergencyContact.objects.create(
                    family=family, name=name[:120], phone=phone[:32],
                    relationship=request.POST.get('relationship', '').strip()[:80],
                    priority=priority,
                )
        elif action == 'contact_delete' and family and can_coordinate(membership):
            family.emergency_contacts.filter(pk=request.POST.get('contact_id')).delete()
        elif action == 'sos' and family:
            EmergencyAlert.objects.create(
                family=family, raised_by=request.user, latitude=request.POST.get('latitude') or None,
                longitude=request.POST.get('longitude') or None, note=request.POST.get('note', '').strip()[:280],
            )
            notify_family(family, request.user, Alert.Kind.SOS, f'SOS: {request.user.username} traži pomoć', 'Otvorite Briga+ za GPS lokaciju i rutu.')
            messages.error(request, 'SOS je poslat članovima porodice.')
        elif action == 'sos_resolve' and family and can_coordinate(membership):
            family.emergencies.filter(pk=request.POST.get('sos_id')).update(resolved_at=timezone.now())
        elif action == 'invite' and family and membership.role == Membership.Role.ADMIN:
            invited = User.objects.filter(username=request.POST.get('username', '').strip()).first()
            if invited:
                Membership.objects.get_or_create(family=family, user=invited, defaults={'role': request.POST.get('role', Membership.Role.CAREGIVER)})
                messages.success(request, 'Član porodice je dodat.')
            else:
                messages.error(request, 'Korisnik nije pronađen. Neka najpre napravi nalog.')
        elif action == 'alert_read':
            request.user.alerts.filter(pk=request.POST.get('alert_id')).update(read_at=timezone.now())
        return redirect('pocetna')

    now = timezone.now()
    week_start, week_end = now - timedelta(days=7), now + timedelta(days=7)
    active_reminders = care_user.reminders.filter(completed_at__isnull=True)
    next_reminder = active_reminders.filter(scheduled_for__gte=now).first()
    overdue_reminders = active_reminders.filter(scheduled_for__lt=now)
    tasks = family.tasks.all()[:8] if family else []
    care_week = {
        'checkins': care_user.checkins.filter(created_at__gte=week_start).count(),
        'taken': care_user.reminders.filter(completed_at__gte=week_start).count(),
        'missed': care_user.reminders.filter(completed_at__isnull=True, scheduled_for__lt=now).count(),
        'upcoming': care_user.reminders.filter(completed_at__isnull=True, scheduled_for__range=(now, week_end)).count(),
        'open_tasks': family.tasks.filter(done=False).count() if family else 0,
        'overdue_tasks': family.tasks.filter(done=False, due_at__lt=now).count() if family else 0,
    }
    return render(request, 'dashboard.html', {
        'family': family, 'membership': membership, 'care_person': care_user,
        'last_checkin': care_user.checkins.first(), 'reminders': active_reminders[:8], 'next_reminder': next_reminder,
        'overdue_reminders': overdue_reminders[:4], 'tasks': tasks,
        'chat_messages': family.messages.select_related('sender').all()[:8] if family else [],
        'voice_messages': family.voice_messages.select_related('sender').all()[:8] if family else [],
        'sos_active': family.emergencies.filter(resolved_at__isnull=True).first() if family else None,
        'members': family.memberships.select_related('user').all() if family else [],
        'contacts': family.emergency_contacts.all() if family else [],
        'alerts': request.user.alerts.filter(read_at__isnull=True)[:6], 'unread_alert_count': request.user.alerts.filter(read_at__isnull=True).count(), 'care_week': care_week,
        'push_public_key': settings.VAPID_PUBLIC_KEY,
    })
