#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-sre-agent-demo}"
WEBAPP_NAME="${WEBAPP_NAME:-sre-demo-order-31591}"

echo "==> Restoring $WEBAPP_NAME to healthy v1.1.0-stable configuration..."
az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEBAPP_NAME" \
  --settings \
    APP_VERSION="1.1.0-stable" \
    FAULT_MODE="none" \
    DB_MAX_CONNECTIONS="50" \
    PAYMENT_GATEWAY_URL="https://payments.contoso.internal/v2/charge" \
  --output none

HOST=$(az webapp show -g "$RESOURCE_GROUP" -n "$WEBAPP_NAME" --query defaultHostName -o tsv)
echo "==> Waiting 6 seconds and verifying https://$HOST/health ..."
sleep 6
curl -i -s "https://$HOST/health"
echo ""
