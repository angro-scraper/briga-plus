from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator


phone_validator = RegexValidator(
    regex=r'^[0-9+()\-\s]{6,32}$',
    message='Unesite ispravan broj telefona.',
)


class BrigaRegistrationForm(UserCreationForm):
    first_name = forms.CharField(label='Ime', max_length=150, required=True)
    last_name = forms.CharField(label='Prezime', max_length=150, required=True)
    email = forms.EmailField(label='E-mail adresa', required=True)
    phone = forms.CharField(label='Broj telefona', max_length=32, validators=[phone_validator], widget=forms.TextInput(attrs={'inputmode': 'tel', 'autocomplete': 'tel'}))
    address = forms.CharField(label='Adresa stanovanja', max_length=240, widget=forms.TextInput(attrs={'autocomplete': 'street-address'}))
    privacy_consent = forms.BooleanField(
        required=True,
        label='Prihvatam Politiku privatnosti i Uslove korišćenja.',
        error_messages={'required': 'Potvrdite saglasnost da biste napravili nalog.'},
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone', 'address', 'username')
        labels = {'username': 'Korisničko ime'}
        help_texts = {'username': 'Koristi se za prijavu i ne mora biti vaše puno ime.'}
        widgets = {
            'first_name': forms.TextInput(attrs={'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'autocomplete': 'family-name'}),
            'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
            'username': forms.TextInput(attrs={'autocomplete': 'username'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Nalog sa ovom e-mail adresom već postoji.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name'].strip()
        user.last_name = self.cleaned_data['last_name'].strip()
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
