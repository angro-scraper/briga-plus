# Briga+ — redizajn 2026

Kompletan vizuelni redizajn je vraćen u aplikaciju 30.07.2026. Poslovna logika, Django rute, forme, CSRF zaštita, SOS/GPS, push i Sophie glas ostaju odvojeni od vizuelnog sloja.

## Šta je najvažnije

- Postoje dva odvojena mobilna panela:
  - panel čuvanog lica u `templates/senior_dashboard.html`
  - porodični panel u `templates/dashboard.html`
- Čuvano lice mora uvek imati veliko SOS dugme na vrhu.
- Donja navigacija mora ostati potpuno klikabilna i ne sme prekrivati kartice.
- Otvoreni detalji na telefonu treba da koriste ceo ekran i da imaju jasno dugme „Nazad”.
- Veliki tekst, visok kontrast i veliki dodirni ciljevi su obavezni.
- Ne menjati Django modele, rute, forme, nazive `name` polja, CSRF zaštitu ili JavaScript funkcije za SOS, GPS, push i Sophie glas.

## Glavne datoteke redizajna

- `templates/senior_dashboard.html`
- `templates/dashboard.html`
- `templates/senior_easy.html`
- `static/briga-v2.css`
- `static/briga-v2.js`
- `static/briga-ui-icons.svg`
- `templates/service-worker.js`
- `static/manifest.webmanifest`

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

## Provera pre objave

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
node --check static\briga-v2.js
```

Automatizovani test proverava i da svaka kartica sa `data-modal` ili `data-dialog` atributom vodi ka postojećem prozoru.
