# 录屏操作指南

## 为什么需要你本人录制

题目要求视频演示 agent 完成真实编程任务，并简要讲解功能实现。项目和脚本我已经准备好，但最终视频建议由你本人录制：一是需要你的口头说明，二是录屏时不能出现 API Key，三是最终提交文件需要用你的姓名命名。

## 录制前准备

1. 打开 PowerShell，进入项目目录：

```powershell
cd C:\Users\MR\Desktop\南软实训
```

2. 确认环境变量已经设置。不要把密钥输在会被录进去的位置；如果已经在系统环境变量里设置好，直接跳过：

```powershell
$env:DEEPSEEK_API_KEY.Length
```

只展示长度，不展示值。

3. 启动网页 demo：

```powershell
python scripts\demo_server.py
```

另开一个 PowerShell 窗口用于运行检查命令。

## 推荐录屏工具

Windows 自带 Xbox Game Bar：

1. 按 `Win + G`。
2. 点击“捕获”里的录制按钮。
3. 打开麦克风。
4. 录完后在“视频/捕获”目录找到 mp4。

如果 Game Bar 不能录桌面，可以用 PowerPoint 录屏：

1. 插入 -> 屏幕录制。
2. 选择 PowerShell 和浏览器区域。
3. 录完导出为 mp4。

## 2 分钟流程

0:00-0:15：展示项目目录、`README.txt` 和 GitHub 地址。

0:15-0:35：打开 `coding_agent/agent.py`，讲一句：模型每轮只返回一个 JSON action，主循环解析后调用本地工具，再把观察结果放回上下文。

0:35-0:50：运行：

```powershell
python scripts\audit_assignment.py
```

说一句：这个脚本检查 README 长度、远端仓库、核心文件、禁止框架、密钥泄漏、DeepSeek V4 默认值和测试。

0:50-1:20：运行：

```powershell
python scripts\run_deepseek_demo.py
```

保留画面里的 `MODEL: deepseek-v4-flash`、工具调用和 pytest 通过结果。

1:20-1:50：打开 `http://127.0.0.1:8787`，选择 “DeepSeek 实时模型”，确认模型输入框是 `deepseek-v4-flash`。点击“运行一次”；如果时间够，点“连续运行 3 次”展示稳定性。重点展示工具参数、运行历史、代码 diff、pytest 输出和项目记忆。

1:50-2:00：总结：没有使用 Agent 框架，没有使用云端代码执行或 Files API，文件和命令都在本地 workspace 完成。

## 打包

录制完成后运行：

```powershell
python scripts\prepare_submission.py --video 路径\你的录屏.mp4 --name 你的姓名
```

生成的 zip 在 `submission/` 目录下，里面只包含 `README.txt` 和 mp4。
