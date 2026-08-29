# 面试准备

## 60 秒中文介绍

我做的项目叫 ForgeAgent，是一个面向本地代码仓库的 coding agent。它没有套 LangChain、AutoGen 这类 Agent 框架，而是自己实现了一个可解释的主循环：模型每轮只能返回一个 JSON action，主循环解析 action 后调用本地工具，再把工具观察结果放回上下文，直到测试通过、模型报错、解析连续失败或达到步数上限。

我重点考虑了三个问题。第一是执行边界，文件路径必须留在 workspace 内，shell 命令有超时、输出截断和危险命令拦截；第二是可观测性，网页 demo 会展示 DeepSeek V4 的工具调用参数、真实 diff、pytest 输出和项目记忆，而不是只展示一段终端结果；第三是长期上下文，参考 GenericAgent 和 dsh-memoir 的思路，我做了本地项目记忆，把完成过的工作沉淀到 `.agent/memory.json` 和 `PROJECT_MEMORY.md`，下次运行时只注入预算内的 Hot Memory。

目前真实模型链路已经用 `deepseek-v4-flash` 跑通：它会自己选择 `list_dir`、`read_file`、`edit_file`、`run_command`，最后通过 pytest。我的目标不是做一个大而全的平台，而是把题目要求的核心机制做清楚、跑通、可测试，并且答辩时能解释每一步为什么这样设计。

## One-Minute Personal English Introduction

Hello professors, my name is [your name]. I am an undergraduate student interested in software engineering, developer tools, and intelligent systems. In my recent projects, I have been trying to understand not only how to use large language models, but also how to build reliable software around them.

For this assessment, I built ForgeAgent, a small but complete coding agent for local workspaces. It connects to DeepSeek V4 through an OpenAI-compatible API, asks the model for one JSON action at a time, executes local file and shell tools, and feeds the observation back into the next round. I also added workspace isolation, command timeouts, error recovery, automated tests, and a web demo that shows the real tool calls and pytest results.

What I learned most from this project is that an agent is not just a model call. The important part is the engineering loop around the model: how to define tools, control side effects, recover from bad outputs, and decide when the task is actually finished.

## 2 分钟视频稿

0:00-0:15：打开项目目录和 `README.txt`，说明仓库地址、运行方式和项目目标。强调这是题目发布后新建的公开仓库。

0:15-0:35：打开 `coding_agent/agent.py`、`coding_agent/tools/registry.py`、`coding_agent/tools/shell.py`。讲清楚主循环、工具注册、本地执行、路径隔离和命令安全。

0:35-0:50：运行 `python scripts/audit_assignment.py`，展示 README 长度、禁止框架、密钥检查、DeepSeek V4 默认值和测试均通过。

0:50-1:20：运行 `python scripts/run_deepseek_demo.py`。画面保留 `MODEL: deepseek-v4-flash`，以及 `list_dir/read_file/edit_file/run_command` 和 pytest 通过。不要展示 API Key。

1:20-1:50：打开 `http://127.0.0.1:8787`，切到 DeepSeek 实时模型并运行。展示工具调用参数、运行历史、workspace 路径、代码 diff、pytest 输出、项目记忆和合规检查。

1:50-2:00：总结：关键逻辑由项目自行实现，模型只是决策后端；文件和命令都在本地执行，没有使用服务端 Code Interpreter 或 Files API。

## 高频问题与回答

### 1. 你这个 Agent 的核心状态机是什么？

状态机很简单：准备系统提示和用户任务；调用模型得到一个 JSON action；解析 action；如果是 tool，就执行本地工具并把 observation 放回消息；如果是 final，就记录项目记忆并结束。异常路径包括模型请求失败、JSON 连续解析失败和最大步数耗尽。

### 2. 为什么不用模型原生 tool calling？

题目允许使用原生 tool calling，但我这里选择纯 JSON 协议，是为了把解析、错误恢复和工具分发都显式写出来，更方便评审看到核心逻辑。将来要迁移到原生 tool calling，只需要替换模型适配层，`ToolRegistry` 和本地执行器可以保持不变。

### 3. 如何证明接入了真实 DeepSeek V4？

`scripts/run_deepseek_demo.py` 默认模型是 `deepseek-v4-flash`，运行时会打印模型名，并展示真实模型生成的 action。当前跑通过的链路是 `list_dir -> read_file -> read_file -> edit_file -> run_command -> final`，不是固定 DemoModel 的输出。

### 4. 离线 DemoModel 是不是让项目变成玩具？

不是。真实展示主线是 DeepSeek V4。DemoModel 的作用是回归测试和断网时复现，它让测试能稳定覆盖主循环、工具执行和记忆记录，不替代真实模型能力。

### 5. 文件读写怎么防越界？

所有路径都先与 workspace 根目录拼接并 `resolve()`，再检查解析后的路径仍然位于根目录内。比如 `../secret.txt` 会被拒绝，不会进入真实文件操作。

### 6. 命令执行有什么安全边界？

命令通过本地 subprocess 执行，有超时、输出截断和危险命令拦截。CLI 默认还会询问是否批准命令；demo 中只在临时 workspace 里自动批准，用于稳定展示。

### 7. 模型输出非法 JSON 怎么办？

解析失败时不会崩溃，也不会猜测模型意图，而是把明确的错误 observation 放回上下文，请模型重新输出一个合法 action。连续三次失败就终止，避免无限循环。

### 8. 如何判断任务完成？

模型必须显式输出 final action，但项目不会只相信“我完成了”。系统提示要求修改后运行最小必要验证；demo 中必须看到 pytest 通过，才进入 final。

### 9. 上下文压缩为什么这样做？

当前实现采用保守策略：保留系统提示、原始任务和最近轨迹，把早期内容替换成压缩标记。这样能先保证上下文不会无限增长。后续可以把压缩标记升级成模型生成摘要或 token 级预算。

### 10. 项目记忆解决什么问题？

它解决跨会话遗忘。Agent 完成一次真实工具任务后，会记录“做了什么、用了哪些工具、结果是什么”，并生成可读的 `PROJECT_MEMORY.md`。下一轮只注入预算内的相关记忆，避免把历史全塞进上下文。

### 11. 和 GenericAgent、dsh-memoir 的关系是什么？

GenericAgent 更像完整平台，dsh-memoir 是 DSH 的项目记忆插件。我的项目没有直接把它们作为主体提交，而是吸收了可解释循环、原子工具、项目记忆和可视化展示这些思路。ForgeAgent 的主循环、解析器、工具执行和终止条件都是本仓库实现的。

### 12. 这个项目最大的不足是什么？

目前还没有完整审批 UI、增量 patch 视图、并发工具调用和 token 精确计费。我的取舍是先把题目要求的核心闭环做扎实：真实模型能驱动本地工具完成任务，链路可观察，失败可解释，测试可重复。
