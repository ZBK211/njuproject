Git仓库地址：待创建公开仓库后填写（不要填写个人姓名、学校等身份信息）。

运行方式：Windows 下执行 `python -m venv .venv`、`.venv\\Scripts\\Activate.ps1`、`python -m pip install -r requirements.txt`，再执行 `python -m pytest -q`。无需 API Key 即可执行 `python scripts/run_demo.py` 观看离线全链路演示。接入模型时设置 OPENAI_API_KEY、OPENAI_BASE_URL、OPENAI_MODEL 后执行 `python -m coding_agent "任务" --root 工作区`。

特色功能：手写 Agent 循环和 JSON 动作协议；工具定义、注册、分发与本地执行；读写/编辑/搜索文件；工作区路径隔离；命令超时、输出截断和危险命令拦截；模型输出解析失败自动反馈；上下文超限压缩；步数上限终止；本地项目记忆（memory_record/memory_read、BM25 检索、Hot Memory 注入、自动收尾记录）；可替换的 OpenAI 兼容模型适配器；无网络 FakeModel 测试覆盖工具、解析、错误恢复和终止条件。项目不依赖任何现成 Agent 框架，也不使用服务端代码执行或文件工具。

演示任务：智能体读取任务工作区，发现待实现的 FizzBuzz 函数，写入实现并运行 pytest 验证，最后汇报结果。提交视频应由本人录制，2 分钟以内、MP4、不超过 200MB；视频与本文件一起压缩提交。
