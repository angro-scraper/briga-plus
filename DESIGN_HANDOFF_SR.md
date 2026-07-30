# Briga+ — paket za dizajn

Ovo je postojeća funkcionalna Briga+ aplikacija. Potrebno je unaprediti vizuelni dizajn bez uklanjanja ili menjanja poslovne logike.

## Šta je najvažnije

- Postoje dva odvojena mobilna panela:
  - panel čuvanog lica u `templates/senior_dashboard.html`
  - porodični panel u `templates/dashboard.html`
- Čuvano lice mora uvek imati veliko SOS dugme na vrhu.
- Donja navigacija mora ostati potpuno klikabilna i ne sme prekrivati kartice.
- Otvoreni detalji na telefonu treba da koriste ceo ekran i da imaju jasno dugme „Nazad”.
- Veliki tekst, visok kontrast i veliki dodirni ciljevi su obavezni.
- Ne menjati Django modele, rute, forme, nazive `name` polja, CSRF zaštitu ili JavaScript funkcije za SOS, GPS, push i Sophie glas.

## Glavne datoteke za dizajn

- `templates/senior_dashboard.html`
- `templates/dashboard.html`
- `templates/senior_easy.html`
- `static/react-native-design.css`
- `static/directional-mobile-home.css`
- `static/senior-panel.css`
- `static/app.css`
- `static/briga-ui-icons.svg`

## Lokalno pokretanje

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver
```

Demo nalozi imaju lozinku `BrigaPlus2026!`:

- `demo` — administrator porodice
- `mama` — čuvano lice
- `ana` — član porodice

## Provera pre vraćanja paketa

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test users checkins families reminders caretasks emergencies messaging alerts
```

Uz vraćeni ZIP priložiti slike oba mobilna početna ekrana na širini od približno 390 px.
