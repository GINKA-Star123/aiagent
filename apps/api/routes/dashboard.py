from __future__ import annotations

from html import escape
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from cloud.admin_auth import require_cloud_admin
from cloud.config import cloud_settings
from cloud.gpu_client import gpu_client
from cloud.redis_client import redis_health
from cloud.task_queue import CloudTaskQueue
from apps.api.metrics_store import metrics_store
from apps.core.runtime_registry import get_runtime_error

router = APIRouter()
task_queue = CloudTaskQueue(prefix=cloud_settings.redis_prefix)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(_: None = Depends(require_cloud_admin)):
    return HTMLResponse(_dashboard_html())


@router.get("/dashboard/api/snapshot")
async def dashboard_snapshot(_: None = Depends(require_cloud_admin)):
    redis = await redis_health()
    gpu = await gpu_client.health_all()

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
      height: 64px;
      display: flex;
      align-items: center;
      justify-content: space-between;
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
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
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
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      color: var(--muted);
    }
    .dot {
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: var(--muted);
    }
    .ok .dot { background: var(--ok); }
    .bad .dot { background: var(--bad); }
    .warn .dot { background: var(--warn); }
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
    }
    .two {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
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
    @media (max-width: 980px) {
      .grid, .two { grid-template-columns: 1fr; }
      header { padding: 0 16px; }
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
    <h2>最近请求</h2>
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
  </section>
</main>

<script>
const adminToken = new URLSearchParams(location.search).get("token") || localStorage.getItem("aiagent_admin_token") || "";
if (adminToken) {
  localStorage.setItem("aiagent_admin_token", adminToken);
}

function statusLine(label, ok, detail = "") {
  const cls = ok ? "ok" : "bad";
  return `<div class="status ${cls}"><span class="dot"></span><span>${label}${detail ? "：" + detail : ""}</span></div>`;
}

function secondsToText(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${h}h ${m}m ${s}s`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
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
  const metrics = data.metrics;

  document.getElementById("updated").textContent = `刷新于 ${new Date().toLocaleTimeString()}`;
  document.getElementById("uptime").textContent = secondsToText(metrics.uptime_seconds);
  document.getElementById("avgLatency").textContent = `${metrics.avg_latency_ms} ms`;
  document.getElementById("errors").textContent = metrics.recent_errors;
  document.getElementById("limited").textContent = metrics.recent_limited;

  document.getElementById("coreStatus").innerHTML = [
    statusLine("Runtime", data.runtime.import_ok, data.runtime.import_ok ? "OK" : data.runtime.error),
    statusLine("Redis", Boolean(data.redis.ok), data.redis.ok ? "OK" : (data.redis.error || "未连接")),
    statusLine("Cloud Mode", Boolean(data.cloud.cloud_mode), data.cloud.cloud_mode ? "ON" : "OFF"),
    statusLine("Rate Limit", Boolean(data.cloud.rate_limit_enabled), data.cloud.rate_limit_enabled ? "ON" : "OFF"),
    statusLine("Inflight Limit", Boolean(data.cloud.inflight_limit_enabled), data.cloud.inflight_limit_enabled ? "ON" : "OFF"),
  ].join("<br>");

  const gpu = data.gpu;
  document.getElementById("gpuStatus").innerHTML = ["llm", "tts", "asr"].map((name) => {
    const item = gpu[name] || {};
    const detail = item.configured ? (item.ok ? "OK" : (item.error || item.status_code || "异常")) : "未配置";
    return statusLine(name.toUpperCase(), item.configured ? Boolean(item.ok) : true, detail);
  }).join("<br>");

  document.getElementById("cloudConfig").textContent = JSON.stringify(data.cloud, null, 2);
  document.getElementById("routeCounts").textContent = JSON.stringify(metrics.route_counts, null, 2);

  const rows = metrics.recent_requests.map((item) => {
    const statusColor = item.status_code >= 500 ? "var(--bad)" : item.status_code >= 400 ? "var(--warn)" : "var(--ok)";
    return `
      <tr>
        <td>${new Date(item.created_at * 1000).toLocaleTimeString()}</td>
        <td style="color:${statusColor};font-weight:700">${item.status_code}</td>
        <td>${escapeHtml(item.method)}</td>
        <td><code>${escapeHtml(item.path)}</code></td>
        <td>${item.latency_ms} ms</td>
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


def safe_text(value: Any) -> str:
    return escape(str(value))