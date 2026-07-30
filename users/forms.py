from django import forms
from django.contrib.auth.forms import UserCreationForm


class BrigaRegistrationForm(UserCreationForm):
    privacy_consent = forms.BooleanField(
        required=True,
        label='Prihvatam Politiku privatnosti i Uslove korišćenja.',
        error_messages={'required': 'Potvrdite saglasnost da biste napravili nalog.'},
    )
