# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Záměr projektu

Firemní rezervační systém parkovacích míst pro zaměstnance. Uživatel si přes webové rozhraní rezervuje konkrétní parkovací místo na konkrétní den nebo směnu, maximálně měsíc dopředu.

**Stack**: FastAPI + Python, Jinja2 šablony, SQLAlchemy + Alembic, PostgreSQL.

## Autentizace

Tři způsoby přihlášení:

- **Zaměstnanci**: Microsoft Entra ID (Azure AD) OAuth 2.0 / OIDC (tenant: `d15176d7-e40c-4cae-bff5-11d57e820fbd`). Po prvním přihlášení se uživatel uloží do `users` tabulky (azure_oid, email, display_name).
- **Lokální admin účet**: username + heslo uložené v Key Vault (`ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH`). Slouží jako záchranná síť nezávislá na SSO. Přihlašuje se přes `/auth/admin-login`.
- **Lokální SOC účet**: Speciální uživatel (`is_admin=False`) pro správu parkovacích míst. Přihlášení přes admin login s SOC username.

Admin roli (`is_admin = True`) lze přidělit i SSO uživateli — pak může používat admin panel i přes SSO přihlášení.

Session uložena v podepsaném cookie (Starlette SessionMiddleware) s CSRF tokenem na všech POST akcích.

## Typy parkovacích míst

Parkoviště má do 30 míst, každé místo je identifikováno číslem a patrem (např. patro 1, místo 7). Dva typy:

- **Přidělené místo** — trvale přiřazeno konkrétnímu zaměstnanci adminem. Vlastník ho může:
  - Uvolnit na celý den → místo přejde do sdíleného poolu
  - Uvolnit na denní směnu nebo noční směnu (18:00–00:00) → půlden do poolu
  - Předat konkrétní osobě (ne do poolu, ale cíleně)
- **Sdílené místo** — volně dostupné, kdokoli si ho může rezervovat

## Rezervační model

- Granularita: celý den, denní směna (06:00-18:00), noční směna (18:00-08:00)
- Horizont: max. 1 měsíc dopředu
- Zaměstnanec rezervuje konkrétní místo (ne automatické přidělení)
- Přidělené místo, u něhož vlastník neudělá žádnou akci, zůstává blokované výhradně pro něj — neuvolní se automaticky
- **Na víkendech (sobota, neděle)**: Přidělená místa se automaticky uvolňují, vlastník je nemusí manuálně uvolňovat
- Pokud vlastník uvolní slot do poolu a nikdo si ho nezabere, zůstane volný — místo se vlastníkovi automaticky nevrátí
- Vlastník může uvolnění vzít zpět (stornovat), dokud si slot nikdo jiný nezarezervoval
- Konflikt kontrola: DAY + NIGHT = FULL_DAY (overlap detection v `_shifts_conflict()`)

## UI — zaměstnanec

**Týdenní kalendářový pohled** (responsive na všechny velikosti obrazovky):
- Vlastní rezervace zvýrazněné
- Ve dnech bez rezervace viditelná dostupnost sdílených míst (a uvolněných přidělených)
- Počet volných míst s možností rezervace
- Akce: rezervovat, zrušit, uvolnit přidělené místo, předat místo osobě, vytvořit guest parking

**Měsíční kalendářový pohled**:
- Přehled všech dní v měsíci
- Počet volných slotů per shift (Den vs. Noc)
- Detail/zoom do konkrétního dne pro rezervaci

**Responsive design**:
- Widescreen optimization (1920px+): Plný layout s tabulkovým zobrazením
- Tablet (768px-1920px): Vyvážený layout s adaptabilní šířkou
- Mobile (< 768px): Single-column layout, vertikální scroll

## Notifikace

**E-mailové notifikace** (přes Azure Communication Services):

- **Potvrzení rezervace** — při vytvoření rezervace s detaily místa a času
- **Zrušení rezervace** — notifikace při zrušení rezervace  
- **Připomenutí den před** — posílá se v **19:00 CEST** (18:00 UTC) s:
  - Detaily parkovacího místa
  - Instrukcemi k zrušení rezervace
  - Dual action tlačítky: ❌ Zrušit + 🔗 Přejít na kalendář
- **Notifikace hostů** — cuando se vytvoří/zruší guest parking, notifikace se posílá:
  - Sponzorovi (tvůrci rezervace)
  - Kontaktní osobě (pokud je vybrána)

**Email sender**: `DoNotReply@alintrust.cz` (z Key Vault secret `email-from`)
**Timezone**: Aplikace pracuje s UTC, cron job reminder je na `0 18 * * *` (18:00 UTC = 19:00 CEST v létě, 20:00 CEST v zimě)

## Admin

- Přiděluje/odebírá přidělená místa zaměstnancům
- Spravuje seznam míst a uživatelů
- Může udělit `is_admin` SSO uživateli

## Nasazení — Azure architektura

```
Internet
  └─→ Azure Front Door (WAF + OWASP CRS 3.2, DDoS, SSL offload, HTTPS enforce)
        └─→ Azure Container Apps  (FastAPI, privátní ingress)
              ├─→ Azure Container Registry  (Docker image)
              ├─→ Azure Database for PostgreSQL Flexible Server  (private endpoint)
              ├─→ Azure Key Vault  (secrets přes managed identity)
              └─→ Azure Communication Services  (email)
```

PostgreSQL nemá public endpoint — dostupný pouze z VNet Container Apps prostředí.
Secrets (DB connection string, OAuth client secret, session key) jsou v Key Vault; aplikace je čte přes managed identity bez jakýchkoli credentials v kódu nebo env.

IaC: **Bicep** (`infra/` složka).

**Azure Communication Services (ACS)** - Email:
- Dvě ACS instance: "Parking" (pro aplikaci) + "Parking-email" (pro domain konfiguraci)
- Domain: `alintrust.cz` (Verified, SPF/DKIM konfigurováno)
- Email sender: `DoNotReply@alintrust.cz` (z ACS MailFrom addresses)
- Connection string uložen v Key Vault, aplikace čte přes Managed Identity
- Reminder job: Stejná ACS instance, cron `0 18 * * *` pro denní připomenutí v 19:00 CEST

### Bezpečnost po vrstvách

| Vrstva | Opatření |
|---|---|
| WAF | OWASP CRS 3.2 managed ruleset + rate limiting na Azure Front Door |
| Síť | Container Apps v VNet, PostgreSQL pouze přes private endpoint |
| Auth | Entra ID OAuth s PKCE, session v podepsaném cookie + CSRF token na všech POST |
| Secrets | Azure Key Vault + managed identity — žádná hesla v env nebo kódu |
| HTTPS | Front Door vynucuje redirect, HSTS header v odpovědích |
| HTTP headers | CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy v FastAPI middleware |
| DB | SQLAlchemy ORM — parametrizované dotazy všude, žádné raw SQL |
| Container | non-root user, `python:3.12-slim` base image |

## Datový model

Enums: `SpotType` (ASSIGNED/SHARED), `Shift` (FULL_DAY/DAY/NIGHT), `ReleaseType` (POOL/TRANSFER)

**`users`**: id (UUID), azure_oid (unique, nullable pro lokálního admina), email, display_name, is_admin, active, can_manage_guests, can_manage_spots, can_view_reports

**`spots`**: id (UUID), floor (patro, str, např. „1", „P1"), number (číslo místa), spot_type, assigned_user_id (FK users, nullable), active. Unique constraint na (floor, number).

**`releases`** — vlastník uvolňuje přidělené místo:
id (UUID), spot_id, date, shift, release_type, transfer_to_user_id (nullable), retracted_at (nullable)

**`reservations`** — rezervace místa:
id (UUID), spot_id, user_id, date, shift, cancelled_at (nullable)

**`guest_parkings`** — rezervace pro hosty (sponzor si zarezervuje pro svého hosta):
id (UUID), spot_id, created_by_user_id, contact_user_id (nullable), date, time_from, time_to, guest_name, guest_plate, guest_company, note, cancelled_at (nullable)

Partial unique index na `reservations(spot_id, date, shift)` kde `cancelled_at IS NULL` — DB hlídá kolize.
FULL_DAY konflikt s DAY/NIGHT pro stejné (spot, date) řeší `availability` service před zápisem.
Guest parking time ranges se kontrolují v `_guest_blocks_shift()` — time-based overlap detection.

## Struktura aplikace

```
parking/
├── infra/                   # Bicep IaC
│   ├── main.bicep           # entry point — orchestruje moduly
│   ├── modules/
│   │   ├── containerapp.bicep
│   │   ├── frontdoor.bicep
│   │   ├── postgres.bicep
│   │   ├── keyvault.bicep
│   │   └── network.bicep
│   └── parameters/
│       └── prod.bicepparam
├── docker-compose.yml       # lokální vývoj (app + postgres)
├── Dockerfile
├── requirements.txt
├── .env.example
├── alembic.ini
├── alembic/versions/
└── app/
    ├── main.py              # FastAPI app, router registration, security middleware
    ├── config.py            # Settings přes os.getenv / dotenv
    ├── database.py          # SQLAlchemy engine + session
    ├── middleware.py        # CSP, HSTS, X-Frame-Options, CSRF hlavičky
    ├── models/
    │   ├── user.py
    │   ├── spot.py
    │   ├── release.py
    │   └── reservation.py
    ├── routers/
    │   ├── auth.py          # /auth/login (SSO + PKCE), /auth/callback, /auth/admin-login
    │   ├── calendar.py      # GET / — týdenní + měsíční pohled, kalendář
    │   ├── reservations.py  # POST + DELETE /reservations (CSRF chráněné, s email notifikacemi)
    │   ├── releases.py      # POST + DELETE /releases (uvolňování přidělených míst)
    │   ├── guest_parkings.py # POST + DELETE /guest-parkings (rezervace pro hosty)
    │   └── admin.py         # /admin — správa míst, uživatelů, guest parkings
    ├── services/
    │   ├── auth.py          # OAuth token exchange, session, lokální admin ověření
    │   ├── availability.py  # výpočet volných slotů, weekend handling, shift conflicts
    │   ├── booking.py       # create/cancel s kontrolou konfliktů
    │   ├── email_notifications.py # Azure Communication Services — potvrzení, zrušení, připomenutí, guest notifikace
    │   └── (jobs/)
    │       └── reminder.py  # Background cron job pro denní připomenutí (19:00 CEST)
    └── templates/
        ├── base.html
        ├── calendar.html
        └── admin/
            ├── spots.html
            └── users.html
```

