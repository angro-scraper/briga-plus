# Briga+

Web aplikacija za porodice koje brinu o starijim članovima. Razvijena je kao Django web aplikacija, sa bazom koja kasnije može preći na PostgreSQL i istim URL-om za Android/iOS WebView omote.

## Pokretanje

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Zatim otvorite `http://127.0.0.1:8000/registracija/`. Registracijom se pravi lični nalog i početna porodična grupa.

Za gotov prikaz porodičnog panela pokrenite:

```powershell
.\.venv\Scripts\python.exe manage.py seed_demo
```

Demo prijava je `demo` / `BrigaPlus2026!`.

Pre objavljivanja kopirati `.env.example` u `.env`, upisati pravi tajni ključ i dozvoljeni domen. Lokalni razvoj ostaje na HTTP-u; produkcija sa `BRIGA_DEBUG=0` automatski zahteva HTTPS i bezbedne kolačiće.

## Trenutni MVP tokovi

- prijava i registracija;
- porodična grupa i uloge u bazi;
- dnevna potvrda „Dobro sam”;
- podsetnici, porodični zadaci i poruke u domen modelu;
- prikaz i unos zadataka, poruka i SOS signala;
- SOS traži GPS dozvolu u pregledniku i čuva dostupnu lokaciju uz alarm.

Pre slanja u produkciju potrebno je dodati e-mail/SMS/push provajdera, PostgreSQL, HTTPS, provere članstva za svaki API tok, testove dozvola i politiku privatnosti.

Za internu proveru dospelih podsetnika i izostalih dnevnih potvrda (kasnije se poziva periodično kroz Celery/cron):

```powershell
.\.venv\Scripts\python.exe manage.py create_due_alerts
```
