Git仓库地址：https://github.com/ZBK211/njuproject

ForgeAgent 是我对 coding agent 最小闭环的一次实现：模型不直接“说自己改好了”，而是每轮只能输出一个 JSON 动作；主循环解析动作，调用本地工具，再把观察结果放回上下文，直到测试通过或触发明确终止条件。项目没有使用 LangChain、LlamaIndex、OpenAI Agents SDK、AutoGen、CrewAI，也没有使用服务端代码执行或文件工具。

我重点做了三层设计。第一层是执行边界：文件路径必须留在工作区内，shell 命令有超时、输出截断和危险命令拦截，API Key 只从环境变量或运行时密码框读取。第二层是可解释循环：上下文压缩、解析失败重试、模型错误返回、最大步数停止都在代码里显式实现。第三层是项目记忆：参考 GenericAgent 和 dsh-memoir 的思路，用本地 `.agent/memory.json` 记录工作结论，生成可读的 `PROJECT_MEMORY.md`，并用中文/英文/代码标识符分词和 BM25 检索做 Hot Memory 注入。

运行：`python -m pytest -q`。真实模型演示：设置 `DEEPSEEK_API_KEY` 后运行 `python scripts/run_deepseek_demo.py`，默认模型为 `deepseek-v4-flash`，也可加 `--template text_tools` 换任务。可视化演示：`python scripts/demo_server.py` 后打开 `http://127.0.0.1:8787`，切到 DeepSeek 实时模型，页面会展示本地工具调用参数、代码 diff、pytest 输出和记忆文件。合规自检：`python scripts/audit_assignment.py`。
