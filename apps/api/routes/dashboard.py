from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from apps.api.metrics_store import metrics_store
from apps.core.runtime_registry import get_runtime_error
from cloud.admin_auth import require_cloud_admin
from cloud.config import cloud_settings
from cloud.gpu_client import gpu_client
from cloud.redis_client import redis_health
from cloud.task_queue import CloudTaskQueue

router = APIRouter()
task_queue = CloudTaskQueue(prefix=cloud_settings.redis_prefix)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(_: None = Depends(require_cloud_admin)):
    return HTMLResponse(_dashboard_html())


@router.get("/dashboard/api/snapshot")
async def dashboard_snapshot(_: None = Depends(require_cloud_admin)):
    redis = await redis_health()
    gpu = await gpu_client.health_all()
    task_summary = await task_queue.task_summary(queue="default")
    dead_tasks = await task_queue.list_dead_tasks(queue="default", limit=10)

    return {
        "ok": True,
        "runtime": {
            "import_ok": get_runtime_error() is None,
            "error": get_runtime_error(),
        },
        "cloud": {
            "cloud_mode": cloud_settings.cloud_mode,
            "region": cloud_settings.cloud_deploy_region,
            "storage_provider": cloud_settings.storage_provider,
            "rate_limit_enabled": cloud_settings.rate_limit_enabled,
            "inflight_limit_enabled": cloud_settings.inflight_limit_enabled,
            "global_inflight_limit": cloud_settings.global_inflight_limit,
            "chat_inflight_limit": cloud_settings.chat_inflight_limit,
            "multimodal_inflight_limit": cloud_settings.multimodal_inflight_limit,
            "voice_inflight_limit": cloud_settings.voice_inflight_limit,
        },
        "redis": redis,
        "gpu": gpu,
        "metrics": metrics_store.snapshot(),
        "tasks": {
            "summary": task_summary,
            "dead": dead_tasks,
        },
    }


def _dashboard_html() -> str:
    return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>AIAgent Dashboard</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #101216;
      --panel: #171a20;
      --panel-2: #1e232b;
      --text: #f2f4f8;
      --muted: #9aa4b2;
      --line: #2b323d;
      --ok: #43d17a;
      --warn: #ffcc66;
      --bad: #ff6b6b;
      --blue: #6aa9ff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      min-height: 64px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 0 24px;
      border-bottom: 1px solid var(--line);
      background: #0d0f13;
    }
    h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 700;
      letter-spacing: 0;
    }
    main {
      padding: 20px;
      display: grid;
      gap: 16px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 16px;
    }
    .three {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
    }
    .two {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      min-width: 0;
    }
    .panel h2 {
      margin: 0 0 12px;
      font-size: 15px;
      color: var(--muted);
      font-weight: 600;
    }
    .metric {
      font-size: 28px;
      font-weight: 760;
      line-height: 1.2;
    }
    .sub {
      margin-top: 6px;
      color: var(--muted);
      font-size: 13px;
    }
    .status {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 8px 0;
      font-size: 14px;
      color: var(--muted);
    }
    .dot {
      width: 9px;
      height: 9px;
      flex: 0 0 auto;
      border-radius: 999px;
      background: var(--muted);
    }
    .ok .dot { background: var(--ok); }
    .bad .dot { background: var(--bad); }
    .warn .dot { background: var(--warn); }
    .kv {
      display: grid;
      grid-template-columns: 92px 1fr;
      gap: 8px;
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
    }
    .kv b {
      color: var(--text);
      font-weight: 600;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    th, td {
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font-weight: 600;
    }
    code {
      color: var(--blue);
      background: var(--panel-2);
      padding: 2px 5px;
      border-radius: 4px;
      word-break: break-all;
    }
    button {
      border: 1px solid var(--line);
      background: var(--panel-2);
      color: var(--text);
      border-radius: 6px;
      padding: 6px 10px;
      cursor: pointer;
      font-size: 13px;
      white-space: nowrap;
    }
    button:hover {
      border-color: var(--blue);
      color: var(--blue);
    }
    .json {
      white-space: pre-wrap;
      word-break: break-word;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      color: #d7dee9;
      background: var(--panel-2);
      padding: 12px;
      border-radius: 6px;
      max-height: 360px;
      overflow: auto;
    }
    .table-wrap {
      overflow-x: auto;
    }
    .error-text {
      max-width: 560px;
      color: #d7dee9;
      white-space: pre-wrap;
      word-break: break-word;
    }
    @media (max-width: 980px) {
      .grid, .three, .two { grid-template-columns: 1fr; }
      header { padding: 12px 16px; align-items: flex-start; flex-direction: column; }
      main { padding: 16px; }
    }
  </style>
</head>
<body>
<header>
  <h1>AIAgent Dashboard</h1>
  <div id="updated" class="sub">等待刷新</div>
</header>

<main>
  <section class="grid">
    <div class="panel">
      <h2>运行时间</h2>
      <div id="uptime" class="metric">-</div>
      <div class="sub">API process uptime</div>
    </div>
    <div class="panel">
      <h2>平均延迟</h2>
      <div id="avgLatency" class="metric">-</div>
      <div class="sub">最近请求</div>
    </div>
    <div class="panel">
      <h2>错误</h2>
      <div id="errors" class="metric">-</div>
      <div class="sub">HTTP 5xx</div>
    </div>
    <div class="panel">
      <h2>限流/繁忙</h2>
      <div id="limited" class="metric">-</div>
      <div class="sub">429 / 503</div>
    </div>
  </section>

  <section class="grid">
    <div class="panel">
      <h2>队列任务</h2>
      <div id="taskTotal" class="metric">-</div>
      <div class="sub">default queue total</div>
    </div>
    <div class="panel">
      <h2>等待中</h2>
      <div id="taskQueued" class="metric">-</div>
      <div class="sub">queued</div>
    </div>
    <div class="panel">
      <h2>运行中</h2>
      <div id="taskRunning" class="metric">-</div>
      <div class="sub">running</div>
    </div>
    <div class="panel">
      <h2>Dead</h2>
      <div id="taskDead" class="metric">-</div>
      <div class="sub">dead-letter</div>
    </div>
  </section>

  <section class="two">
    <div class="panel">
      <h2>核心状态</h2>
      <div id="coreStatus"></div>
    </div>
    <div class="panel">
      <h2>GPU 状态</h2>
      <div id="gpuStatus"></div>
    </div>
  </section>

  <section class="three">
    <div class="panel">
      <h2>LLM</h2>
      <div id="gpuLlm"></div>
    </div>
    <div class="panel">
      <h2>TTS</h2>
      <div id="gpuTts"></div>
    </div>
    <div class="panel">
      <h2>ASR</h2>
      <div id="gpuAsr"></div>
    </div>
  </section>

  <section class="two">
    <div class="panel">
      <h2>云端配置</h2>
      <div id="cloudConfig" class="json"></div>
    </div>
    <div class="panel">
      <h2>路由计数</h2>
      <div id="routeCounts" class="json"></div>
    </div>
  </section>

  <section class="panel">
    <h2>Dead Letter 任务</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>任务 ID</th>
            <th>类型</th>
            <th>尝试次数</th>
            <th>错误</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody id="deadTasks"></tbody>
      </table>
    </div>
  </section>

  <section class="panel">
    <h2>最近请求</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>时间</th>
            <th>状态</th>
            <th>方法</th>
            <th>路径</th>
            <th>耗时</th>
            <th>Request ID</th>
          </tr>
        </thead>
        <tbody id="requests"></tbody>
      </table>
    </div>
  </section>
</main>

<script>
const adminToken = new URLSearchParams(location.search).get("token") || localStorage.getItem("aiagent_admin_token") || "";
if (adminToken) {
  localStorage.setItem("aiagent_admin_token", adminToken);
}

function statusLine(label, ok, detail = "") {
  const cls = ok ? "ok" : "bad";
  return `<div class="status ${cls}"><span class="dot"></span><span>${escapeHtml(label)}${detail ? "：" + escapeHtml(detail) : ""}</span></div>`;
}

function secondsToText(seconds) {
  const value = Number(seconds || 0);
  const h = Math.floor(value / 3600);
  const m = Math.floor((value % 3600) / 60);
  const s = value % 60;
  return `${h}h ${m}m ${s}s`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderGpuDetail(name, data) {
  const gpu = data.gpu || {};
  const metrics = data.metrics || {};
  const external = metrics.external_services || {};
  const circuit = gpu.circuit || {};

  const item = gpu[name] || {};
  const serviceMetric = external[name] || {};
  const circuitItem = circuit[name] || {};
  const configured = Boolean(item.configured);
  const state = circuitItem.state || "unknown";
  const healthText = configured ? (item.ok ? "OK" : (item.error || item.status_code || "异常")) : "未配置";
  const healthy = configured ? Boolean(item.ok) && state !== "open" : true;

  const rows = [
    ["健康", healthText],
    ["熔断", state],
    ["平均延迟", `${serviceMetric.avg_latency_ms ?? "-"} ms`],
    ["近期错误", serviceMetric.recent_errors ?? 0],
    ["近期调用", serviceMetric.recent_total ?? 0],
    ["最后错误", serviceMetric.last_error || circuitItem.last_error || "-"],
  ];

  return `
    ${statusLine(name.toUpperCase(), healthy, configured ? `circuit=${state}` : "未配置")}
    <div class="kv">
      ${rows.map(([key, value]) => `<span>${escapeHtml(key)}</span><b>${escapeHtml(value)}</b>`).join("")}
    </div>
  `;
}

async function retryTask(taskId) {
  const response = await fetch(`/cloud/tasks/${encodeURIComponent(taskId)}/retry`, {
    method: "POST",
    headers: adminToken ? { "x-cloud-admin-token": adminToken } : {}
  });

  if (!response.ok) {
    alert(`重试失败：${response.status}`);
    return;
  }

  await loadSnapshot();
}

async function loadSnapshot() {
  const response = await fetch("/dashboard/api/snapshot", {
    headers: adminToken ? { "x-cloud-admin-token": adminToken } : {}
  });

  if (!response.ok) {
    document.getElementById("coreStatus").innerHTML = statusLine("Dashboard 鉴权失败或服务不可用", false, response.status);
    return;
  }

  const data = await response.json();
  const metrics = data.metrics || {};
  const taskSummary = data.tasks?.summary || {};

  document.getElementById("updated").textContent = `刷新于 ${new Date().toLocaleTimeString()}`;
  document.getElementById("uptime").textContent = secondsToText(metrics.uptime_seconds);
  document.getElementById("avgLatency").textContent = `${metrics.avg_latency_ms ?? 0} ms`;
  document.getElementById("errors").textContent = metrics.recent_errors ?? 0;
  document.getElementById("limited").textContent = metrics.recent_limited ?? 0;

  document.getElementById("taskTotal").textContent = taskSummary.total ?? 0;
  document.getElementById("taskQueued").textContent = taskSummary.queued ?? 0;
  document.getElementById("taskRunning").textContent = taskSummary.running ?? 0;
  document.getElementById("taskDead").textContent = taskSummary.dead ?? 0;

  document.getElementById("coreStatus").innerHTML = [
    statusLine("Runtime", data.runtime?.import_ok, data.runtime?.import_ok ? "OK" : data.runtime?.error),
    statusLine("Redis", Boolean(data.redis?.ok), data.redis?.ok ? "OK" : (data.redis?.error || "未连接")),
    statusLine("Cloud Mode", Boolean(data.cloud?.cloud_mode), data.cloud?.cloud_mode ? "ON" : "OFF"),
    statusLine("Rate Limit", Boolean(data.cloud?.rate_limit_enabled), data.cloud?.rate_limit_enabled ? "ON" : "OFF"),
    statusLine("Inflight Limit", Boolean(data.cloud?.inflight_limit_enabled), data.cloud?.inflight_limit_enabled ? "ON" : "OFF"),
  ].join("");

  const gpu = data.gpu || {};
  const external = metrics.external_services || {};
  const circuit = gpu.circuit || {};
  document.getElementById("gpuStatus").innerHTML = ["llm", "tts", "asr"].map((name) => {
    const item = gpu[name] || {};
    const metricItem = external[name] || {};
    const circuitItem = circuit[name] || {};
    const configured = Boolean(item.configured);
    const state = circuitItem.state || "unknown";
    const avg = metricItem.avg_latency_ms ?? "-";
    const errors = metricItem.recent_errors ?? 0;
    const detail = configured
      ? `${item.ok ? "OK" : (item.error || item.status_code || "异常")} / circuit=${state} / avg=${avg}ms / errors=${errors}`
      : "未配置";
    return statusLine(name.toUpperCase(), configured ? Boolean(item.ok) && state !== "open" : true, detail);
  }).join("");

  document.getElementById("gpuLlm").innerHTML = renderGpuDetail("llm", data);
  document.getElementById("gpuTts").innerHTML = renderGpuDetail("tts", data);
  document.getElementById("gpuAsr").innerHTML = renderGpuDetail("asr", data);

  document.getElementById("cloudConfig").textContent = JSON.stringify(data.cloud || {}, null, 2);
  document.getElementById("routeCounts").textContent = JSON.stringify(metrics.route_counts || {}, null, 2);

  const deadTasks = data.tasks?.dead || [];
  document.getElementById("deadTasks").innerHTML = deadTasks.map((task) => {
    const taskId = String(task.id || "");
    const error = String(task.error || "").slice(0, 400);
    return `
      <tr>
        <td><code>${escapeHtml(taskId)}</code></td>
        <td>${escapeHtml(task.type || "")}</td>
        <td>${escapeHtml(task.attempts || 0)} / ${escapeHtml(task.max_attempts || 0)}</td>
        <td><div class="error-text">${escapeHtml(error)}</div></td>
        <td><button onclick="retryTask('${escapeHtml(taskId)}')">重试</button></td>
      </tr>
    `;
  }).join("") || `<tr><td colspan="5">暂无 dead 任务</td></tr>`;

  const requests = metrics.recent_requests || [];
  const rows = requests.map((item) => {
    const statusColor = item.status_code >= 500 ? "var(--bad)" : item.status_code >= 400 ? "var(--warn)" : "var(--ok)";
    return `
      <tr>
        <td>${new Date(item.created_at * 1000).toLocaleTimeString()}</td>
        <td style="color:${statusColor};font-weight:700">${escapeHtml(item.status_code)}</td>
        <td>${escapeHtml(item.method)}</td>
        <td><code>${escapeHtml(item.path)}</code></td>
        <td>${escapeHtml(item.latency_ms)} ms</td>
        <td><code>${escapeHtml(item.request_id)}</code></td>
      </tr>
    `;
  }).join("");

  document.getElementById("requests").innerHTML = rows || `<tr><td colspan="6">暂无请求</td></tr>`;
}

loadSnapshot();
setInterval(loadSnapshot, 5000);
</script>
</body>
</html>
"""
