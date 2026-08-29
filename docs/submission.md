# 提交清单

## 三项提交物

1. 公开 Git 仓库：提交完整项目代码。创建仓库后，把公开 URL 填到 `README.txt` 第一行。
2. `README.txt`：控制在 1000 字以内，不写姓名、学校、API Key 等身份信息。
3. MP4 演示视频：2 分钟以内、200MB 以内。视频由本人录制，最终与 `README.txt` 打包提交。

## 录屏建议

录制前先打开一个干净终端，进入项目目录：

```powershell
cd C:\Users\MR\Desktop\南软实训
python -m pytest -q
python scripts/audit_assignment.py
python scripts/run_deepseek_demo.py
python scripts/demo_server.py
```

视频节奏：

0:00-0:15 展示项目目录和 `README.txt`。

0:15-0:35 展示 `coding_agent/agent.py`、`coding_agent/tools/registry.py` 和 `coding_agent/tools/shell.py`，说明核心循环、工具注册和安全执行是自己实现的。

0:35-0:50 运行 `python scripts/audit_assignment.py`，展示 README 长度、禁止框架、密钥、DeepSeek V4 默认值和测试全部通过。

0:50-1:20 运行 `python scripts/run_deepseek_demo.py`，保留 `MODEL: deepseek-v4-flash`、`list_dir/read_file/edit_file/run_command` 和 pytest 通过结果。录屏时不要展示 API Key。

1:20-1:50 打开 `http://127.0.0.1:8787`，切到 “DeepSeek 实时模型”，点击“运行一次”，重点展示网页中的本地工具调用参数、workspace 路径、代码 diff、pytest 输出、项目记忆和合规检查。时间够的话再点“连续运行 3 次”展示稳定性。

1:50-2:00 总结没有使用被禁止的 Agent 框架，也没有使用服务端代码执行或文件工具。

如果担心现场网络波动，可以在视频里展示 `scripts/run_deepseek_demo.py` 已经真实跑通；网页 demo 录制时优先用 DeepSeek 模式，必要时再切回“本地工具链路演示”解释它只用于稳定回归。

## 打包检查

只检查 `README.txt`：

```powershell
python scripts/prepare_submission.py
```

录好视频后生成 zip：

```powershell
python scripts/prepare_submission.py --video path\to\demo.mp4 --name 你的姓名
```

打包脚本只放入 `README.txt` 和 MP4，不会把源码、缓存或密钥放进提交 zip。
