#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-sre-agent-demo}"
WEBAPP_NAME="${WEBAPP_NAME:-sre-demo-order-31591}"

echo "==> [Scenario 1B] Simulating bad release rollout (v1.2.0-buggy) on $WEBAPP_NAME..."
az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEBAPP_NAME" \
  --settings \
    APP_VERSION="1.2.0-buggy" \
    FAULT_MODE="bad_release" \
  --output none

HOST=$(az webapp show -g "$RESOURCE_GROUP" -n "$WEBAPP_NAME" --query defaultHostName -o tsv)
URL="https://$HOST"

echo "==> Waiting 8 seconds for release settings to take effect..."
sleep 8

echo "==> Sending 25 checkout requests to $URL/api/checkout to trigger HTTP 503 regression..."
for i in $(seq 1 25); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$URL/api/checkout" \
    -H "Content-Type: application/json" \
    -d "{\"item\":\"ReleaseTest-$i\",\"amount\":299.0,\"quantity\":1}" || true)
  printf "  Request #%02d -> HTTP %s\n" "$i" "$STATUS"
done

echo ""
echo "Bad release outage active! App Insights is logging ReleaseRegressionError in app/services/checkout.py."
