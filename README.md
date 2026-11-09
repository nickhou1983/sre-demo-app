# Contoso Order Service — Azure SRE Agent 演示工程 (`sre-demo-app`)

专为 **Microsoft Azure SRE Agent** 打造的场景 1（**不良发布 / 配置错误引发 HTTP 503 故障与自动排障**）端到端演示项目，基于 **Python FastAPI + Azure App Service + Application Insights + Bicep**。

## 核心特性

1. **可视化故障注入与实时遥测面板 (`/`)**
   - 实时展示 HTTP 200 / HTTP 503 请求计数、错误率、当前部署版本 (`APP_VERSION`) 与核心环境变量。
   - 支持网页端一键切换故障模式或发送突发流量，也支持通过 Azure CLI 修改 App Service 配置真实触发 Azure Activity Log 与 Azure Monitor 告警。
2. **双故障子场景支持**
   - **场景 1A（配置错误 `bad_config`）**：模拟 `DB_MAX_CONNECTIONS=0` 及失效的支付网关地址，抛出 `ConnectionPoolExhaustedError` 并返回 HTTP 503。
   - **场景 1B（不良发版 `bad_release`）**：模拟 `1.2.0-buggy` 版本上线，在 `app/services/checkout.py` 触发 `ReleaseRegressionError (KeyError: 'discount_tier_v2_multiplier')` 并返回 HTTP 503。
3. **开箱即用的 Azure 基础设施与 SRE 资产**
   - `infra/main.bicep`：自动部署 App Service (Linux Python 3.11)、Application Insights、Log Analytics 以及 `Http5xx > 5` 的 Sev-1 告警规则。
   - `demo/runbook-app-service-503.md`：可直接上传至 Azure SRE Agent 知识库的企业级排障 SOP 手册。
   - `demo/DEMO_GUIDE.md`：完整的现场演示步骤与 SRE Agent 互动 Prompt 剧本。

## 快速开始

### 本地运行与预览
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
浏览器打开 `http://localhost:8000` 即可体验可视化故障注入控制台。

### 部署到 Azure 并演示 SRE Agent
```bash
# 1. 一键部署 Bicep 基础设施与应用
./scripts/deploy-azure.sh

# 2. 注入配置故障并发送 25 次请求触发 503 告警
export RESOURCE_GROUP="rg-sre-agent-demo"
export WEBAPP_NAME="<部署输出的 WebApp 名称>"
./scripts/trigger-outage-config.sh

# 3. 或模拟 v1.2.0-buggy 不良发版引发代码异常 503
./scripts/trigger-outage-release.sh

# 4. 手动恢复健康状态（也可交由 Azure SRE Agent 自动执行）
./scripts/restore-healthy.sh
```

详细现场演示步骤与 Prompt 话术请参阅 [`demo/DEMO_GUIDE.md`](demo/DEMO_GUIDE.md)。
