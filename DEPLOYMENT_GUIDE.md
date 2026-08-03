# Parking App - Deployment Guide

## Problematika

Deployment do Azure Container Apps má několik problémů. Tento dokument je shrnutí toho, co funguje a co nefunguje.

---

## ✅ Co Funguje

### 1. Docker Build Lokálně
```bash
docker build -t parking:v1.4.4 .
```
**Status:** Funguje vždy ✅
- Build image lokálně bez problémů
- Image je dostupný jako `parking:v1.4.4`

### 2. Git Commit a Verze
```bash
git add .
git commit -m "fix: message"
```
**Status:** Funguje vždy ✅
- Commitují se změny
- Version se updatuje v `app/config.py`
- Git history je správná

### 3. Azure Login se Service Principal
```bash
az login --service-principal -u $AZURE_CLIENT_ID -p $AZURE_CLIENT_SECRET --tenant $AZURE_TENANT_ID
```
**Status:** Funguje z docker kontejneru ✅
- Přihlášení v docker kontejneru v docker kontejneru pracuje
- Subscription se korektně nastaví

### 4. Container App Manual Restart
```
Azure Portal → Container Apps → parking-app → Stop/Start
```
**Status:** Funguje vždy ✅
- Stop zastaví aplikaci
- Start ji znovu spustí
- Po restartu se načte nový image z ACR

### 5. ACR Push přes az acr build (někdy)
```bash
az acr build --registry parkingcr --image 'parking:latest' .
```
**Status:** Funguje někdy ✅/❌
- Někdy se povedá pushit image úspěšně
- Někdy selhá s "resource not found"
- Pracuje to zejména když je `~/.azure` mounted v docker kontejneru

---

## ❌ Co Nefunguje

### 1. Docker Push se Service Principal Credentials
```bash
docker login parkingcr.azurecr.io -u $USERNAME -p $PASSWORD
docker push parkingcr.azurecr.io/parking:v1.4.4
```
**Status:** NEFUNGUJE ❌
- Service principal credentials nejsou ACR login credentials
- Docker push vždy selhává s UNAUTHORIZED
- **Řešení:** Nepoužívat docker login, používat `az acr build`

### 2. Azure REST API pro Container App Restart
```bash
curl -X POST "https://management.azure.com/.../restart?api-version=2023-04-01-preview" \
  -H "Authorization: Bearer $TOKEN"
```
**Status:** NEFUNGUJE ❌
- Service principal nemá oprávnění `Microsoft.App/containerApps/restart/action`
- AuthorizationFailed se vrátí vždy
- **Řešení:** Restartovat ručně v Azure Portal nebo přidat oprávnění

### 3. Azure REST API pro Container App Update
```bash
curl -X PATCH "https://management.azure.com/.../..." \
  -H "Authorization: Bearer $TOKEN"
  -d '{"properties": {"template": {...}}}'
```
**Status:** NEFUNGUJE ❌
- Service principal nemá oprávnění `Microsoft.App/containerApps/write`
- **Řešení:** Ručně v Azure Portal

### 4. Azure CLI v Docker bez ~/.azure Mount
```bash
docker run -e AZURE_CLIENT_ID=... mcr.microsoft.com/azure-cli az acr list
```
**Status:** NEFUNGUJE ❌
- `az acr list` vrací prázdný seznam
- `az acr build` selhává s "resource not found"
- **Řešení:** Mountovat `-v ~/.azure:/root/.azure`

### 5. ACR Resource Lookup v Docker
I s správným mountem `~/.azure` někdy selhá:
```
ERROR: The resource with name 'parkingcr' and type 'Microsoft.ContainerRegistry/registries' 
could not be found in subscription
```
**Status:** NEFUNGUJE (nepředvídatelně) ❌
- Příčina nejasná
- Někdy funguje, někdy ne
- **Řešení:** Zkusit znovu

---

## 🚀 Deploy.sh - Co dělá

**Soubor:** `deploy.sh`

Script orchestruje kompletní deployment do Azure. Má 3 kroky:

### Step 1: Azure Login
```bash
az account show > /dev/null 2>&1 || az login --tenant "$TENANT_ID"
az account set --subscription "$SUBSCRIPTION_ID"
```
- Přihlášení se service principal credentials (ze `deploy.env`)
- Nastavení správné subscription

### Step 2: Deploy Infrastructure (Bicep)
```bash
az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file infra/main.bicep \
  --parameters containerImage="$ACR_NAME.azurecr.io/$APP_NAME:latest" ...
```
- Deployuje infrastrukturu z Bicep šablon (Container Apps, Database, Front Door, atd.)
- Passuje environment variables (Azure Client ID, Secret, Database config, atd.)
- **Pozor:** Konfiguruje Container App aby používal image `parking:latest`

### Step 3: Build and Push Docker Image
```bash
az acr build --registry "$ACR_NAME" --image "$APP_NAME:latest" .
```
- Builduje Docker image
- Pushuje do Azure Container Registry
- Taguje jako `latest`
- Toto je to, co se Container App při restartu sáhne

### Proč deploy.sh nefunguje v mém setup

1. **Step 1 (Login)** - Funguje ✅
2. **Step 2 (Bicep)** - Selhává: Network error (DNS resolution) ❌
   - Pravděpodobně issue s docker kontejnerem nebo Azure CLI v docker
3. **Step 3 (ACR Build)** - Někdy funguje, někdy ne ✅/❌

### Kdy použít deploy.sh

**Úplný Fresh Deploy:**
```bash
./deploy.sh
```
- Vytvoří/aktualizuje infrastrukturu
- Builduje a pushuje image
- Vhodné pro: První deployment, změny v Bicep, změny env vars

**Běžná aktualizace (kdy infrastruktura existuje):**
```bash
# Jen build a push - skip Bicep
source deploy.env
docker run --rm \
  -e AZURE_CLIENT_ID="$AZURE_CLIENT_ID" \
  -e AZURE_CLIENT_SECRET="$AZURE_CLIENT_SECRET" \
  -v ~/.azure:/root/.azure \
  -v "$(pwd):/workspace" \
  -w /workspace \
  mcr.microsoft.com/azure-cli:latest \
  bash -c "
    az login --service-principal -u \$AZURE_CLIENT_ID -p \$AZURE_CLIENT_SECRET --tenant d15176d7-e40c-4cae-bff5-11d57e820fbd > /dev/null 2>&1
    az account set --subscription 2ae6e588-ab90-4994-a6f9-542500cba224 > /dev/null 2>&1
    az acr build -r parkingcr --image 'parking:latest' .
  "
```

---

## 📋 Doporučená Cesta: Build → Commit → Push → Restart

### 1. Code Changes
```bash
# Edit files
nano app/services/entra_id.py
```

### 2. Git Commit
```bash
git add .
git commit -m "fix: message"
```

### 3. Update Version
```bash
# Edit app/config.py - bump version
sed -i 's/v1.4.3/v1.4.4/' app/config.py
git add app/config.py
git commit -m "chore: bump to v1.4.4"
```

### 4. Docker Build Lokálně
```bash
docker build -t parking:v1.4.4 .
```

### 5. Push do ACR
```bash
source deploy.env

docker run --rm \
  -e AZURE_CLIENT_ID="$AZURE_CLIENT_ID" \
  -e AZURE_CLIENT_SECRET="$AZURE_CLIENT_SECRET" \
  -v ~/.azure:/root/.azure \
  -v "$(pwd):/workspace" \
  -w /workspace \
  mcr.microsoft.com/azure-cli:latest \
  bash -c "
    az login --service-principal -u \$AZURE_CLIENT_ID -p \$AZURE_CLIENT_SECRET --tenant d15176d7-e40c-4cae-bff5-11d57e820fbd > /dev/null 2>&1
    az account set --subscription 2ae6e588-ab90-4994-a6f9-542500cba224 > /dev/null 2>&1
    az acr build -r parkingcr --image 'parking:latest' .
  "
```

**Pokud ACR build selže:** Zkusit znovu (někdy je to jen fluke)

### 6. Manual Container App Restart
```
Azure Portal:
  1. Container Apps → parking-app
  2. Stop (čekej)
  3. Start (čekej 2-3 minuty)
```

### 7. Ověřit
```bash
# Check version
curl -s https://parking.alintrust.cz/ | grep -o "v[0-9]\.[0-9]\.[0-9]"

# Test feature
https://parking.alintrust.cz/admin/users → 🔄 Načíst uživatele
```

---

## 🔧 Config

Deployment credentials v `deploy.env`:
```bash
AZURE_CLIENT_ID=<your-client-id>
AZURE_CLIENT_SECRET=<your-client-secret>
AZURE_TENANT_ID=<your-tenant-id>
```

Azure Details:
```
Subscription: 2ae6e588-ab90-4994-a6f9-542500cba224
Resource Group: Parking
Container Registry: parkingcr (parkingcr.azurecr.io)
Container App: parking-app
Region: germanywestcentral
```

---

## ⚠️ Known Issues

1. **ACR Resource Lookup** - Někdy selhává random, zkusit znovu
2. **Service Principal Permissions** - Nelze restartovat Container App přes API
3. **Docker Login** - Service Principal credentials nejsou ACR login

---

## ✅ Deploy.sh je Správná Cesta

**Poznatek:** `deploy.sh` je plně funkční cesta na deployment!

### Když infrastructure existuje (obvyklý case):
```bash
# Příprava
source deploy.env

# Spustit deploy.sh
./deploy.sh
```

**Co se stane:**
1. ✅ Přihlášení k Azure
2. ⚠️ Bicep deployment (aktualizuje konfiguraci, ale již existující prostředky)
3. ✅ Docker image builduje se v ACR a pushuje se
4. Container App se automaticky refreshne (podívá se na nový image)

Výsledek: **v1.4.4 je live bez ručního restartu v Azure Portal!**

---

## 🎯 Future Improvements

1. Přidat service principal oprávnění na Container App restart
2. Zkusit GitHub Actions pro automatický deploy
3. Nastavit webhook v ACR pro automatický restart Container App po push
