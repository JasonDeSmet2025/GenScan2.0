# Automatische WordPress-setup (frontend)

Dit mapje zet met **één commando** een werkende, gestructureerde WordPress-site
op op deze pc — lokaal, via Docker. Je hoeft niets handmatig in te typen en je
kunt het na elke `git pull` opnieuw uitvoeren.

```
wordpress/
├── docker-compose.yml      # de stack: MySQL + WordPress + phpMyAdmin
├── .env.example            # voorbeeld-configuratie (→ kopieer naar .env)
├── .env                    # jouw configuratie (niet naar git gestuurd)
├── .gitignore              # houdt .env buiten de repo
├── site.json               # ★ HET ONTWERPBESTAND: hoe de site eruitziet
├── setup_wordpress.py      # het script dat alles doet (standaard-Python)
└── run.bat                 # handige Windows-wrapper voor het script
```

---

## Snel beginnen

**Voorwaarde:** Docker Desktop is geïnstalleerd en draait.

```powershell
cd wordpress
py setup_wordpress.py
```

(Alleen `run.bat` dubbelklikken doet hetzelfde. Op een machine waar `python`
gebruikt wordt in plaats van `py`, gebruik dan `python setup_wordpress.py`.)

Het script doet, in deze volgorde:

1. Maak `.env` aan vanuit `.env.example` (als die nog ontbreekt).
2. Start de Docker-stack (MySQL + WordPress + phpMyAdmin).
3. Wacht tot WordPress en de database bereikbaar zijn.
4. Installeert WordPress (alleen nog niet geïnstalleerd).
5. Past **alles** uit `site.json` toe: naam, taal, thema, plugins,
   gebruikers, pagina's en menu's.

Het script is **idempotent**: je kunt het gerust opnieuw uitvoeren. Wat al
bestaat, slaat het over.

### Resultaat (standaard)

| Wat            | Waar                                            |
|----------------|-------------------------------------------------|
| Website        | http://localhost:8080                           |
| Beheer (admin) | http://localhost:8080/wp-admin                  |
| Database (UI)  | http://localhost:8081 (phpMyAdmin)              |
| Inlog          | `admin` — wachtwoord staat in `.env`            |

---

## Stappen (in detail)

### 1. Pas de configuratie aan (`.env`)

Bij de eerste start kopieert het script `.env.example` automatisch naar `.env`.
Open `.env` en verander minstens de wachtwoorden:

```ini
DB_PASSWORD=GenScan_WP_2026_change_me
DB_ROOT_PASSWORD=GenScan_WP_root_2026_change_me
WP_ADMIN_PASSWORD=GenScan_Admin_2026_change_me
```

Wil je de site op een **domein** (FQDN) in plaats van `localhost`?
Zet `WP_SITE_URL` op dat adres en werk het domein op naar die naam,
bv. `WP_SITE_URL=http://genstack.local`.

> `.env` staat in `.gitignore` en wordt daarom **niet** naar GitHub gestuurd.

### 2. Start de setup

```powershell
py setup_wordpress.py
```

Het eerste keer duurt het even langer: Docker downloadt de
WordPress-, MySQL- en phpMyAdmin-beelden. Daarna is het snel.

### 3. Inloggen

Ga naar <http://localhost:8080/wp-admin> en log in met het admin-gebruiker
uit `.env`. Extra gebruikers (bv. `redactie`) legt het script aan op basis van
`site.json`; hun wachtwoorden worden tijdens de run in het scherm getoond —
kopieer die bij het eerste aanmaken.

---

## Het ontwerpbestand `site.json`

`site.json` beschrijft **hoe de website eruit moet zien en gestructureerd
moet zijn**. Pas het aan naar jouw wensen en herstart de setup.
Onbekende velden worden genegeerd; ontbrekende velden worden overgeslagen.

### `site` — algemene instellingen

| Veld             | Omschrijving                                   | Voorbeeld          |
|------------------|------------------------------------------------|--------------------|
| `title`          | Naam van de website (site-titel)               | `"GenScan — Overlijdensberichten"` |
| `tagline`        | Omschrijving/leuze tekst onder de titel        | `"Digitale archivering …"` |
| `language`       | Taalcode (downloadt de taalpakket)             | `"nl_NL"`          |
| `timezone`       | Tijdzone (IANA-naam)                           | `"Europe/Brussels"`|
| `date_format`    | Datumnotatie                                   | `"d/m/Y"`          |
| `time_format`    | Tijdnotatie                                    | `"H:i"`            |
| `start_of_week`  | Startdag van de week (0 = zondag, 1 = maandag) | `1`                |
| `posts_per_page` | Aantal berichten per pagina                    | `10`               |

### `permalinks` — URL-structuur

| Veld        | Omschrijving                                   | Voorbeeld         |
|-------------|------------------------------------------------|-------------------|
| `structure` | Permanente-link structuur                      | `"/%postname%/"`  |

### Thema

| Veld                | Omschrijving                                        |
|---------------------|-----------------------------------------------------|
| `theme`             | Naam (slug) van het in te zetten thema. Wordt geïnstalleerd als het nog niet staat, en geactiveerd. Voorbeeld: `"twentytwentythree"`. |
| `themes_to_remove`  | Lijst met thema-slugs die verwijderd moeten worden (alleen als ze geïnstalleerd zijn). |
| `theme_mods`        | Sleutel/waardeparen voor uiterlijk-instellingen via `theme_mod`. Lijsten/voorwaarden gaan als JSON. Voorbeeld: `{ "site_tagline": "…" }`. |

### Plugins

```json
"plugins": [
  { "slug": "wpvivid", "name": "WPvivid Backup & Migration", "activate": true },
  { "slug": "wordpress-seo", "name": "Yoast SEO", "activate": true }
]
```

- `slug` — naam van de plugin op de WordPress.org-ruilmarkt (verplicht).
- `name` — optioneel, alleen voor leesbaarheid.
- `activate` — `true`/`false` (standaard `true`).

`plugins_to_remove` — lijst met plugin-slugs om te verwijderen
(bv. `["akismet", "hello-dolly"]`).

### Gebruikers

```json
"users": [
  {
    "username": "redactie",
    "email": "redactie@fvbrugge.be",
    "role": "editor",
    "first_name": "GenScan",
    "last_name": "Redactie"
  }
]
```

- `username`, `email` — verplicht.
- `role` — `administrator`, `editor`, `author`, `contributor` of `subscriber` (standaard `subscriber`).
- `first_name` / `last_name` — optioneel.
- Het wachtwoord wordt automatisch gegenereerd en **een keer** op het scherm
  getoond bij het aanmaken.

### Pagina's en berichten

```json
"pages": [
  { "title": "Over ons", "slug": "over-ons", "status": "publish",
    "content": "…HTML-content…", "parent": "home" }
]
```

- `title`, `slug` — `slug` is de URL-deel (optioneel; anders afgeleid van de titel).
- `status` — `publish`, `draft`, `pending`, … (standaard `publish`).
- `content` — HTML-tekst van de pagina.
- `parent` — slug van de bovenliggende pagina (voor subs).
- `posts` werkt exact hetzelfde als `pages`, maar voor blogberichten.

### Menu's

```json
"menus": [
  { "name": "Hoofdnavigatie", "location": "primary",
    "items": ["home", "over-ons", "zoeken", "contact"] }
]
```

- `name` — naam van het menu.
- `location` — plaats in het thema (bv. `primary`, `footer`); afhangend van het thema.
- `items` — slugs van pagina's/berichten in volgorde.

### Import (optioneel)

```json
"import": { "xml_files": ["import/oude-site.xml"] }
```

Paden zijn relatief ten opzichte van dit mapje. Wordt geïmporteerd met
WordPress' ingebouwde importer (auteurs worden aangelegt).

---

## Handige commando's

```powershell
docker compose logs -f wordpress    # live logs van de site
docker compose ps                   # status van de containers
docker compose down                 # alles stoppen (data blijft in volumes)
docker compose down -v              # stoppen EN alle data definitief wissen
```

De data zit in twee Docker-volumes (`genstack_db_data`, `genstack_wp_data`).
Die blijven bewaard zolang je `-v` niet gebruikt.

---

## Foutopsporing

| Symptoom                                    | Oorzaak / oplossing                                                            |
|---------------------------------------------|--------------------------------------------------------------------------------|
| `Docker is niet draaiend`                   | Start Docker Desktop; controleer of de containers draaien (`docker compose ps`). |
| `Docker-stack was niet tijdig bereikbaar`   | `docker compose logs db` en `docker compose logs wordpress` bekijken.           |
| Site opent niet                             | Poortbezet? Pas `WP_HTTP_PORT` aan in `.env` en herstart.                       |
| `site.json is geen geldig JSON`             | Komma's/haakjes controleren; bij twijfel de JSON online valideren.              |
| Wachtwoord van extra gebruiker vergeten     | De gebruiker verwijderen (`user delete`) in phpMyAdmin of WP, en opnieuw draaien. |

---

## Verwijzen

- Dit is een **lokale** ontwikkel/voorbeeldomgeving op deze pc.
- Voor een **productieve** website op een server (met SSL, FQDN, back-ups)
  is dezelfde stack bruikbaar, maar dan op een server geplaatst en met echte
  wachtwoorden en domeinen.
