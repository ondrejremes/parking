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
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── alembic.ini
├── alembic/versions/
└── app/
    ├── main.py              # FastAPI app, router registration, middleware
    ├── config.py            # os.getenv / dotenv
    ├── database.py          # SQLAlchemy engine + session
    ├── models/
    │   ├── user.py
    │   ├── spot.py
    │   ├── release.py
    │   └── reservation.py
    ├── routers/
    │   ├── auth.py          # /auth/login (SSO), /auth/callback, /auth/admin-login
    │   ├── calendar.py      # GET / — týdenní pohled
    │   ├── reservations.py  # POST + DELETE /reservations
    │   ├── releases.py      # POST + DELETE /releases
    │   └── admin.py         # /admin — správa míst a uživatelů
    ├── services/
    │   ├── auth.py          # OAuth token exchange, session, lokální admin ověření
    │   ├── availability.py  # výpočet volných slotů pro daný týden/uživatele
    │   ├── booking.py       # create/cancel s kontrolou konfliktů
    │   └── email.py         # potvrzení + připomenutí
    └── templates/
        ├── base.html
        ├── calendar.html
        └── admin/
            ├── spots.html
            └── users.html
```

