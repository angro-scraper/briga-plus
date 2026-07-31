# Briga+ za Android i iOS

Ovo je nov, odvojen Capacitor projekat za pakete `rs.brigaplus.app`. Ne deli identitet sa postojećim aplikacijama u Play Console-u ili App Store Connect-u.

## Šta radi omot

Otvara isključivo HTTPS produkcioni panel Briga+. Web aplikacija je jedini izvor interfejsa i poslovnih funkcija, pa Android, iOS i web prikazuju isti panel. Omot dodaje samo prava uređaja: native push, lokalna obaveštenja, GPS, kameru, haptiku i bezbedne deep linkove.

## Lokalno stvaranje platformi

```powershell
cd mobile
npm install
npx cap add android
npx cap add ios
npx cap sync
```

Android se zatim otvara kroz Android Studio (`npm run android`). iOS se potpisuje i šalje kroz Xcode na macOS-u (`npm run ios`). Windows ne može napraviti ili poslati iOS build.

## Pre prvog store build-a

1. U Play Console-u napraviti novu aplikaciju Briga+ sa novim package name-om `rs.brigaplus.app`.
2. U App Store Connect-u napraviti novu aplikaciju Briga+ i novi Bundle ID `rs.brigaplus.app`.
3. Uključiti native push za Android (Firebase) i iOS (APNs), zatim uneti odgovarajuće `BRIGA_FIREBASE_*` i `BRIGA_APNS_*` tajne u Render. Serverska isporuka za oba provajdera je implementirana; web VAPID push ostaje zaseban kanal za preglednik.
4. Dodati jasne opise dozvola za lokaciju, mikrofon, kameru i obaveštenja; nikada ne tražiti pozadinsku lokaciju za trenutni SOS tok.
5. Testirati TestFlight i zatvoreni Play test sa stvarnim uređajima pre javne objave.

## Pametni pozivni linkovi

Pozivnica ostaje jedan bezbedan HTTPS link (`https://briga-plus.onrender.com/poziv/...`). Kada je aplikacija instalirana, Android/iPhone je otvara direktno; bez aplikacije vodi na web registraciju.

Pre sledećeg Android/iOS build-a u Render dodati:

1. `BRIGA_ANDROID_APP_LINK_SHA256` — SHA-256 otisak sertifikata kojim je potpisan Play build. Više otisaka se razdvajaju zarezom.
2. `BRIGA_APPLE_APP_ID` — `AppleTeamID.rs.brigaplus.app`, iz Apple Developer naloga.

Nakon toga ponovo napraviti Android i iOS build, jer oba omota sadrže konfiguraciju za potvrđeni domen. Bez ova dva podatka server namerno ne objavljuje verifikacione fajlove i pozivnica ostaje web link.

Ne objavljivati ovaj omot dok se ne završe stavke iz glavnog `README.md`: trajni privatni media bucket, produkcioni backup, VAPID/scheduler i pravni pregled politike privatnosti.
