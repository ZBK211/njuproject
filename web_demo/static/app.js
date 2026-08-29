const runBtn = document.getElementById("runBtn");
const statusEl = document.getElementById("status");
const taskEl = document.getElementById("task");
const flowEl = document.getElementById("flow");
const transcriptEl = document.getElementById("transcript");
const codeView = document.getElementById("codeView");
const testView = document.getElementById("testView");
const diffView = document.getElementById("diffView");
const testFileView = document.getElementById("testFileView");
const memoryView = document.getElementById("memoryView");
const auditGrid = document.getElementById("auditGrid");
const toolCallsEl = document.getElementById("toolCalls");
const workspacePath = document.getElementById("workspacePath");
const stepsMetric = document.getElementById("stepsMetric");
const testsMetric = document.getElementById("testsMetric");
const memoryMetric = document.getElementById("memoryMetric");
const providerBox = document.getElementById("providerBox");
const baseUrlEl = document.getElementById("baseUrl");
const modelNameEl = document.getElementById("modelName");
const apiKeyEl = document.getElementById("apiKey");

const flow = [
  ["Task", "用户任务进入 Agent.run"],
  ["Model", "模型返回一个 JSON action"],
  ["Tool", "本地工具读写文件或执行命令"],
  ["Observation", "工具结果回填上下文"],
  ["Final", "验证后结束并写入项目记忆"],
];

function renderFlow(active = 0, done = 0) {
  flowEl.innerHTML = flow.map((item, index) => {
    const current = index + 1;
    const state = current <= done ? "done" : current === active ? "active" : "";
    return `<div class="flow-step ${state}">
      <div class="num">${current}</div>
      <strong>${item[0]}</strong>
      <p>${item[1]}</p>
    </div>`;
  }).join("");
}

function setStatus(cls, text) {
  statusEl.className = `status ${cls}`;
  statusEl.textContent = text;
}

function renderTranscript(items) {
  if (!items.length) {
    transcriptEl.textContent = "没有 transcript。";
    return;
  }
  transcriptEl.textContent = items.map((item) => {
    const title = item.tool ? `${item.type.toUpperCase()} ${item.step} ${item.tool}` : `${item.type.toUpperCase()} ${item.step}`;
    return `[${title}]\n${item.text}`;
  }).join("\n\n");
}

function renderAudit(items) {
  auditGrid.innerHTML = items.map((item) => `
    <div class="audit-item ${item.level}">
      <strong>${item.title}</strong>
      <p>${item.detail}</p>
    </div>
  `).join("");
}

function selectedMode() {
  return document.querySelector('input[name="mode"]:checked')?.value || "offline";
}

function renderToolCalls(items) {
  if (!items.length) {
    toolCallsEl.textContent = "没有工具调用。";
    return;
  }
  toolCallsEl.innerHTML = items.map((item) => `
    <article class="tool-call">
      <div class="tool-top">
        <strong>${item.tool}</strong>
        <span>step ${item.step}</span>
      </div>
      <p>${item.summary}</p>
      <div class="tool-args">
        <span>arguments</span>
        <code>${escapeHtml(JSON.stringify(item.arguments || {}, null, 2))}</code>
      </div>
      <pre>${escapeHtml(item.output)}</pre>
    </article>
  `).join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function loadConfig() {
  try {
    const response = await fetch("/api/config");
    const data = await response.json();
    baseUrlEl.value = data.deepseek_base_url || "https://api.deepseek.com";
    modelNameEl.value = data.deepseek_model || "deepseek-chat";
    if (data.deepseek_configured) apiKeyEl.placeholder = "已检测到环境变量，可留空";
  } catch {
    // The demo can still run offline.
  }
}

async function runDemo() {
  runBtn.disabled = true;
  setStatus("running", "正在运行");
  renderFlow(1, 0);
  transcriptEl.textContent = "后端正在重置演示工作区并运行 Agent...";
  codeView.textContent = "等待生成";
  diffView.textContent = "等待 diff";
  testView.textContent = "等待测试";
  testFileView.textContent = "等待读取";
  memoryView.textContent = "等待写入";
  toolCallsEl.textContent = "等待本地工具调用";
  workspacePath.textContent = "workspace: 后端正在创建演示工作区";
  stepsMetric.textContent = "0";
  testsMetric.textContent = "-";
  memoryMetric.textContent = "-";
  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        task: taskEl.value,
        mode: selectedMode(),
        provider: {
          base_url: baseUrlEl.value,
          model: modelNameEl.value,
          api_key: apiKeyEl.value,
        },
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "demo failed");
    renderFlow(0, 5);
    renderTranscript(data.transcript);
    renderToolCalls(data.tool_calls || []);
    workspacePath.textContent = `workspace: ${data.workspace || "unknown"}`;
    codeView.textContent = data.files.fizzbuzz || "(missing)";
    diffView.textContent = data.file_diff || "(no diff)";
    testView.textContent = data.test_output || "(no test output)";
    testFileView.textContent = data.files.test_fizzbuzz || "(missing)";
    memoryView.textContent = data.memory || "(no memory generated)";
    stepsMetric.textContent = String(data.steps);
    testsMetric.textContent = data.tests_passed ? "pass" : "check";
    memoryMetric.textContent = data.memory_recorded ? "yes" : "no";
    renderAudit(data.audit);
    setStatus("done", "运行完成");
  } catch (error) {
    renderFlow(0, 0);
    transcriptEl.textContent = error.message;
    setStatus("error", "运行失败");
  } finally {
    runBtn.disabled = false;
  }
}

renderFlow();
renderAudit([]);
loadConfig();
document.querySelectorAll('input[name="mode"]').forEach((input) => {
  input.addEventListener("change", () => {
    providerBox.hidden = selectedMode() !== "deepseek";
  });
});
runBtn.addEventListener("click", runDemo);
