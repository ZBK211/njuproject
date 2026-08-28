const runBtn = document.getElementById("runBtn");
const statusEl = document.getElementById("status");
const taskEl = document.getElementById("task");
const flowEl = document.getElementById("flow");
const transcriptEl = document.getElementById("transcript");
const codeView = document.getElementById("codeView");
const testView = document.getElementById("testView");
const memoryView = document.getElementById("memoryView");
const auditGrid = document.getElementById("auditGrid");
const stepsMetric = document.getElementById("stepsMetric");
const testsMetric = document.getElementById("testsMetric");
const memoryMetric = document.getElementById("memoryMetric");

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

async function runDemo() {
  runBtn.disabled = true;
  setStatus("running", "正在运行");
  renderFlow(1, 0);
  transcriptEl.textContent = "后端正在重置演示工作区并运行 Agent...";
  codeView.textContent = "等待生成";
  testView.textContent = "等待测试";
  memoryView.textContent = "等待写入";
  stepsMetric.textContent = "0";
  testsMetric.textContent = "-";
  memoryMetric.textContent = "-";
  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({task: taskEl.value}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "demo failed");
    renderFlow(0, 5);
    renderTranscript(data.transcript);
    codeView.textContent = data.files.fizzbuzz || "(missing)";
    testView.textContent = data.test_output || "(no test output)";
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
runBtn.addEventListener("click", runDemo);
