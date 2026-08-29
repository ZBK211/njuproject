# 合规审查

## 结论

当前 ForgeAgent 主体满足题目要求：它是一个独立 coding agent，已经用 `deepseek-v4-flash` 跑通真实模型链路，实现了模型交互、动作解析、本地工具执行、上下文管理、错误处理和循环终止。运行时未使用任何禁止的 Agent 框架，也未使用服务端托管的代码执行或文件工具。

## 逐项核对

符合：

- 独立实现 coding agent：核心在 `coding_agent/agent.py`，DeepSeek V4 只作为模型后端，不接管工具执行。
- 可自主读写文件：`coding_agent/tools/filesystem.py`。
- 可执行命令：`coding_agent/tools/shell.py`，带超时、输出截断和危险命令拦截。
- 模型输出解析：`coding_agent/parser.py` 支持 JSON 和 json 代码围栏。
- 上下文管理：`Agent._compact()` 在字符预算超限后保留头部和最近轨迹。
- 循环终止：final、模型错误、连续解析失败、最大步数都会终止。
- API Key 安全：`coding_agent/config.py` 只读环境变量；网页 demo 只接受运行时密码框输入，不把密钥写入仓库。
- 无 Agent 框架依赖：`requirements.txt` 只有 pytest 测试依赖；运行时使用 Python 标准库。
- 无服务端代码工具：所有文件和 shell 操作都在本地 workspace 执行。
- DeepSeek V4 验证：`scripts/run_deepseek_demo.py` 默认使用 `deepseek-v4-flash`，已实际跑通 `list_dir/read_file/edit_file/run_command/final`。
- 自动合规检查：`scripts/audit_assignment.py` 检查 README 长度、远端仓库、核心文件、禁止框架依赖、疑似密钥、DeepSeek V4 默认值和 pytest。

注意：

- 真实模型调用会使用当前 shell 的 `DEEPSEEK_API_KEY`。只检查是否设置，不打印、不落盘。
- `tmp/dsh-memoir` 是参考仓库，已被 `.gitignore` 忽略。
- `D:/浙大实习/GenericAgent-full-unzip/GenericAgent-main` 是外部参考目录，不会进入本项目仓库。
- 最终视频需要本人录制并避免出现 API Key；脚本只能辅助检查和打包。

## 按题目原文逐条核对

1. 个人独立设计并实现 coding agent：满足。主体代码在 `coding_agent/`，不是在现成 agent 产品外封装界面。
2. 通过大语言模型交互：满足。`OpenAICompatibleModel` 走 Chat Completions；真实路径已接入 DeepSeek V4。
3. 自主读写文件、执行命令：满足。文件工具、编辑工具、搜索工具、命令工具均由 `ToolRegistry` 本地分发。
4. 不使用 Agent 框架/SDK：满足。源码和依赖中没有 LangChain、LlamaIndex、OpenAI Agents SDK、Claude Agent SDK、AutoGen、CrewAI。
5. 不依赖服务端托管代码执行或文件工具：满足。没有使用 Code Interpreter、Files API；pytest 在本机工作区执行。
6. 重要逻辑自行编写：满足。对话历史、上下文压缩、工具定义、本地执行、模型输出解析、终止条件、错误处理都在仓库内实现。
7. 模型、语言不限：满足。Python 实现，模型默认 DeepSeek V4。
8. API key 不进仓库、README.txt、视频：仓库与 README 已检查通过；视频录制时仍需避开密码框和终端环境变量。
9. Git 仓库：满足。公开仓库地址已写入 `README.txt`，当前远端为 `https://github.com/ZBK211/njuproject`。
10. README.txt 1000 字以内：满足。当前 794 字，脚本会自动检查。
11. 视频 2 分钟以内、mp4、小于 200MB：待你录制。`docs/submission.md` 已给出脚本和节奏。
12. 最终 zip 只包含 README.txt 和视频：待录制完成后用 `scripts/prepare_submission.py --video ... --name ...` 生成。

## 与参考项目的关系

GenericAgent 很接近题目要求，但它是一个更大的 Agent 平台，包含真实浏览器、IM 前端、桌面端、SOP、插件、可选 UI 依赖等。直接搬完整项目会带来两个问题：一是项目主体不够聚焦，二是答辩时很难在短时间内解释每条链路。

本项目采用更稳的路线：保留 ForgeAgent 的小核心，把 GenericAgent 的“极简循环、原子工具、可视化演示、自我沉淀”这些思想吸收进来。这样既能说明设计思考，也能把关键代码讲清楚。
