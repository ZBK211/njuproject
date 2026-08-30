const runBtn = document.getElementById("runBtn");
const runCountEl = document.getElementById("runCount");
const statusEl = document.getElementById("status");
const taskEl = document.getElementById("task");
const flowEl = document.getElementById("flow");
const transcriptEl = document.getElementById("transcript");
const answerView = document.getElementById("answerView");
const testSummary = document.getElementById("testSummary");
const fileSummary = document.getElementById("fileSummary");
const codeView = document.getElementById("codeView");
const codeFileLabel = document.getElementById("codeFileLabel");
const testView = document.getElementById("testView");
const diffView = document.getElementById("diffView");
const testFileView = document.getElementById("testFileView");
const testFileLabel = document.getElementById("testFileLabel");
const memoryView = document.getElementById("memoryView");
const toolCallsEl = document.getElementById("toolCalls");
const toolRunLabel = document.getElementById("toolRunLabel");
const workspacePath = document.getElementById("workspacePath");
const historyView = document.getElementById("historyView");
const resultLine = document.getElementById("resultLine");
const evidenceRun = document.getElementById("evidenceRun");
const evidenceTools = document.getElementById("evidenceTools");
const stepsMetric = document.getElementById("stepsMetric");
const testsMetric = document.getElementById("testsMetric");
const memoryMetric = document.getElementById("memoryMetric");
const providerBox = document.getElementById("providerBox");
const baseUrlEl = document.getElementById("baseUrl");
const modelNameEl = document.getElementById("modelName");
const apiKeyEl = document.getElementById("apiKey");

const taskSamples = {
  nqueens: "Create a Python solution for the N-Queens problem. Implement solve_n_queens(n) in n_queens.py, add pytest tests for n=1, n=4 and n=5, and run the tests locally.",
  text: "Create text_tools.py with normalize_words(text). It should return sorted unique lowercase alphanumeric tokens. Add pytest tests for empty input, punctuation, repeated words and numbers, then run them locally.",
  fizzbuzz: "Create fizzbuzz.py with fizzbuzz(n). It should return the FizzBuzz sequence from 1 to n and [] for n <= 0. Add pytest tests for edge cases and n=15, then run them locally.",
};

const flow = [
  ["Task", "用户任务进入 Agent.run"],
  ["Model", "模型返回一个 JSON action"],
  ["Tool", "本地工具读写文件或执行命令"],
  ["Observation", "工具结果回填上下文"],
  ["Final", "验证后结束并写入项目记忆"],
];
const runHistory = [];

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

function renderToolCalls(items) {
  if (!items.length) {
    toolCallsEl.textContent = "没有工具调用。";
    toolRunLabel.textContent = "0 calls";
    return;
  }
  toolRunLabel.textContent = `${items.length} calls`;
  toolCallsEl.innerHTML = items.map((item) => `
    <article class="tool-call">
      <div class="tool-top">
        <strong>${item.tool}</strong>
        <span>step ${item.step}</span>
      </div>
      <p>${item.summary}</p>
      <div class="tool-args">
        <span>输入参数</span>
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
    modelNameEl.value = data.deepseek_model || "deepseek-v4-flash";
    if (data.deepseek_configured) {
      apiKeyEl.placeholder = "已检测到环境变量，可留空";
      resultLine.textContent = "已检测到 DeepSeek 配置：可以直接点击开始运行。";
    }
  } catch {
    // The demo can still run offline.
  }
}

async function runDemo() {
  const count = Math.max(1, Math.min(Number(runCountEl.value || 1), 3));
  runBtn.disabled = true;
  for (let i = 1; i <= count; i += 1) {
    try {
      await runOnce(count > 1 ? i : null, true);
    } catch {
      break;
    }
  }
  runBtn.disabled = false;
}

async function runOnce(batchIndex = null, propagateError = false) {
  runBtn.disabled = true;
  const prefix = batchIndex ? `第 ${batchIndex} 次` : "正在";
  setStatus("running", `${prefix}运行`);
  renderFlow(1, 0);
  transcriptEl.textContent = "后端正在重置演示工作区并运行 Agent...";
  answerView.textContent = "等待 final";
  testSummary.textContent = "pytest 尚未执行。";
  fileSummary.textContent = "文件变化尚未返回。";
  codeView.textContent = "等待生成";
  diffView.textContent = "等待 diff";
  testView.textContent = "等待测试";
  testFileView.textContent = "等待读取";
  memoryView.textContent = "等待写入";
  toolCallsEl.textContent = "等待本地工具调用";
  toolRunLabel.textContent = "running";
  workspacePath.textContent = "workspace: 后端正在创建演示工作区";
  resultLine.textContent = "运行中：等待模型返回 JSON action。";
  evidenceRun.textContent = "正在创建独立 workspace。";
  evidenceTools.textContent = "工具轨迹尚未返回。";
  stepsMetric.textContent = "0";
  testsMetric.textContent = "-";
  memoryMetric.textContent = "-";
  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        task: taskEl.value,
        template: "scratch",
        mode: "deepseek",
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
    answerView.textContent = data.answer || "(no final answer)";
    codeFileLabel.textContent = data.primary_file || "source file";
    testFileLabel.textContent = data.test_file || "test file";
    codeView.textContent = data.files.source || "(missing)";
    diffView.textContent = data.file_diff || "(no diff)";
    testView.textContent = data.test_output || "(no test output)";
    testFileView.textContent = data.files.test || "(missing)";
    memoryView.textContent = data.memory || "(no memory generated)";
    stepsMetric.textContent = String(data.steps);
    testsMetric.textContent = data.tests_passed ? "pass" : "check";
    memoryMetric.textContent = data.memory_recorded ? "yes" : "no";
    addHistory(data);
    const tools = (data.tool_calls || []).map((item) => item.tool).join(" -> ");
    const changedFiles = (data.changed_files || []).join(", ");
    const changedPaths = (data.changed_file_paths || []).join("\n");
    resultLine.textContent = `完成：run ${data.run_id || "-"} / ${data.model || "-"} / ${data.duration_ms || 0} ms / ${data.tests_passed ? "tests passed" : "tests need check"}`;
    evidenceRun.textContent = `本次 run id 是 ${data.run_id || "-"}，workspace 是 ${data.workspace || "unknown"}。`;
    evidenceTools.textContent = `工具轨迹：${tools || "无"}`;
    fileSummary.textContent = changedFiles
      ? `${changedFiles}\n\n位置：\n${changedPaths}`
      : "没有检测到文件变化。";
    testSummary.textContent = data.tests_passed
      ? `测试通过：${compactTestOutput(data.test_output)}`
      : `测试未通过：${compactTestOutput(data.test_output)}`;
    setStatus("done", "运行完成");
    return data;
  } catch (error) {
    renderFlow(0, 0);
    transcriptEl.textContent = error.message;
    resultLine.textContent = error.message;
    toolRunLabel.textContent = "failed";
    setStatus("error", "运行失败");
    if (propagateError) throw error;
    return null;
  } finally {
    if (!batchIndex) runBtn.disabled = false;
  }
}

function compactTestOutput(output) {
  const lines = String(output || "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const passedLine = [...lines].reverse().map((line) => {
    const match = line.match(/(\d+\s+passed(?:\s+in\s+[\d.]+s)?)/);
    return match ? match[1] : "";
  }).find(Boolean);
  const exitLine = lines.find((line) => line.startsWith("exit_code="));
  return [exitLine, passedLine].filter(Boolean).join(" / ") || "没有测试输出";
}

function addHistory(data) {
  runHistory.unshift({
    run_id: data.run_id,
    model: data.model,
    mode: "deepseek",
    duration_ms: data.duration_ms,
    steps: data.steps,
    tests_passed: data.tests_passed,
    tools: (data.tool_calls || []).map((item) => item.tool),
  });
  if (runHistory.length > 8) runHistory.pop();
  historyView.innerHTML = runHistory.map((item, index) => `
    <article class="history-item ${item.tests_passed ? "ok" : "warn"}">
      <div>
        <strong>#${runHistory.length - index} ${escapeHtml(item.model)}</strong>
        <p>${escapeHtml(item.mode)} · ${item.steps} steps · ${item.duration_ms} ms</p>
      </div>
      <span>${item.tests_passed ? "pass" : "check"}</span>
      <code>${escapeHtml(item.tools.join(" -> "))}</code>
    </article>
  `).join("");
}

renderFlow();
loadConfig();
document.querySelectorAll(".sample-chip").forEach((button) => {
  button.addEventListener("click", () => {
    const key = button.dataset.sample;
    taskEl.value = taskSamples[key] || taskSamples.nqueens;
    document.querySelectorAll(".sample-chip").forEach((item) => item.classList.toggle("active", item === button));
  });
});
runBtn.addEventListener("click", runDemo);
