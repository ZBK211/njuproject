# 效果展示

## 同学仓库是否拉取

已经拉取到本地：

```text
C:\Users\MR\Desktop\南软实训\tmp\dsh-memoir
```

该目录已被 `.gitignore` 忽略，只作为参考分析使用，不会进入最终公开仓库。

## 能否直接使用 dsh-memoir

不能把它直接当本次项目主体交，因为它是 DeepSeek Harness 的项目记忆插件，不是独立 coding agent。它的优势是“记忆层”，不是“代码智能体主循环”。题目核心要求的模型动作协议、工具定义、本地执行、循环终止、错误处理，仍然要由我们的项目自己实现。

可以复用的部分已经迁移进 ForgeAgent：

- 本地项目记忆：`.agent/memory.json`
- 可读记忆投影：`.agent/PROJECT_MEMORY.md`
- `memory_record` / `memory_read` 工具
- 中文、英文、代码标识符分词
- BM25 排序召回
- Hot Memory 有界注入
- 完成任务后自动记录本轮工作摘要

## 当前全链路效果

DeepSeek V4 网页 demo 截图：

![DeepSeek V4 本地工具调用演示](../web_demo/assets/demo-deepseek-v4.png)

真实模型运行：

```powershell
python scripts\run_deepseek_demo.py
```

实际链路：

1. DeepSeek V4 输出 `list_dir`，查看工作区。
2. 输出 `read_file`，读取待实现代码。
3. 输出 `read_file`，读取测试约束。
4. 输出 `edit_file`，精确替换 `fizzbuzz.py`。
5. 输出 `run_command`，执行 `python -m pytest test_fizzbuzz.py -q`。
6. 测试通过后输出 final。
7. 自动生成项目记忆。

实际输出关键部分：

```text
MODEL: deepseek-v4-flash
[MODEL 1] {"kind":"tool","tool":"list_dir","arguments":{"path":"."}}
[TOOL 5] run_command: exit_code=0
..                                                                       [100%]
2 passed in 0.01s

RESULT: completed; steps=6
Implemented `fizzbuzz(n)` ... Verified by running `python -m pytest test_fizzbuzz.py -q`.
```

离线回归运行：

```powershell
python scripts\run_demo.py
```

会看到固定 DemoModel 完成同一类链路，适合没有网络时回归：

1. `list_dir` 查看工作区。
2. `read_file` 读取待实现代码。
3. `write_file` 写入 `fizzbuzz(n)`。
4. `run_command` 执行 `python -m pytest -q`。
5. 测试通过后返回 final。
6. 自动生成项目记忆。

离线输出关键部分：

```text
[TOOL 4] run_command: exit_code=0
..                                                                       [100%]
2 passed

RESULT: completed; steps=5
Implemented fizzbuzz(n) and verified it with pytest.

PROJECT MEMORY
# Project Memory

## Work Log

- Agent run completed - Completed run using tools: list_dir, read_file, write_file, run_command.
```

## 当前测试状态

运行：

```powershell
python -m pytest -q
```

当前结果：

```text
21 passed
```

测试覆盖：

- JSON 动作解析和错误恢复
- 工作区路径隔离
- 文件读写、编辑、搜索
- shell 返回码、超时和危险命令拦截
- Agent 步数上限和上下文压缩
- OpenAI-compatible HTTP 客户端 mock
- 项目记忆记录、检索、重复检测和 Hot Memory 预算

## 网页 demo 真实执行证据

运行：

```powershell
python scripts\demo_server.py
```

打开 `http://127.0.0.1:8787` 后点击“运行一次”，页面会展示：

- 本次演示 workspace 的绝对路径。
- `list_dir`、`read_file`、`write_file`、`run_command` 的工具调用顺序。
- 每个工具调用的 JSON 参数和本地执行输出。
- 连续运行历史，可用 3 次真实模型运行检查稳定性。
- `fizzbuzz.py` 从 `NotImplementedError` 到完整实现的 unified diff。
- `python -m pytest -q` 的真实输出。
- 自动生成的 `.agent/PROJECT_MEMORY.md`。

页面可在“本地工具链路演示”和“DeepSeek 实时模型”之间切换。模型输入框可填 `deepseek-v4-flash` 或 `deepseek-v4-pro`；录制时优先展示 DeepSeek 实时模型。API Key 只在运行时输入或从环境变量读取，不进入仓库。

## 题目合规自检

运行：

```powershell
python scripts\audit_assignment.py
```

当前结果：

```text
[OK] README.txt exists and is <= 1000 chars
[OK] Git remote is configured
[OK] Core agent files exist
[OK] No forbidden agent framework dependency/import in runtime code
[OK] No obvious API key committed
[OK] DeepSeek demo defaults to V4
[OK] Tests pass
```
