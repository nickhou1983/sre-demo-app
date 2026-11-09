# Azure SRE Agent 现场演示指南（场景 1：不良发布/配置变更引发 503 故障）

本指南提供从 **环境部署 → SRE Agent 接入 → 故障触发 → 现场互动问答与自动修复** 的完整演示剧本。

---

## 一、演示前准备（5 分钟）

### 1. 一键部署演示环境到 Azure
确保已登录 Azure CLI (`az login`)，在仓库根目录运行：
```bash
chmod +x scripts/*.sh startup.sh
./scripts/deploy-azure.sh
```
脚本会自动创建：
- **Resource Group**: `rg-sre-agent-demo`（可通过环境变量自定义）
- **Log Analytics + Application Insights**: 自动挂载到 Web App，收集 HTTP 503 异常堆栈
- **Azure App Service (Python 3.11)**: 运行 Contoso Order & Checkout Service
- **Azure Monitor Sev-1 告警规则**: 当 5 分钟内 `Http5xx > 5` 时自动触发告警

部署完成后，记录输出的环境变量：
```bash
export RESOURCE_GROUP="rg-sre-agent-demo"
export WEBAPP_NAME="<输出中的 Web App 名称>"
```

### 2. 配置 Azure SRE Agent
1. 在 Azure Portal 创建或打开你的 **Azure SRE Agent**。
2. **授权托管资源组**：将 `rg-sre-agent-demo` 添加到 SRE Agent 的受管资源范围（赋予 Reader + Website Contributor 权限以允许执行修复）。
3. **（可选）上传企业排障手册**：在 SRE Agent 的 **Knowledge Base / Runbooks** 中上传本仓库的 `demo/runbook-app-service-503.md`。
4. **（可选）连接 GitHub 仓库**：在 SRE Agent 的 Integrations 中连接 `nickhou1983/sre-demo-app`，以便演示自动提 Issue。

---

## 二、现场演示剧本（Live Demo Flow）

### 阶段 1：展示健康基线（1 分钟）
1. 打开浏览器访问 Web App 控制台首页 `https://<WEBAPP_NAME>.azurewebsites.net`。
2. 展示当前状态为 **● 服务正常 (HTTP 200 OK)**，版本为 `1.1.0-stable`。
3. 点击页面上的 **“🛒 发起单笔下单”**，展示请求返回 `HTTP 200`。

---

### 阶段 2：注入故障（模拟不良配置发布或 Bug 发版）（1 分钟）
你可以选择 **命令行注入**（推荐，会在 Azure Activity Log 留下真实变更记录）或 **网页端一键注入**：

- **方式 A（推荐 - 模拟错误配置变更引发连接池耗尽 503）**：
  ```bash
  ./scripts/trigger-outage-config.sh
  ```
  *效果*：通过 `az webapp config appsettings set` 将 `DB_MAX_CONNECTIONS` 设为 `0`、支付网关地址改为失效地址，并连续发送 25 个请求触发 `Http5xx` 告警。

- **方式 B（模拟 v1.2.0-buggy 不良代码发版引发 KeyError 503）**：
  ```bash
  ./scripts/trigger-outage-release.sh
  ```
  *效果*：模拟上线 `1.2.0-buggy`，在 `app/services/checkout.py` 抛出 `ReleaseRegressionError (KeyError: 'discount_tier_v2_multiplier')`。

此时回到 Web 控制台页面，状态栏变为红色 **▲ 服务故障 (HTTP 503 Service Unavailable)**，5xx 错误率飙升。

---

### 阶段 3：在 Azure SRE Agent 中演示核心能力（5 分钟）

#### 演示点 1：多信号根因分析（RCA）
当 Azure Monitor 告警自动触发 incident，或在 SRE Agent 对话框输入以下 Prompt：

> **Prompt 1（根因诊断）**：
> `Our Contoso Order Service web app in resource group rg-sre-agent-demo is returning HTTP 503 errors. Please investigate the root cause using Application Insights exceptions, recent Activity Log changes, and App Service configuration.`

**向观众讲解的亮点**：
- Agent 自动查询 App Insights 异常表，定位到 `app/services/checkout.py` 中的 `ConnectionPoolExhaustedError` 或 `ReleaseRegressionError`。
- Agent 自动比对 Azure Activity Log 和当前 App Settings，发现刚刚有人修改了 `DB_MAX_CONNECTIONS=0` 或发布了 `APP_VERSION=1.2.0-buggy`。

#### 演示点 2：遵循企业 Runbook 自动修复（Remediation）
继续在 SRE Agent 中输入（或在 Incident 线程中点击 Approve）：

> **Prompt 2（执行修复并验证）**：
> `Follow our Contoso Order Service 503 SOP runbook to remediate the issue on the Web App, then verify that /health and /api/orders return HTTP 200.`

**向观众讲解的亮点**：
- 展示 **Human-in-the-loop (Review 模式)** 或 **Autonomous 模式**：Agent 生成修复用的 Azure CLI 命令（将 `DB_MAX_CONNECTIONS` 恢复为 `50`、`FAULT_MODE=none`、`APP_VERSION=1.1.0-stable`）。
- 修复执行后，切回 Web 控制台页面，观众可以实时看到状态自动恢复为绿色 **● 服务正常 (HTTP 200 OK)**！

#### 演示点 3：代码联动与复盘总结（Post-Incident & GitHub Integration）
> **Prompt 3（生成复盘与 GitHub Issue）**：
> `Generate a post-incident RCA summary with timeline, root cause in app/services/checkout.py, and remediation taken, and create a GitHub issue in nickhou1983/sre-demo-app to track adding config validation in CI/CD.`
