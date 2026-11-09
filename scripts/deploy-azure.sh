#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-sre-agent-demo}"
LOCATION="${LOCATION:-westus3}"
APP_NAME="${APP_NAME:-sre-demo-order-$RANDOM}"

echo "==> [1/3] Ensuring Resource Group: $RESOURCE_GROUP ($LOCATION)"
if ! az group show --name "$RESOURCE_GROUP" --output none 2>/dev/null; then
  az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none
fi

# Clean up corrupted/0-byte local bicep binary if present
if [ -f "$HOME/.azure/bin/bicep" ] && [ ! -s "$HOME/.azure/bin/bicep" ]; then
  rm -f "$HOME/.azure/bin/bicep"
fi

echo "==> [2/3] Deploying Azure App Service + App Insights + Http5xx Alert via ARM/Bicep"
DEPLOY_OUT=$(az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file infra/main.json \
  --parameters appName="$APP_NAME" location="$LOCATION" \
  --query "properties.outputs" \
  --output json)

WEBAPP_NAME=$(echo "$DEPLOY_OUT" | python3 -c "import sys, json; print(json.load(sys.stdin)['webAppName']['value'])")
WEBAPP_URL=$(echo "$DEPLOY_OUT" | python3 -c "import sys, json; print(json.load(sys.stdin)['webAppUrl']['value'])")

echo "==> [3/3] Packaging and deploying FastAPI application to $WEBAPP_NAME"
TMP_ZIP="/tmp/sre-demo-app-$$.zip"
rm -f "$TMP_ZIP"
trap 'rm -f "$TMP_ZIP"' EXIT
zip -r -q "$TMP_ZIP" app requirements.txt startup.sh -x "**/__pycache__/*"

az webapp deploy \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEBAPP_NAME" \
  --src-path "$TMP_ZIP" \
  --type zip \
  --output none

echo ""
echo "============================================================"
echo "Deployment Complete!"
echo "Resource Group : $RESOURCE_GROUP"
echo "Web App Name   : $WEBAPP_NAME"
echo "Dashboard URL  : $WEBAPP_URL"
echo "Health Check   : $WEBAPP_URL/health"
echo "============================================================"
echo "Export these for fault injection scripts:"
echo "  export RESOURCE_GROUP=\"$RESOURCE_GROUP\""
echo "  export WEBAPP_NAME=\"$WEBAPP_NAME\""
