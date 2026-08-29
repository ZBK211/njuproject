# ForgeAgent 项目导读

## 先抓主线

这个项目可以按一句话理解：DeepSeek V4 只负责“下一步做什么”的决策，ForgeAgent 自己负责“怎么安全地在本地执行、怎么把结果反馈给模型、什么时候结束”。

一次真实运行的顺序是：

1. 用户输入编程任务。
2. `Agent.run()` 组织系统提示、用户任务和项目记忆。
3. `OpenAICompatibleModel` 调用 `deepseek-v4-flash` 或 `deepseek-v4-pro`。
4. 模型返回一个 JSON action。
5. `parser.py` 解析 action。
6. `ToolRegistry` 找到工具并在本地 workspace 执行。
7. 工具 observation 回到上下文。
8. 模型继续下一轮，直到运行测试并返回 final。
9. Agent 把本轮结果写入项目记忆。

## 核心文件地图

`coding_agent/agent.py`

项目最核心的文件。重点看 `Agent.run()`：它保存消息历史，调用模型，解析 JSON action，执行工具，把 observation 放回上下文，并处理 final、错误和步数上限。老师如果问“你的 agent 为什么能运转”，主要讲这个文件。

`coding_agent/prompts/system.md`

给模型的协议说明。它要求模型每次只返回一个 JSON 对象，要么是 tool action，要么是 final answer。它还要求模型读文件后再编辑，修改后跑测试，不允许凭空说成功。

`coding_agent/parser.py`

模型输出解析器。它支持纯 JSON 和 ```json 代码块，解析失败会抛出 `ActionParseError`。这个文件对应题目里的“模型输出的解析”和“错误处理”。

`coding_agent/llm.py`

OpenAI-compatible Chat Completions 客户端。它只做普通 HTTP 请求，不使用 Agent SDK，也不调用服务端文件或代码执行工具。

`coding_agent/config.py`

环境变量配置。普通 OpenAI-compatible 路径读 `OPENAI_*`，DeepSeek V4 路径读 `DEEPSEEK_*`。默认 DeepSeek 模型是 `deepseek-v4-flash`。

`coding_agent/tools/registry.py`

工具注册和分发中心。每个工具都有名称、描述、参数 schema 和 handler。模型只能通过这里暴露出来的工具做事。

`coding_agent/tools/filesystem.py`

本地文件工具：`list_dir`、`read_file`、`write_file`、`edit_file`、`search`。重点是 `_safe_path()`：任何路径都必须 resolve 后仍在 workspace 内。

`coding_agent/tools/shell.py`

本地命令工具：`run_command`。它使用 subprocess 在 workspace 中执行命令，有超时、输出截断和 UTF-8 输出处理。

`coding_agent/tools/safety.py`

危险命令拦截。比如递归强删、`git reset --hard`、格式化磁盘、关机等会被拒绝。

`coding_agent/memory.py`

项目记忆层。完成任务后记录工作摘要，生成 `.agent/PROJECT_MEMORY.md`，并用 BM25 检索相关记忆作为 Hot Memory。

`scripts/run_deepseek_demo.py`

真实模型命令行演示。默认调用 `deepseek-v4-flash`，让模型自己选择本地工具完成 FizzBuzz 任务并跑 pytest。

`scripts/demo_server.py`

网页 demo 后端。每次运行都会创建独立 workspace，避免多次演示互相覆盖。它把 transcript、工具调用、代码 diff、测试输出和项目记忆返回给前端。

`web_demo/`

可视化运行台。你可以输入编程任务、把模型名改成 `deepseek-v4-flash` 或 `deepseek-v4-pro`、点击运行、连续运行 3 次，并查看每次工具调用的参数和结果。

`scripts/audit_assignment.py`

题目合规自检脚本。它检查 README 长度、仓库地址、核心文件、禁止 Agent 框架、疑似密钥、DeepSeek V4 默认值和测试结果。

`scripts/prepare_submission.py`

最终打包脚本。录好视频后，用它生成只包含 `README.txt` 和 mp4 的 zip。

## 演示时怎么一步步跑通

1. 进入项目目录：

```powershell
cd C:\Users\MR\Desktop\南软实训
```

2. 合规自检：

```powershell
python scripts\audit_assignment.py
```

3. 真实模型链路：

```powershell
python scripts\run_deepseek_demo.py
```

重点看输出里的：

```text
MODEL: deepseek-v4-flash
[MODEL 1] {"kind":"tool","tool":"list_dir"...}
[TOOL 5] run_command: exit_code=0
2 passed
RESULT: completed
```

4. 网页展示：

```powershell
python scripts\demo_server.py
```

打开 `http://127.0.0.1:8787`，选择 “DeepSeek 实时模型”，点击“运行一次”。如果想证明稳定性，点“连续运行 3 次”。

网页连续运行时，每一轮都会创建独立目录 `demo_workspace/web_runs/<run_id>`，不会和命令行演示互相覆盖。

## 关于 deepseek-v4-pro

可以切换。网页上直接把模型输入框改成 `deepseek-v4-pro` 即可；命令行里可以这样设：

```powershell
$env:DEEPSEEK_MODEL = "deepseek-v4-pro"
python scripts\run_deepseek_demo.py
```

`v4-flash` 更适合录屏，因为响应快；`v4-pro` 可作为更强模型展示，但延迟和成本通常更高。

## 关于“能不能打开 QQ”

这个项目定位是 coding agent，不是桌面控制 agent。它暴露给模型的是本地文件工具和 shell 工具，所以理论上如果系统里有可执行命令，模型可能通过 `run_command` 尝试启动某个程序。但这不是本题应该展示的能力，也不建议把 QQ 这类桌面应用作为演示任务。

更准确的回答是：ForgeAgent 的能力边界是“在指定 workspace 内完成编程任务”。它可以读写文件、搜索代码、运行测试、执行构建命令；对非编程、非 workspace 的系统操作，需要审批和更严格的安全策略。

## 老师最可能追问的代码点

1. `Agent.run()`：模型、工具、observation 是怎么串起来的？
2. `parse_action()`：模型输出不合法怎么办？
3. `_safe_path()`：怎么保证不能读写 workspace 外的文件？
4. `CommandSafetyPolicy`：危险命令怎么拦截？
5. `OpenAICompatibleModel`：为什么这不算使用 Agent SDK？
6. `ProjectMemoryStore`：项目记忆如何写入、检索和注入？
7. `audit_assignment.py`：如何证明没有违反题目约束？
8. `demo_server.py`：网页展示的数据是不是后端真实执行生成的？
