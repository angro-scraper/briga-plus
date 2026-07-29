from django.conf import settings
from django.db import models

class CheckIn(models.Model):
    class Period(models.TextChoices):
        ANY = 'any', 'Potvrda'
        MORNING = 'morning', 'Jutro'
        EVENING = 'evening', 'Veče'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='checkins')
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=240, blank=True)
    period = models.CharField(max_length=12, choices=Period.choices, default=Period.ANY)
    class Meta: ordering = ['-created_at']


class DailyRoutine(models.Model):
    class Category(models.TextChoices):
        MEDICINE = 'medicine', 'Lekovi'
        WELLBEING = 'wellbeing', 'Dobro stanje'
        MOVEMENT = 'movement', 'Kretanje'
        CONTACT = 'contact', 'Kontakt'
        OTHER = 'other', 'Drugo'
    class PartOfDay(models.TextChoices):
        MORNING = 'morning', 'Jutro'
        DAY = 'day', 'Tokom dana'
        EVENING = 'evening', 'Veče'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_routines')
    title = models.CharField(max_length=140)
    category = models.CharField(max_length=16, choices=Category.choices, default=Category.WELLBEING)
    part_of_day = models.CharField(max_length=16, choices=PartOfDay.choices, default=PartOfDay.DAY)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['part_of_day', 'title']


class RoutineCompletion(models.Model):
    routine = models.ForeignKey(DailyRoutine, on_delete=models.CASCADE, related_name='completions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='routine_completions')
    completed_on = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['routine', 'completed_on'], name='one_routine_completion_per_day')]


class HealthLog(models.Model):
    class Kind(models.TextChoices):
        PRESSURE = 'pressure', 'Krvni pritisak'
        GLUCOSE = 'glucose', 'Šećer u krvi'
        SYMPTOM = 'symptom', 'Simptom / kako se osećam'
        NOTE = 'note', 'Napomena'
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='health_logs')
    kind = models.CharField(max_length=16, choices=Kind.choices)
    value = models.CharField(max_length=80, blank=True)
    note = models.CharField(max_length=300, blank=True)
    recorded_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
