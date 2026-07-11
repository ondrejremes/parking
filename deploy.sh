#!/bin/bash
set -e

# ────────────────────────────────────────────────────────────────
# Parking App Azure Deployment Script
# ────────────────────────────────────────────────────────────────

# Configuration
SUBSCRIPTION_ID="2ae6e588-ab90-4994-a6f9-542500cba224"
TENANT_ID="d15176d7-e40c-4cae-bff5-11d57e820fbd"
RESOURCE_GROUP="Parking"
REGION="germanywestcentral"
APP_NAME="parking"
ACR_NAME="parkingcr"
# CUSTOM_DOMAIN is read from deploy.env (set to empty to disable custom domain creation)

# Credentials from environment variables (NEVER hardcode!)
AZURE_CLIENT_ID="${AZURE_CLIENT_ID:?Environment variable AZURE_CLIENT_ID is required}"
AZURE_CLIENT_SECRET="${AZURE_CLIENT_SECRET:?Environment variable AZURE_CLIENT_SECRET is required}"
ADMIN_USERNAME="${ADMIN_USERNAME:?Environment variable ADMIN_USERNAME is required}"
ADMIN_PASSWORD_HASH="${ADMIN_PASSWORD_HASH:?Environment variable ADMIN_PASSWORD_HASH is required}"
SESSION_SECRET="${SESSION_SECRET:?Environment variable SESSION_SECRET is required}"
ACS_CONNECTION_STRING="${ACS_CONNECTION_STRING:?Environment variable ACS_CONNECTION_STRING is required}"

# ────────────────────────────────────────────────────────────────
# Docker wrapper for az CLI (only if not already in Docker)
# ────────────────────────────────────────────────────────────────
if [ -f /.dockerenv ]; then
  # Already in Docker, use az directly
  az() { command az "$@"; }
else
  # Not in Docker, wrap az with Docker
  az() {
    docker run --rm -v ~/.azure:/root/.azure -v "$(pwd):/workspace" -w /workspace \
      mcr.microsoft.com/azure-cli:latest az "$@"
  }
fi

echo "════════════════════════════════════════════════════════════"
echo "🚀 Parking App - Azure Deployment"
echo "════════════════════════════════════════════════════════════"

# Step 1: Login (nebo use existing auth)
echo ""
echo "📌 Step 1: Checking Azure authentication..."
az account show > /dev/null 2>&1 || az login --tenant "$TENANT_ID"
az account set --subscription "$SUBSCRIPTION_ID"

# Step 2: Deploy Bicep (creates ACR first)
echo ""
echo "📌 Step 2: Deploying infrastructure with Bicep..."
az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file infra/main.bicep \
  --parameters \
    containerImage="$ACR_NAME.azurecr.io/$APP_NAME:latest" \
    customDomain="$CUSTOM_DOMAIN" \
    azureTenantId="$TENANT_ID" \
    azureClientId="$AZURE_CLIENT_ID" \
    azureClientSecret="$AZURE_CLIENT_SECRET" \
    sessionSecret="$SESSION_SECRET" \
    adminUsername="$ADMIN_USERNAME" \
    adminPasswordHash="$ADMIN_PASSWORD_HASH" \
    acsConnectionString="$ACS_CONNECTION_STRING"

# Step 3: Build Docker image directly in ACR (now that ACR exists)
echo ""
echo "📌 Step 3: Building and pushing Docker image to ACR..."
az acr build --registry "$ACR_NAME" --image "$APP_NAME:latest" .

echo ""
echo "✅ Deployment complete!"
echo "📍 Getting Front Door endpoint..."
az deployment group show --resource-group "$RESOURCE_GROUP" --name main --query properties.outputs --output json
