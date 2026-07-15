# Build & Release Process

Postup pro vytvoření nové verze aplikace Parking a její nasazení do Azure.

## 1. Příprava kódu

### 1.1 Kontrola stavu repozitáře
```bash
git status
git log --oneline -5
```

### 1.2 Vytvoření feature branch (pro nové features)
```bash
git checkout -b feature/popis-zmeny
# nebo pro bugfixy:
git checkout -b fix/popis-bugfixu
```

## 2. Vývoj & Commity

### 2.1 Commit do gitu
**Pravidla:**
- Commit zprávy v češtině nebo angličtině (NE v cyrilici/azbuuce)
- Počátek s prefixem: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, etc.
- Včetně `Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>` na konci

**Příklad:**
```bash
git add app/services/email.py app/models/user.py
git commit -m "feat: add email notifications for guest parking

- Modified send_reservation_reminders() to include guest parkings
- Sends notifications to users about guest reservations for tomorrow

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

### 2.2 Bez commitu se nedělá build!
Jakmile máš změny hotové, commitni je do gitu. Build bez commitu není best practice.

## 3. Inkrementování verze

### 3.1 Určení typu verze
Postupuj podle [Semantic Versioning](https://semver.org/):
- **MAJOR** (v2.0.0): Breaking changes, zásadní přepracování
- **MINOR** (v1.9.0): Nové features, bez breaking changes
- **PATCH** (v1.8.2): Bugfixy a drobné vylepšení

**Současná verze:** viz `app/config.py` → `APP_VERSION`

### 3.2 Aktualizace verze v kódu

Otevři `app/config.py` a aktualizuj:
```python
# Stará verze:
APP_VERSION = f"v1.8.1+{GIT_COMMIT}"

# Nová verze (PATCH):
APP_VERSION = f"v1.8.2+{GIT_COMMIT}"
```

### 3.3 Commit pro verzi
```bash
git add app/config.py
git commit -m "bump version to v1.8.2

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

## 4. Build & Deploy do Azure

### 4.1 Build Docker image
```bash
docker build -t parking:latest .
```

### 4.2 Tag image pro Azure Container Registry
```bash
docker tag parking:latest parkingcr.azurecr.io/parking:latest
```

### 4.3 Login do ACR (pokud ještě nejsi přihlášen)
```bash
source .venv/bin/activate
az acr login --name parkingcr
```

### 4.4 Push image do Azure
```bash
docker push parkingcr.azurecr.io/parking:latest
```

**Kombinovaně (Build + Push):**
```bash
docker build -t parking:latest . && \
docker tag parking:latest parkingcr.azurecr.io/parking:latest && \
docker push parkingcr.azurecr.io/parking:latest
```

### 4.5 Automatický restart Container App
Container App se **automaticky restartuje** když detekuje nový image v registru (cca 1-2 minuty).

Pokud se to nestane, můžeš ručně restartovat v Azure Portal:
1. Jdi na Container App "parking" v resource groupu "Parking"
2. Klikni na "Revisions and replicas"
3. Klikni na poslední revizi a klikni "Restart" nebo "Deactivate → Activate"

## 5. Testování aplikace

### 5.1 Funkcionální testy (po deployi)

**Web UI test:**
- Otevři: https://parking.alintrust.cz
- Přihlášení funguje ✅
- Kalendář se načítá ✅
- Rezervace fungují ✅
- Guest parking funguje ✅

**Notifikace test:**
```bash
docker-compose exec -T app python3 << 'EOF'
import asyncio
from app.services import background_tasks

asyncio.run(background_tasks.send_reservation_reminders())
print("✅ Notifikace test hotov")
EOF
```

### 5.2 Database migrace test
```bash
docker-compose exec -T db psql -U parking -d parking -c \
"SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
```

### 5.3 Logy check
```bash
docker-compose logs app --tail 50 | grep -i "error\|warning\|startup"
```

## 6. Bezpečnostní testy

### 6.1 OWASP Top 10 checklist

- [ ] **SQL Injection** — DB queries používají parametrizované statements (SQLAlchemy ORM) ✅
- [ ] **Authentication** — Azure SSO + session middleware + CSRF token ✅
- [ ] **Sensitive Data Exposure** — HTTPS enforce, secrets v Key Vault, password hashing ✅
- [ ] **XML/XXE** — Nepoužíváme XML ✅
- [ ] **Broken Access Control** — Role-based access (admin, can_manage_guests, can_manage_spots, can_view_reports) ✅
- [ ] **Security Misconfiguration** — CSP headers, X-Frame-Options, X-Content-Type-Options ✅
- [ ] **XSS** — Jinja2 auto-escaping, HTML escaping v emailech (html.escape) ✅
- [ ] **Insecure Deserialization** — Nepoužíváme pickle, JSON only ✅
- [ ] **Using Components with Known Vulnerabilities** — Regular `pip check`, `pip audit` ✅
- [ ] **Insufficient Logging & Monitoring** — Logging v background_tasks, app.main, middleware ✅

### 6.2 Dependency check
```bash
pip audit
pip check
```

### 6.3 Secret scan (local, před commitem)
```bash
git log -p | grep -i "password\|secret\|token\|key" || echo "✅ Žádné sekrety v historii"
```

### 6.4 HTTPS & Headers check
```bash
curl -I https://parking.alintrust.cz | grep -i "strict-transport-security\|x-frame-options\|content-security-policy"
```

### 6.5 Database secrets check
- ✅ DATABASE_URL v Key Vault, ne v .env
- ✅ CONNECTION STRING s sslmode=require
- ✅ Azure AD managed identity pro auth (ne credentials v kódu)

## 7. Release Notes (volitelné)

Při release vytvoř soubor `RELEASE_NOTES_v1.8.2.md`:

```markdown
# Parking v1.8.2 Release Notes

## Features
- ✨ Reminder emails pro guest parkings
- ✨ Notifikace pro přidělená místa

## Bug Fixes
- 🐛 Fixed guest booking button visibility on days without reservations

## Security
- 🔒 Added flex-shrink:0 to action buttons (XSS prevention)
- 🔒 Email escaping for all user inputs

## Deployed
- 2026-07-15 v 15:30 UTC
- Container App: parking-ca
- Database: parking-pg (Azure PostgreSQL)
```

## 8. Checklist před pushnutím

- [ ] Všechny testy projdou lokálně (`docker-compose up`)
- [ ] Žádné `console.error` v browser dev tools
- [ ] Žádné Python exceptions v logu
- [ ] Verze je inkrementovaná v `app/config.py`
- [ ] Commit zpráva má smysl a je bez chyb
- [ ] Bez sekretu v kódu nebo Git historii
- [ ] HTTPS funguje na produkci
- [ ] Database migrace jsou aplikovány (pokud jsou)

## Příklad: Kompletní release flow

```bash
# 1. Feature branch
git checkout -b feature/new-notification

# 2. Vývoj & testing
# ... změny v kódu ...
docker-compose up

# 3. Commit
git add app/services/background_tasks.py
git commit -m "feat: add notification for admins

- New email template for admin alerts

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"

# 4. Verze
sed -i 's/v1.8.2/v1.8.3/g' app/config.py
git add app/config.py
git commit -m "bump version to v1.8.3

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"

# 5. Build & Deploy
docker build -t parking:latest . && \
docker tag parking:latest parkingcr.azurecr.io/parking:latest && \
source .venv/bin/activate && \
az acr login --name parkingcr && \
docker push parkingcr.azurecr.io/parking:latest

# 6. Merge do main (pokud jsi na feature branch)
git checkout main
git merge feature/new-notification

# 7. Verifikace
# Otevři https://parking.alintrust.cz a prověř UI
# Zkontroluj logy
```

## Troubleshooting

**Docker image se nepushuje:**
```bash
az acr login --name parkingcr
docker push parkingcr.azurecr.io/parking:latest
```

**Container App se nerestaruje:**
- Jdi do Azure Portal → Container App → Revisions
- Klikni "Restart" ručně

**Database migrace se neaplikují:**
```bash
docker-compose exec -T app alembic upgrade head
```

**Email se nepošle:**
- Zkontroluj Key Vault → ACS_CONNECTION_STRING
- Zkontroluj Azure Communication Services → Email settings
- Zkontroluj logy: `docker-compose logs app | grep -i email`

## Kontakt

Pro otázky nebo problémy otevři issue v GitHub nebo se kontaktuj na ondrej@remesovi.cz
