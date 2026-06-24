# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Záměr projektu

Firemní rezervační systém parkovacích míst pro zaměstnance. Uživatel si přes webové rozhraní rezervuje konkrétní parkovací místo na konkrétní den nebo směnu, maximálně měsíc dopředu.

**Stack**: FastAPI + Python, Jinja2 šablony, SQLAlchemy + Alembic, PostgreSQL.

## Autentizace

Dva oddělené způsoby přihlášení:

- **Zaměstnanci**: Microsoft Entra ID (Azure AD) OAuth 2.0 / OIDC. Po prvním přihlášení se uživatel uloží do `users` tabulky (azure_oid, email, display_name).
- **Lokální admin účet**: username + heslo uložené v `.env` (`ADMIN_USERNAME`, `ADMIN_PASSWORD_HASH`). Slouží jako záchranná síť nezávislá na SSO. Přihlašuje se přes `/auth/admin-login`.

Admin roli (`is_admin = True`) lze přidělit i SSO uživateli — pak může používat admin panel i přes SSO přihlášení.

Session uložena v podepsaném cookie (Starlette SessionMiddleware).

## Typy parkovacích míst

Parkoviště má do 30 míst, každé místo je identifikováno číslem a patrem (např. patro 1, místo 7). Dva typy:

- **Přidělené místo** — trvale přiřazeno konkrétnímu zaměstnanci adminem. Vlastník ho může:
  - Uvolnit na celý den → místo přejde do sdíleného poolu
  - Uvolnit na denní směnu nebo noční směnu (18:00–00:00) → půlden do poolu
  - Předat konkrétní osobě (ne do poolu, ale cíleně)
- **Sdílené místo** — volně dostupné, kdokoli si ho může rezervovat

## Rezervační model

- Granularita: celý den, denní směna, noční směna (18:00–00:00)
- Horizont: max. 1 měsíc dopředu
- Zaměstnanec rezervuje konkrétní místo (ne automatické přidělení)
- Přidělené místo, u něhož vlastník neudělá žádnou akci, zůstává blokované výhradně pro něj — neuvolní se automaticky
- Pokud vlastník uvolní slot do poolu a nikdo si ho nezabere, zůstane volný — místo se vlastníkovi automaticky nevrátí
- Vlastník může uvolnění vzít zpět (stornovat), dokud si slot nikdo jiný nezarezervoval

## UI — zaměstnanec

Týdenní kalendářový pohled:
- Vlastní rezervace zvýrazněné
- Ve dnech bez rezervace viditelná dostupnost sdílených míst (a uvolněných přidělených)
- Akce: rezervovat, zrušit, uvolnit přidělené místo, předat místo osobě

## Notifikace

- E-mail potvrzení při vytvoření rezervace
- E-mail připomenutí den před rezervací

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

**`users`**: id (UUID), azure_oid (unique, nullable pro lokálního admina), email, display_name, is_admin

**`spots`**: id (UUID), floor (patro, str, např. „1", „P1"), number (číslo místa), spot_type, assigned_user_id (FK users, nullable), active. Unique constraint na (floor, number).

**`releases`** — vlastník uvolňuje přidělené místo:
id (UUID), spot_id, date, shift, release_type, transfer_to_user_id (nullable), retracted_at (nullable)

**`reservations`** — rezervace místa:
id (UUID), spot_id, user_id, date, shift, cancelled_at (nullable)

Partial unique index na `reservations(spot_id, date, shift)` kde `cancelled_at IS NULL` — DB hlídá kolize.
FULL_DAY konflikt s DAY/NIGHT pro stejné (spot, date) řeší `availability` service před zápisem.

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
    │   ├── calendar.py      # GET / — týdenní pohled
    │   ├── reservations.py  # POST + DELETE /reservations (CSRF chráněné)
    │   ├── releases.py      # POST + DELETE /releases
    │   └── admin.py         # /admin — správa míst a uživatelů
    ├── services/
    │   ├── auth.py          # OAuth token exchange, session, lokální admin ověření
    │   ├── availability.py  # výpočet volných slotů pro daný týden/uživatele
    │   ├── booking.py       # create/cancel s kontrolou konfliktů
    │   └── email.py         # Azure Communication Services — potvrzení + připomenutí
    └── templates/
        ├── base.html
        ├── calendar.html
        └── admin/
            ├── spots.html
            └── users.html
```

