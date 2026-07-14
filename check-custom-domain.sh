#!/bin/bash

# Check if custom domain exists in Azure Front Door
SUBSCRIPTION_ID="2ae6e588-ab90-4994-a6f9-542500cba224"
RESOURCE_GROUP="Parking"
PROFILE_NAME="parking-afd"
CUSTOM_DOMAIN_RESOURCE_NAME="parking-alintrust-cz"

echo "🔍 Ověřuji, zda custom domain existuje v Azure..."

# Try to get the custom domain resource
DOMAIN_EXISTS=$(az cdn custom-domain show \
  --resource-group "$RESOURCE_GROUP" \
  --profile-name "$PROFILE_NAME" \
  --custom-domain-name "$CUSTOM_DOMAIN_RESOURCE_NAME" \
  --query "hostNames[0]" \
  -o tsv 2>/dev/null)

if [ -z "$DOMAIN_EXISTS" ]; then
  echo "❌ Custom domain NEEXISTUJE"
  echo "✓ CUSTOM_DOMAIN='parking.alintrust.cz' (bude vytvořena)"
  echo "export CUSTOM_DOMAIN='parking.alintrust.cz'"
else
  echo "✅ Custom domain JIŽ EXISTUJE: $DOMAIN_EXISTS"
  echo "✓ CUSTOM_DOMAIN='' (přeskočit vytvoření, použít existující)"
  echo "export CUSTOM_DOMAIN=''"
fi
