# Briga+ za Android i iOS

Ovo je nov, odvojen Capacitor projekat za pakete `rs.brigaplus.app`. Ne deli identitet sa postojećim aplikacijama u Play Console-u ili App Store Connect-u.

## Šta radi omot

Otvara isključivo HTTPS produkcioni panel Briga+. Web aplikacija ostaje izvor funkcionalnosti, dok omot kasnije dodaje prava uređaja: native push, lokalna obaveštenja, GPS, kameru, haptiku i bezbedne deep linkove.

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
3. Uključiti native push za Android (Firebase) i iOS (APNs), zatim povezati server sa oba provajdera. Web VAPID push nije zamena za native push u omotu.
4. Dodati jasne opise dozvola za lokaciju, mikrofon, kameru i obaveštenja; nikada ne tražiti pozadinsku lokaciju za trenutni SOS tok.
5. Testirati TestFlight i zatvoreni Play test sa stvarnim uređajima pre javne objave.

Ne objavljivati ovaj omot dok se ne završe stavke iz glavnog `README.md`: trajni privatni media bucket, produkcioni backup, VAPID/scheduler i pravni pregled politike privatnosti.
