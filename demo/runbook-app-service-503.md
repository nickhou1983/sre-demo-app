# Standard Operating Procedure (SOP): Contoso Order Service HTTP 503 Outage

**Service Name**: Contoso Order & Checkout Service (`sre-demo-app`)  
**Platform**: Azure App Service (Linux, Python 3.11 FastAPI)  
**Telemetry**: Azure Application Insights + Log Analytics  
**Repository**: `nickhou1983/sre-demo-app`

---

## 1. Symptoms & Alert Triggers
- Azure Monitor Alert `*-http5xx-outage` fires when `Http5xx > 5` within a 5-minute window.
- Health probe `/health` and business endpoints (`/api/orders`, `/api/checkout`) return `HTTP 503 Service Unavailable`.

---

## 2. Triage & Root Cause Analysis Steps

When investigating HTTP 503 errors on the Contoso Order Service Web App, execute the following checks in order:

### Step 1: Check Application Insights Exceptions & Traces
Query the linked Application Insights / Log Analytics workspace (`AppExceptions` / `AppTraces` or `exceptions` / `traces` tables) over the last 30 minutes:
- Look for `ConnectionPoolExhaustedError` or `ReleaseRegressionError` in `app/services/checkout.py`.

### Step 2: Inspect Azure Activity Log & App Service Configuration
Check recent changes to App Service Application Settings (`Microsoft.Web/sites/config/write`):
1. **`DB_MAX_CONNECTIONS`**: Must be an integer `>= 10` (baseline is `50`). If set to `0` or negative, the service raises `ConnectionPoolExhaustedError` and returns HTTP 503.
2. **`PAYMENT_GATEWAY_URL`**: Must be `https://payments.contoso.internal/v2/charge`. Any URL containing `invalid` or `deprecated` causes HTTP 503.
3. **`FAULT_MODE`**: Must be `none` in production. Values `bad_config` or `bad_release` indicate active fault injection or a broken rollout.
4. **`APP_VERSION`**: Baseline stable release is `1.1.0-stable`. Version `1.2.0-buggy` contains a known `KeyError: 'discount_tier_v2_multiplier'` regression in `app/services/checkout.py`.

---

## 3. Approved Remediation Actions

### Case A: Configuration Drift (`ConnectionPoolExhaustedError` / `bad_config`)
Restore the approved production App Settings using Azure CLI:
```bash
az webapp config appsettings set \
  --resource-group <RESOURCE_GROUP> \
  --name <WEBAPP_NAME> \
  --settings \
    FAULT_MODE="none" \
    DB_MAX_CONNECTIONS="50" \
    PAYMENT_GATEWAY_URL="https://payments.contoso.internal/v2/charge"
```

### Case B: Bad Release Regression (`ReleaseRegressionError` / `1.2.0-buggy`)
1. Roll back the application version setting immediately:
```bash
az webapp config appsettings set \
  --resource-group <RESOURCE_GROUP> \
  --name <WEBAPP_NAME> \
  --settings \
    APP_VERSION="1.1.0-stable" \
    FAULT_MODE="none"
```
2. Create a GitHub Issue in `nickhou1983/sre-demo-app` documenting the `KeyError: 'discount_tier_v2_multiplier'` stack trace in `app/services/checkout.py` and the mitigation timeline.

---

## 4. Post-Mitigation Verification
Verify recovery by calling `GET https://<defaultHostName>/health` and `GET https://<defaultHostName>/api/orders` and confirming both return `HTTP 200 OK` with `"status": "healthy"`.
