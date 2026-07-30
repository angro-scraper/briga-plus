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
- SOS traži GPS dozvolu u pregledniku, čuva dostupnu lokaciju, prikazuje mapu i pokreće rutu do osobe;
- hitni kontakti sa pozivom jednim dodirom;
- nedeljni pregled potvrda, terapija, propuštenih stavki i rokova;
- terapije sa dozom, uputstvom, fotografijom pakovanja i dnevnim ponavljanjem;
- glasovne poruke u porodičnom chatu;
- režim za starije: veće komande i manje opcija;
- web-push pretplate i slanje za SOS, poruke, potvrde, terapije i propušten „Dobro sam”.

Pre rada sa stvarnim porodičnim podacima potrebno je povezati e-mail/SMS provajdera po izboru, produkcioni PostgreSQL sa backupom, HTTPS i trajno privatno skladište priloga. Politika privatnosti i Uslovi korišćenja sada postoje u aplikaciji, ali ih pre javnog puštanja mora pregledati pravnik i dopuniti punim podacima operatera.

## Push obaveštenja na Renderu

Web-push je ugrađen, ali se aktivira tek kada se u Render servisu `briga-plus` unesu sledeće promenljive okruženja. Privatni VAPID ključ nikada ne ide u GitHub.

```text
BRIGA_VAPID_PUBLIC_KEY=<application server key>
BRIGA_VAPID_PRIVATE_KEY=<privatni PEM ključ>
BRIGA_VAPID_SUBJECT=mailto:podrska@briga-plus.rs
```

Nakon ponovnog pokretanja, korisnik u prozoru „Obaveštenja” bira „Uključi obaveštenja na ovom uređaju”. SOS i poruke šalju push odmah; za dospele terapije i izostalu potvrdu potrebno je periodično pokretanje komande ispod, na primer Render Cron servisom na svakih 10 minuta.

Za internu proveru dospelih podsetnika i izostalih dnevnih potvrda:

```powershell
.\.venv\Scripts\python.exe manage.py create_due_alerts
```

Fotografije pakovanja, dokumenti i glasovne poruke su dostupni samo prijavljenim članovima iste porodice kroz zaštićeni URL aplikacije. Render disk je privremen: za produkciju postavite privatni S3/R2 bucket preko promenljivih `BRIGA_STORAGE_*` iz `.env.example`. Kada je bucket povezan, `/zdravlje/` vraća `durable_media_configured: true`.

## Render raspored i važan trošak

`render.yaml` sada definiše poseban cron servis `briga-plus-obavestenja` koji proverava terapije i „Dobro sam” na svakih pet minuta. Render cron nema besplatan plan i koristi `starter` plan; aktivirajte Blueprint tek kada odobrite taj mesečni trošak. Pre javne objave prebacite i PostgreSQL sa besplatnog plana na produkcioni plan sa backupom.

## Lista pre javne objave

1. U Renderu postaviti VAPID ključeve na web servisu i cron servisu, zatim testirati push na Androidu i iPhone-u.
2. Kreirati privatni R2/S3 bucket i uneti `BRIGA_STORAGE_*` promenljive.
3. Zameniti privremenu `podrska@briga-plus.rs` stvarnim kontaktom i dopuniti Politiku privatnosti poslovnim podacima posle pravnog pregleda.
4. Promeniti početnu lozinku vlasničkog naloga i uključiti višefaktorsku zaštitu na Render, GitHub, Apple i Google nalozima.
5. Proći zatvoreni pilot: pozivnica, nivo pristupa, SOS sa i bez GPS-a, terapija, odbijena dozvola, brisanje naloga i vraćanje iz backup-a.
