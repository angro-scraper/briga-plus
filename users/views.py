import json
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from alerts.models import Alert, PushSubscription
from alerts.push import send_push_alert
from caretasks.models import CareTask
from checkins.models import CheckIn, DailyRoutine, HealthLog, MoodEntry, RoutineCompletion
from emergencies.models import EmergencyAlert
from families.models import CareDevice, CareDocument, CareProfile, EmergencyContact, Family, FamilyInvite, FamilyVisit, Membership
from messaging.models import Message, VoiceMessage
from reminders.models import Reminder
from users.forms import BrigaRegistrationForm
from users.models import AuditEvent, PrivacyConsent


def audit(actor, event, family=None, target='', detail=None):
    """Zadržava samo podatke potrebne za bezbednosni trag, bez zdravstvenog sadržaja."""
    AuditEvent.objects.create(
        actor=actor,
        family_id=family.id if family else None,
        event=event,
        target=str(target)[:160],
        detail=detail or {},
    )


def notify_family(family, sender, kind, title, body='', url='/'):
    recipients = family.memberships.exclude(user=sender).values_list('user_id', flat=True)
    alerts = Alert.objects.bulk_create([
        Alert(recipient_id=user_id, kind=kind, title=title, body=body, url=url) for user_id in recipients
    ])
    for alert in alerts:
        send_push_alert(alert)


def can_coordinate(membership):
    return membership and (
        membership.role == Membership.Role.ADMIN or
        (membership.role == Membership.Role.CAREGIVER and membership.access_level == Membership.AccessLevel.FULL)
    )


def can_view_health(membership):
    return membership and (
        membership.role in {Membership.Role.ADMIN, Membership.Role.SENIOR} or
        (membership.role == Membership.Role.CAREGIVER and membership.access_level in {
            Membership.AccessLevel.HEALTH, Membership.AccessLevel.FULL,
        })
    )


def can_support_family(membership):
    return membership and membership.role in {Membership.Role.ADMIN, Membership.Role.CAREGIVER}


def register(request):
    if request.method == 'POST':
        form = BrigaRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            family = Family.objects.create(name=f'Porodica {user.username}')
            Membership.objects.create(user=user, family=family, role=Membership.Role.ADMIN)
            PrivacyConsent.objects.create(user=user)
            audit(user, AuditEvent.Event.CONSENT, family, 'Registracija', {'policy_version': PrivacyConsent.POLICY_VERSION})
            login(request, user)
            return redirect('pocetna')
    else:
        form = BrigaRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


def accept_invite(request, token):
    invite = FamilyInvite.objects.select_related('family', 'created_by').filter(token=token).first()
    if not invite or not invite.available:
        return render(request, 'registration/invite_invalid.html', status=404)

    if request.user.is_authenticated:
        membership, created = Membership.objects.get_or_create(
            family=invite.family,
            user=request.user,
            defaults={'role': invite.role, 'access_level': invite.access_level},
        )
        if created:
            invite.accepted_at = timezone.now()
            invite.accepted_by = request.user
            invite.save(update_fields=['accepted_at', 'accepted_by'])
            messages.success(request, 'Uspešno ste se pridružili porodičnom krugu.')
        else:
            messages.info(request, 'Već ste deo ovog porodičnog kruga.')
        return redirect('pocetna')

    if request.method == 'POST':
        form = BrigaRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Membership.objects.create(family=invite.family, user=user, role=invite.role, access_level=invite.access_level)
            PrivacyConsent.objects.create(user=user)
            audit(user, AuditEvent.Event.CONSENT, invite.family, 'Pozivnica', {'policy_version': PrivacyConsent.POLICY_VERSION})
            invite.accepted_at = timezone.now()
            invite.accepted_by = user
            invite.save(update_fields=['accepted_at', 'accepted_by'])
            login(request, user)
            messages.success(request, 'Nalog je napravljen i sada ste u porodičnom krugu.')
            return redirect('pocetna')
    else:
        form = BrigaRegistrationForm()
    return render(request, 'registration/invite_register.html', {'form': form, 'invite': invite})


def service_worker(request):
    return render(request, 'service-worker.js', content_type='application/javascript')


def health(request):
    return JsonResponse({
        'status': 'ok',
        'application': 'Briga+',
        'version': '0.6.0',
        'durable_media_configured': bool(settings.BRIGA_DURABLE_MEDIA_CONFIGURED),
        'push_configured': bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY),
    })


def privacy_policy(request):
    return render(request, 'privacy_policy.html', {'policy_version': PrivacyConsent.POLICY_VERSION})


def terms(request):
    return render(request, 'terms.html')


@login_required
def account(request):
    consent = PrivacyConsent.objects.filter(user=request.user).first()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'accept_privacy':
            PrivacyConsent.objects.update_or_create(
                user=request.user,
                defaults={'policy_version': PrivacyConsent.POLICY_VERSION},
            )
            audit(request.user, AuditEvent.Event.CONSENT, target='Nalog', detail={'policy_version': PrivacyConsent.POLICY_VERSION})
            messages.success(request, 'Saglasnost je sačuvana.')
            return redirect('nalog')
        if action == 'delete_account':
            if request.POST.get('confirmation', '').strip().upper() != 'OBRIŠI':
                messages.error(request, 'Za brisanje upišite tačno: OBRIŠI.')
            else:
                username = request.user.username
                audit(request.user, AuditEvent.Event.ACCOUNT_DELETED, target=username)
                logout(request)
                User.objects.filter(username=username).delete()
                messages.success(request, 'Nalog i podaci vezani za nalog su poslati na brisanje.')
                return redirect('prijava')
    return render(request, 'account.html', {
        'consent': consent,
        'policy_version': PrivacyConsent.POLICY_VERSION,
        'push_subscriptions': request.user.push_subscriptions.count(),
    })


@staff_member_required(login_url='prijava')
def control_center(request):
    if request.method == 'POST' and request.POST.get('action') == 'platform_resolve_emergency':
        resolved = EmergencyAlert.objects.filter(
            pk=request.POST.get('emergency_id'), resolved_at__isnull=True,
        ).update(resolved_at=timezone.now())
        if resolved:
            audit(request.user, AuditEvent.Event.PLATFORM_EMERGENCY, target=f"SOS #{request.POST.get('emergency_id')}")
            messages.success(request, 'Hitni slučaj je označen kao rešen u platformskom centru.')

    now = timezone.now()
    active_emergencies = EmergencyAlert.objects.filter(resolved_at__isnull=True).select_related('family', 'raised_by')[:12]
    return render(request, 'control_center.html', {
        'summary': {
            'users': User.objects.count(),
            'families': Family.objects.count(),
            'memberships': Membership.objects.count(),
            'open_invites': FamilyInvite.objects.filter(accepted_at__isnull=True, expires_at__gt=now).count(),
            'active_sos': EmergencyAlert.objects.filter(resolved_at__isnull=True, kind=EmergencyAlert.Kind.SOS).count(),
            'push_devices': PushSubscription.objects.count(),
        },
        'active_emergencies': active_emergencies,
        'latest_invites': FamilyInvite.objects.select_related('family', 'created_by').all()[:8],
        'recent_families': Family.objects.order_by('-created_at')[:8],
    })


@login_required
def protected_media(request, path):
    reminder = Reminder.objects.filter(package_photo=path).select_related('user').first()
    voice = VoiceMessage.objects.filter(audio=path).select_related('family').first()
    document = CareDocument.objects.filter(document=path).select_related('user').first()
    if reminder:
        family_ids = request.user.family_memberships.values_list('family_id', flat=True)
        viewer_memberships = Membership.objects.filter(user=request.user, family_id__in=family_ids)
        allowed = reminder.user_id == request.user.id or any(can_view_health(item) for item in viewer_memberships)
    elif voice:
        allowed = voice.family.memberships.filter(user=request.user).exists()
    elif document:
        family_ids = request.user.family_memberships.values_list('family_id', flat=True)
        viewer_memberships = Membership.objects.filter(user=request.user, family_id__in=family_ids)
        allowed = document.user_id == request.user.id or any(can_view_health(item) for item in viewer_memberships)
    else:
        allowed = False
    if not allowed:
        raise Http404
    try:
        return FileResponse(default_storage.open(path, 'rb'), as_attachment=bool(document))
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
    if not membership and request.user.is_staff:
        return redirect('kontrola')
    family = membership.family if membership else None
    senior_membership = family.memberships.filter(role=Membership.Role.SENIOR).select_related('user').first() if family else None
    health_access = can_view_health(membership)
    care_user = senior_membership.user if senior_membership and health_access else request.user

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'checkin' and (membership.role == Membership.Role.SENIOR or care_user == request.user):
            note = request.POST.get('note', '').strip()[:240]
            period = request.POST.get('period', CheckIn.Period.ANY)
            if period not in CheckIn.Period.values:
                period = CheckIn.Period.ANY
            CheckIn.objects.create(user=request.user, note=note, period=period)
            if family:
                notify_family(family, request.user, Alert.Kind.CHECKIN, f'Potvrda: {request.user.username} je dobro', note)
        elif action == 'routine_done' and family:
            routine = DailyRoutine.objects.filter(pk=request.POST.get('routine_id'), user=care_user, active=True).first()
            if routine:
                RoutineCompletion.objects.get_or_create(routine=routine, completed_on=timezone.localdate(), defaults={'user': request.user})
        elif action == 'routine' and family and can_coordinate(membership):
            title = request.POST.get('title', '').strip()[:140]
            category = request.POST.get('category', DailyRoutine.Category.WELLBEING)
            part_of_day = request.POST.get('part_of_day', DailyRoutine.PartOfDay.DAY)
            if title and category in DailyRoutine.Category.values and part_of_day in DailyRoutine.PartOfDay.values:
                DailyRoutine.objects.create(user=care_user, title=title, category=category, part_of_day=part_of_day)
        elif action == 'routine_delete' and family and can_coordinate(membership):
            DailyRoutine.objects.filter(pk=request.POST.get('routine_id'), user=care_user).update(active=False)
        elif action == 'routine_defaults' and family and can_coordinate(membership):
            for title, category, part in [
                ('Popiti čašu vode', DailyRoutine.Category.WELLBEING, DailyRoutine.PartOfDay.MORNING),
                ('Pojesti redovan obrok', DailyRoutine.Category.WELLBEING, DailyRoutine.PartOfDay.DAY),
                ('Kratka šetnja ili razgibavanje', DailyRoutine.Category.MOVEMENT, DailyRoutine.PartOfDay.DAY),
            ]:
                DailyRoutine.objects.get_or_create(user=care_user, title=title, defaults={'category': category, 'part_of_day': part})
        elif action == 'mood' and family and (membership.role == Membership.Role.SENIOR or can_coordinate(membership)):
            mood = request.POST.get('mood')
            if mood in MoodEntry.Mood.values:
                MoodEntry.objects.update_or_create(
                    user=care_user, recorded_on=timezone.localdate(),
                    defaults={'mood': mood, 'note': request.POST.get('note', '').strip()[:240]},
                )
        elif action == 'care_profile' and family and can_coordinate(membership):
            profile, _ = CareProfile.objects.get_or_create(user=care_user)
            profile.allergies = request.POST.get('allergies', '').strip()[:500]
            profile.diagnoses = request.POST.get('diagnoses', '').strip()[:700]
            profile.doctor_name = request.POST.get('doctor_name', '').strip()[:120]
            profile.doctor_phone = request.POST.get('doctor_phone', '').strip()[:32]
            profile.health_card_number = request.POST.get('health_card_number', '').strip()[:80]
            profile.save()
        elif action == 'document' and family and can_coordinate(membership):
            uploaded = request.FILES.get('document')
            category = request.POST.get('category', CareDocument.Category.OTHER)
            allowed_types = {'application/pdf', 'image/jpeg', 'image/png', 'image/webp'}
            if uploaded and uploaded.size <= 10 * 1024 * 1024 and uploaded.content_type in allowed_types and category in CareDocument.Category.values:
                CareDocument.objects.create(user=care_user, uploaded_by=request.user, title=request.POST.get('title', '').strip()[:160] or uploaded.name[:160], category=category, document=uploaded)
            else:
                messages.error(request, 'Dokument mora biti PDF ili fotografija manja od 10 MB.')
        elif action == 'device' and family and can_coordinate(membership):
            kind = request.POST.get('device_type', CareDevice.DeviceType.BRACELET)
            if kind in CareDevice.DeviceType.values:
                CareDevice.objects.create(
                    user=care_user, name=request.POST.get('name', '').strip()[:80] or 'Briga+ uređaj',
                    serial_number=request.POST.get('serial_number', '').strip()[:80], device_type=kind,
                )
        elif action == 'visit' and family and can_coordinate(membership):
            try:
                scheduled_for = timezone.datetime.fromisoformat(request.POST.get('scheduled_for', ''))
                if timezone.is_naive(scheduled_for):
                    scheduled_for = timezone.make_aware(scheduled_for)
            except ValueError:
                scheduled_for = None
            visitor = family.memberships.filter(user_id=request.POST.get('visitor_id')).select_related('user').first()
            if visitor and scheduled_for:
                FamilyVisit.objects.create(family=family, visitor=visitor.user, scheduled_for=scheduled_for, note=request.POST.get('note', '').strip()[:300])
        elif action == 'visit_status' and family and can_coordinate(membership):
            status = request.POST.get('status')
            visit = family.visits.filter(pk=request.POST.get('visit_id')).first()
            if visit and status in FamilyVisit.Status.values and (visit.visitor_id == request.user.id or membership.role == Membership.Role.ADMIN):
                visit.status = status
                visit.save(update_fields=['status'])
        elif action == 'health_log' and family and (membership.role == Membership.Role.SENIOR or can_coordinate(membership)):
            kind = request.POST.get('kind')
            value = request.POST.get('value', '').strip()[:80]
            note = request.POST.get('note', '').strip()[:300]
            try:
                recorded_at = timezone.datetime.fromisoformat(request.POST.get('recorded_at', ''))
                if timezone.is_naive(recorded_at):
                    recorded_at = timezone.make_aware(recorded_at)
            except ValueError:
                recorded_at = timezone.now()
            if kind in HealthLog.Kind.values and (value or note):
                HealthLog.objects.create(user=care_user, kind=kind, value=value, note=note, recorded_at=recorded_at)
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
            assignee_id = request.POST.get('assignee_id')
            assigned = family.memberships.filter(user_id=assignee_id).select_related('user').first() if assignee_id else None
            if title:
                CareTask.objects.create(
                    family=family, title=title, assignee=assigned.user if assigned else None, due_at=due_at,
                    category=request.POST.get('category', 'other')[:16], notes=request.POST.get('notes', '').strip()[:300],
                )
        elif action == 'task_done' and family and can_coordinate(membership):
            family.tasks.filter(pk=request.POST.get('task_id')).update(done=True)
        elif action == 'task_claim' and family and can_coordinate(membership):
            family.tasks.filter(pk=request.POST.get('task_id'), assignee__isnull=True, done=False).update(assignee=request.user)
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
            emergency = EmergencyAlert.objects.create(
                family=family, raised_by=request.user, latitude=request.POST.get('latitude') or None,
                longitude=request.POST.get('longitude') or None, note=request.POST.get('note', '').strip()[:280], kind=EmergencyAlert.Kind.SOS,
            )
            audit(request.user, AuditEvent.Event.SOS_CREATED, family, f'SOS #{emergency.id}', {'has_location': bool(emergency.latitude)})
            notify_family(family, request.user, Alert.Kind.SOS, f'SOS: {request.user.username} traži pomoć', 'Otvorite Briga+ za GPS lokaciju i rutu.')
            messages.error(request, 'SOS je poslat članovima porodice.')
        elif action == 'help_request' and family:
            kind = request.POST.get('kind', EmergencyAlert.Kind.CALL)
            if kind in {EmergencyAlert.Kind.CALL, EmergencyAlert.Kind.UNWELL, EmergencyAlert.Kind.HELP}:
                EmergencyAlert.objects.create(
                    family=family, raised_by=request.user, kind=kind, note=request.POST.get('note', '').strip()[:280],
                )
                labels = {
                    EmergencyAlert.Kind.CALL: 'traži poziv', EmergencyAlert.Kind.UNWELL: 'ne oseća se dobro',
                    EmergencyAlert.Kind.HELP: 'traži pomoć',
                }
                notify_family(family, request.user, Alert.Kind.NEED_HELP, f'{request.user.username} {labels[kind]}', 'Otvorite Briga+ i javite se osobi.')
                messages.success(request, 'Porodica je obaveštena. Ovo nije aktiviralo SOS.')
        elif action == 'sos_acknowledge' and family and can_coordinate(membership):
            updated = family.emergencies.filter(pk=request.POST.get('sos_id'), resolved_at__isnull=True, acknowledged_at__isnull=True).update(
                acknowledged_at=timezone.now(), acknowledged_by=request.user,
            )
            if updated:
                audit(request.user, AuditEvent.Event.SOS_UPDATED, family, f"SOS #{request.POST.get('sos_id')}", {'state': 'acknowledged'})
        elif action == 'sos_en_route' and family and can_coordinate(membership):
            updated = family.emergencies.filter(pk=request.POST.get('sos_id'), resolved_at__isnull=True, responder_en_route_at__isnull=True).update(
                responder_en_route_at=timezone.now(), responder=request.user,
            )
            if updated:
                audit(request.user, AuditEvent.Event.SOS_UPDATED, family, f"SOS #{request.POST.get('sos_id')}", {'state': 'en_route'})
        elif action == 'sos_resolve' and family and can_coordinate(membership):
            updated = family.emergencies.filter(pk=request.POST.get('sos_id')).update(resolved_at=timezone.now())
            if updated:
                audit(request.user, AuditEvent.Event.SOS_UPDATED, family, f"SOS #{request.POST.get('sos_id')}", {'state': 'resolved'})
        elif action == 'invite_create' and family and membership.role == Membership.Role.ADMIN:
            role = request.POST.get('role')
            access_level = request.POST.get('access_level', Membership.AccessLevel.BASIC)
            if role not in {Membership.Role.CAREGIVER, Membership.Role.SENIOR}:
                messages.error(request, 'Pozivnica mora biti za člana porodice ili čuvano lice.')
            elif access_level not in Membership.AccessLevel.values:
                messages.error(request, 'Nivo pristupa nije ispravan.')
            else:
                if role == Membership.Role.SENIOR:
                    access_level = Membership.AccessLevel.BASIC
                invite = FamilyInvite.objects.create(
                    family=family, created_by=request.user,
                    recipient_label=request.POST.get('recipient_label', '').strip()[:120],
                    role=role, access_level=access_level,
                )
                audit(request.user, AuditEvent.Event.INVITE_CREATED, family, f'Pozivnica #{invite.id}', {'role': role, 'access': access_level})
                messages.success(request, 'Pozivnica je napravljena. Kopirajte bezbedan link iz kartice Porodica.')
        elif action == 'member_access' and family and membership.role == Membership.Role.ADMIN:
            target = family.memberships.filter(pk=request.POST.get('membership_id'), role=Membership.Role.CAREGIVER).first()
            access_level = request.POST.get('access_level')
            if target and access_level in Membership.AccessLevel.values:
                target.access_level = access_level
                target.save(update_fields=['access_level'])
                audit(request.user, AuditEvent.Event.ACCESS_CHANGED, family, target.user.username, {'access': access_level})
                messages.success(request, f'Pristup je ažuriran za {target.user.first_name or target.user.username}.')
        elif action == 'alert_read':
            request.user.alerts.filter(pk=request.POST.get('alert_id')).update(read_at=timezone.now())
        elif action == 'safety_settings' and family and membership.role == Membership.Role.ADMIN:
            senior = family.memberships.filter(role=Membership.Role.SENIOR).first()
            if senior:
                try:
                    due_time = timezone.datetime.strptime(request.POST.get('checkin_due_time', ''), '%H:%M').time()
                    gentle_minutes = min(max(int(request.POST.get('gentle_reminder_minutes', 30)), 5), 180)
                    alert_minutes = min(max(int(request.POST.get('alert_after_minutes', 120)), gentle_minutes + 5), 720)
                    senior.checkin_due_time = due_time
                    senior.gentle_reminder_minutes = gentle_minutes
                    senior.alert_after_minutes = alert_minutes
                    senior.save(update_fields=['checkin_due_time', 'gentle_reminder_minutes', 'alert_after_minutes'])
                except ValueError:
                    messages.error(request, 'Vreme i minuti za podsetnik nisu ispravni.')
        return redirect('pocetna')

    now = timezone.now()
    week_start, week_end = now - timedelta(days=7), now + timedelta(days=7)
    active_reminders = care_user.reminders.filter(completed_at__isnull=True)
    next_reminder = active_reminders.filter(scheduled_for__gte=now).first()
    overdue_reminders = active_reminders.filter(scheduled_for__lt=now)
    tasks = family.tasks.all()[:8] if family else []
    routines = list(care_user.daily_routines.filter(active=True))
    completed_routine_ids = set(RoutineCompletion.objects.filter(routine__user=care_user, completed_on=timezone.localdate()).values_list('routine_id', flat=True))
    for routine in routines:
        routine.completed_today = routine.id in completed_routine_ids
    safety_membership = family.memberships.filter(role=Membership.Role.SENIOR).first() if family else None
    care_profile = CareProfile.objects.filter(user=care_user).first()
    care_week = {
        'checkins': care_user.checkins.filter(created_at__gte=week_start).count(),
        'taken': care_user.reminders.filter(completed_at__gte=week_start).count(),
        'missed': care_user.reminders.filter(completed_at__isnull=True, scheduled_for__lt=now).count(),
        'upcoming': care_user.reminders.filter(completed_at__isnull=True, scheduled_for__range=(now, week_end)).count(),
        'open_tasks': family.tasks.filter(done=False).count() if family else 0,
        'overdue_tasks': family.tasks.filter(done=False, due_at__lt=now).count() if family else 0,
    }
    week_details = {
        'checkins': care_user.checkins.filter(created_at__gte=week_start)[:10],
        'taken': care_user.reminders.filter(completed_at__gte=week_start)[:10],
        'missed': care_user.reminders.filter(completed_at__isnull=True, scheduled_for__lt=now)[:10],
        'upcoming': care_user.reminders.filter(completed_at__isnull=True, scheduled_for__range=(now, week_end))[:10],
        'open_tasks': family.tasks.filter(done=False)[:10] if family else [],
        'overdue_tasks': family.tasks.filter(done=False, due_at__lt=now)[:10] if family else [],
    }
    family_invites = []
    if family and membership.role == Membership.Role.ADMIN:
        for invite in family.invites.filter(accepted_at__isnull=True, expires_at__gt=now)[:8]:
            invite.share_url = request.build_absolute_uri(invite.get_absolute_url())
            family_invites.append(invite)
    return render(request, 'dashboard.html', {
        'family': family, 'membership': membership, 'care_person': care_user,
        'last_checkin': care_user.checkins.first(), 'reminders': active_reminders[:8], 'next_reminder': next_reminder,
        'overdue_reminders': overdue_reminders[:4], 'tasks': tasks,
        'chat_messages': family.messages.select_related('sender').all()[:8] if family else [],
        'voice_messages': family.voice_messages.select_related('sender').all()[:8] if family else [],
        'sos_active': family.emergencies.filter(resolved_at__isnull=True, kind=EmergencyAlert.Kind.SOS).first() if family else None,
        'help_requests': family.emergencies.filter(resolved_at__isnull=True).exclude(kind=EmergencyAlert.Kind.SOS)[:4] if family else [],
        'members': family.memberships.select_related('user').all() if family else [],
        'contacts': family.emergency_contacts.all() if family else [],
        'alerts': request.user.alerts.filter(read_at__isnull=True)[:6], 'unread_alert_count': request.user.alerts.filter(read_at__isnull=True).count(), 'care_week': care_week, 'week_details': week_details,
        'routines': routines, 'routine_done_count': len(completed_routine_ids), 'health_logs': care_user.health_logs.all()[:8], 'safety_membership': safety_membership,
        'mood_today': MoodEntry.objects.filter(user=care_user, recorded_on=timezone.localdate()).first(), 'recent_moods': care_user.mood_entries.all()[:7],
        'care_profile': care_profile, 'documents': care_user.care_documents.all()[:8], 'devices': care_user.care_devices.all()[:5], 'visits': family.visits.select_related('visitor').filter(scheduled_for__gte=now - timedelta(days=1))[:8] if family else [],
        'push_public_key': settings.VAPID_PUBLIC_KEY,
        'has_health_access': health_access, 'can_manage_care': can_coordinate(membership),
        'is_family_panel': membership.role != Membership.Role.SENIOR,
        'family_invites': family_invites,
        'privacy_current': PrivacyConsent.objects.filter(user=request.user, policy_version=PrivacyConsent.POLICY_VERSION).exists(),
    })


@login_required
def senior_easy(request):
    membership = request.user.family_memberships.filter(role=Membership.Role.SENIOR).select_related('family').first()
    if not membership:
        return redirect('pocetna')
    now = timezone.now()
    routines = list(request.user.daily_routines.filter(active=True))
    completed = set(RoutineCompletion.objects.filter(routine__user=request.user, completed_on=timezone.localdate()).values_list('routine_id', flat=True))
    for routine in routines:
        routine.completed_today = routine.id in completed
    return render(request, 'senior_easy.html', {
        'family': membership.family, 'contacts': membership.family.emergency_contacts.all(), 'routines': routines,
        'next_reminder': request.user.reminders.filter(completed_at__isnull=True, scheduled_for__gte=now).first(),
        'mood_today': MoodEntry.objects.filter(user=request.user, recorded_on=timezone.localdate()).first(),
        'next_visit': membership.family.visits.select_related('visitor').filter(scheduled_for__gte=now).first(),
    })
