#!/usr/bin/env bash
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-sre-agent-demo}"
WEBAPP_NAME="${WEBAPP_NAME:-sre-demo-order-31591}"

echo "==> [Scenario 1A] Injecting faulty configuration into $WEBAPP_NAME..."
az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$WEBAPP_NAME" \
  --settings \
    FAULT_MODE="bad_config" \
    DB_MAX_CONNECTIONS="0" \
    PAYMENT_GATEWAY_URL="https://deprecated-v1.payments.contoso.invalid/charge" \
  --output none

HOST=$(az webapp show -g "$RESOURCE_GROUP" -n "$WEBAPP_NAME" --query defaultHostName -o tsv)
URL="https://$HOST"

echo "==> Waiting 8 seconds for App Service settings to apply..."
sleep 8

echo "==> Generating 25 requests to $URL/api/checkout to trigger HTTP 503 & Azure Monitor Alert..."
for i in $(seq 1 25); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$URL/api/checkout" \
    -H "Content-Type: application/json" \
    -d "{\"item\":\"Order-$i\",\"amount\":199.0,\"quantity\":1}" || true)
  printf "  Request #%02d -> HTTP %s\n" "$i" "$STATUS"
done

echo ""
echo "Outage active! App Insights is now logging ConnectionPoolExhaustedError (HTTP 503)."
echo "Open Azure SRE Agent to watch autonomous RCA and remediation."
