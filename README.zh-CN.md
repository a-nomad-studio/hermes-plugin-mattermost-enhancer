# Hermes Mattermost Enhancer Plugin

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Hermes](https://img.shields.io/badge/Hermes-%E2%89%A5%20v0.23-blue)](https://github.com/nousresearch/hermes-agent)
[![Release](https://img.shields.io/github/v/release/a-nomad-studio/hermes-plugin-mattermost-enhancer?label=release)](https://github.com/a-nomad-studio/hermes-plugin-mattermost-enhancer/releases)

[English Version](./README.md) | 中文版本

让你的 Hermes AI 助手在 Mattermost 里变得更聪明、更安全、更好用。

---

## 💡 这是什么？

**一句话介绍：** 如果你正在通过 Mattermost 团队聊天使用 Hermes AI 助手，这个插件能为你补齐所有原生缺失的交互能力。

原版 Hermes 在终端或网页里功能强大，但在 Mattermost 聊天流中缺少许多便捷交互——比如无法直接切换模型、遇到危险操作没有卡片拦截、多步任务容易刷屏、无法像桌面端一样从任意历史消息开辟新分支探索等。

本插件为 Hermes 深度适配了 Mattermost 原生交互界面，让你在手机端或电脑端都能享受丝滑的 AI 交互体验。

---

## ✨ 核心功能（按实用性排序）

### 🧠 1. 随时切换 AI 模型（`/model` 指令与频道继承）

**痛点与改善：**
- **痛点：** 不同的任务需要不同的模型（写代码用专业模型，闲聊用快速轻量模型）。原本想要换模型，必须去修改服务器上的配置文件并重启服务，非常繁琐 💀
- **改善：** 在任意 Thread（对话线）或私聊中输入 `/model`，立刻弹出一张下拉菜单卡片。从菜单中选好模型后，**仅当前 Thread 立即切换**，其他对话线完全不受干扰 ✅

![模型切换选项卡效果](images/model.webp)

> 💡 **频道自动继承特性：**
> 如果你在**频道主聊天窗口**先用 `/model` 选好模型，之后在频道内点击回复创建的任意新 Thread，都会**自动继承**这个模型设置，无需反复手动切换。已有单独设置的 Thread 不会被覆盖。

---

### 🛡️ 2. 危险操作安全确认（私信卡片审批）

**痛点与改善：**
- **痛点：** 当 AI 执行涉及删除文件、修改数据库或敏感命令时，一旦理解偏差就会造成不可逆的破坏，在普通群聊里你甚至来不及打断 😱
- **改善：** 遇到危险操作时，Hermes 会主动向发起者的**私聊窗口发送一张确认卡片**，提供 4 个安全选项：
  - **Allow Once**（仅允许这一次）
  - **Allow This Session**（本次会话内不再询问）
  - **Always Allow**（永久允许该命令）
  - **Deny**（拒绝执行）

![授权选项卡效果](images/approve.webp)

> 🔒 **精准定位发起人：** 即使在多人参与的公共频道中，卡片也只会精准私信给真正发送指令的人，绝不打扰群内其他成员，更不会误发给管理员。

---

### ❓ 3. 方案选择与决策提问（AI 交互式卡片）

**痛点与改善：**
- **痛点：** 当 AI 处理复杂任务需要你做选择时（例如“发现两种实现方案：A 速度更快，B 稳定性更高，请选 1 或 2”），纯文本形式的提问极易被忽略。一旦漏看，AI 就会一直在后台死等直到超时卡住 💀
- **改善：** AI 的提问会自动渲染为**醒目的交互式按钮卡片**。
  - 直接点击选项按钮即可秒速确认，卡片原地更新打勾 ✅
  - 提供「✍️ 其他」按钮，点击后可在聊天框自由输入补充意见
  - 纯开放式问题自动展示清晰的指引文本，直接打字即可回复

![AI 提问交互卡片效果](images/clarify.webp)

---

### 🌿 4. 从任意历史消息分叉新对话（🆕 表情分支）

**痛点与改善：**
- **痛点：** 对话进行到很深时，如果你想回到前面第 3 轮换一个思路探讨，如果清空上下文原讨论就全丢了；如果复制整段历史又太臃肿混乱 💀
- **改善：** 对任意一条历史消息长按或点击添加 🆕（`:new:`）表情，Hermes 会以该消息为分界点，在频道中**自动开辟一个全新的独立 Thread**，完整克隆该节点之前的对话历史，原 Thread 保持原样，两条思路并行探索互不干扰 ✅

| 你给哪条消息点 🆕 | 新分支继承的历史上下文 | 典型使用场景 |
| :--- | :--- | :--- |
| **你自己的提问** | 截取到该提问**之前**的全部历史（不含该提问） | “这个问题我想换种问法”或“换个参数再试一次” |
| **Hermes 的回答** | 包含这条回答在内的**完整对话轮次**（含工具执行结果） | “这个方案很棒，我想基于当前成果深挖另一个方向” |

> 📱 **全平台原生支持：** 手机端长按添加表情、电脑端鼠标悬停点击表情均可触发，无需在 Mattermost 服务器额外安装任何网页端组件。

---

### 🙈 5. 隐藏任务思考与执行过程（`task_progress` 开关）

**痛点与改善：**
- **痛点：** 当 Hermes 执行联网搜索、阅读本地长文件或多步分析时，聊天界面会频繁弹出跳动的中间过程卡片（如 `🔍 Searching the web for ...`、`📖 Reading file ...`）。在日常问答或追求清爽界面的场景下，大量过程消息容易造成视觉干扰和刷屏 💀
- **改善：** 插件拓展了任务过程控制项（默认为 `on`）。将其配置为 `off` 时，彻底隐藏思考推导与文件/网络执行等所有中间步骤，只保留输入中的 Typing 提示，完成后直接送达最终回答，保持对话流干净整洁 ✅

**配置方式（二选一）：**
- **方式 1：环境变量（`~/.hermes/.env`）**
  ```dotenv
  MATTERMOST_TASK_PROGRESS=off
  ```
- **方式 2：配置文件（`~/.hermes/config.yaml`）**
  ```yaml
  mattermost:
    task_progress: off
  ```
  *(修改后重启 Gateway 即可生效)*

---

### 🧠 6. 调整会话推理强度（`/reasoning` 指令）

**痛点与改善：**
- **痛点：** 简单问答不需要模型反复深思熟虑；而疑难代码排查或方案设计又希望模型全力推理。原有系统无法在聊天窗口临时调整思考强度。
- **改善：** 在 Thread 中直接发送指令临时调整思考深度，仅对当前对话生效：
  - `/reasoning low`（快速轻度思考）
  - `/reasoning high`（深入严密推导）
  - `/reasoning none`（关闭思考推导，模型支持时直接输出）
  - `/reasoning`（查看当前对话的思考强度状态）
  - `/reasoning reset`（恢复默认设置）

---

### 🔄 7. 重置当前对话上下文（`/new` 指令）

**痛点与改善：**
- **痛点：** 当前 Thread 讨论偏离了主题，你想在同一个窗口继续聊，但不想让之前的陈旧上下文干扰 AI 思考。
- **改善：** 在 Thread 或私聊窗口中发送 `/new`，点击弹出的确认卡片后，当前窗口即刻开启全新会话，之前的历史不再计入上下文记忆。

![创建会话选项卡效果](images/new.webp)

> 💡 线程模式下，若想探讨全新的主题，直接在频道主时间线发送新消息即可自动开启新 Thread，不需要频繁手动执行 `/new`。

---

### 🗜️ 8. 就地压缩长对话历史（`/compress` / `/compact` 指令）

**痛点与改善：**
- **痛点：** 某个重要任务在 Thread 里聊了数十轮，上下文快要超出模型容量上限，对话变得迟缓且费用倍增。
- **改善：** 输入 `/compress`，AI 会就地把早期的冗长讨论和执行结果提炼浓缩为关键决策摘要，依然在**同一个 Thread** 中继续流畅对话，无需中途搬家换群。

```text
/compress                               # 自动智能压缩
/compress 保留核心架构决定与待办任务清单    # 带有侧重点的个性化压缩
/compress --preview                     # 仅预览压缩计划，不实际修改
```

---

### 🏷️ 9. 显示当前模型与上下文使用率（回复脚注）

**痛点与改善：**
- **痛点：** 同时打开了多个 Thread 讨论不同事项，聊久了容易忘记当前 Thread 使用的是哪个模型。
- **改善：** 开启后，Hermes 的每条回复末尾会自动附带一行灰色等宽小字脚注（如 `── deepseek-v4-pro 34% ──`），一目了然看清当前模型与上下文健康度，不遮挡主体阅读。

![模型脚注效果](images/footer.webp)

> 💡 **启用方法：** 在 `~/.hermes/config.yaml` 的 `display` 节点中添加：
> ```yaml
> display:
>   runtime_footer:
>     enabled: true
>     fields:
>       - model
>       - context_pct
> ```

---

### ⌨️ 10. Thread 内正在输入提示（Typing 指示器）

**痛点与改善：**
- **痛点：** 原版系统的“正在输入...”提示会错误地出现在顶层频道列表中，你在 Thread 里看着界面毫无动静，误以为 AI 已经死机卡死 😕
- **改善：** 修复了状态路由机制，Typing 提示精准出现在当前正在等待的 Thread 底部，让你明确知道 AI 正在认真思考并组织语言 ✅

![Typing 指示器示例效果](images/typing.webp)

---

## 🐛 解决的核心问题与保障

| 类别 | 遇到的问题 | 造成的影响 | 插件带来的改善 |
| :--- | :--- | :--- | :--- |
| **交互控制** | 斜杠命令被 Mattermost 拦截 | 输入 `/model`、`/new` 等指令直接报错，无法在聊天窗口控制 AI | 搭建本地独立回调通道，全套斜杠指令畅通运行 |
| **状态感知** | Typing 提示位置错乱 | Thread 里看不到 AI 状态，频繁误判为服务假死 | 状态指示器精确路由到当前 Thread 底部 |
| **安全隔离** | 多用户群聊审批发错人 | 多人群聊中，普通成员触发危险命令却私信发给管理员 | 依据消息发送者精准路由审批卡片到本人私信 |
| **网络通信** | WebSocket 频繁断线重连 | 遇到网络微小抖动即断开，导致消息吞字或卡顿 | 优化心跳探测机制至 15 秒，连接长期保持稳定 |
| **决策交互** | 提问纯文本混在聊天流中 | AI 的关键分歧点提问容易被漏看，导致任务长期阻塞卡死 | 自动转换为可交互的点击卡片与自由输入框 |
| **会话分叉** | 缺乏局部历史复刻能力 | 无法在保留前置成果的基础上探索不同解法 | 原生支持 🆕 表情一键开辟独立新分支探索 |

---

## 🚀 快速上手（4 步）

### 前提条件
- ✅ 已安装 [Hermes Agent](https://github.com/nousresearch/hermes-agent)（版本 ≥ v0.23.0）
- ✅ 拥有一个可用的 Mattermost 服务器与已配置好的 Bot 账号
- ✅ Python 3.11+ 环境

---

### 第 1 步：安装插件

```bash
hermes plugins install a-nomad-studio/hermes-plugin-mattermost-enhancer --enable
```

---

### 第 2 步：在 Mattermost 中注册自定义 Slash 指令

进入 Mattermost **产品菜单 → 集成 → Slash 指令**，点击添加自定义指令（请求方式选择 **POST**）：

| 触发词（不带斜杠） | 建议显示名称 | 请求 URL（根据实际部署选择） |
| :--- | :--- | :--- |
| `model` | 切换 AI 模型 | `http://<Hermes主机IP>:18065/mm-command` |
| `new` | 重置当前对话 | `http://<Hermes主机IP>:18065/mm-command` |
| `reasoning` | 调整推理强度 | `http://<Hermes主机IP>:18065/mm-command` |
| `compress` | 压缩对话上下文 | `http://<Hermes主机IP>:18065/mm-command` |
| `compact` | 压缩对话上下文 (别名) | `http://<Hermes主机IP>:18065/mm-command` |

> 🔧 **Docker 部署小贴士：** 如果 Mattermost 运行在容器内，Hermes 运行在宿主机上，请求 URL 请统一填写：`http://host.docker.internal:18065/mm-command`。

保存后，复制每条指令生成的 Token。

---

### 第 3 步：配置环境变量

打开 `~/.hermes/.env`，添加以下配置：

```dotenv
# ── 回调服务器（用于接收卡片点击与指令）──
MATTERMOST_CALLBACK_BIND=0.0.0.0
MATTERMOST_CALLBACK_PORT=18065

# ── 回调 URL（Mattermost 服务器访问宿主机的地址）──
# Docker 部署请使用 host.docker.internal：
MATTERMOST_CALLBACK_URL=http://host.docker.internal:18065/mattermost/callback

# ── 安全验证密钥（建议填写 32 位随机字符串，防伪造请求）──
MATTERMOST_CALLBACK_SECRET=replace-with-a-long-random-secret

# ── Slash 指令 Token 校验（将第 2 步复制的 Token 分号隔开填入）──
MATTERMOST_SLASH_COMMAND_TOKENS="model=token1;new=token2;reasoning=token3;compress=token4;compact=token5"

# ── 可选：任务过程展示（默认 on；若需隐藏文件与搜索等执行细节可设为 off）──
# MATTERMOST_TASK_PROGRESS=on

# ── 可选：消息分叉表情（默认 new；填 off 可关闭）──
# MATTERMOST_BRANCH_EMOJI=new
```

---

### 第 4 步：运行配套补充脚本并重启服务

```bash
cd ~/.hermes/plugins/mattermost-enhancer

# 1. 检查配套环境与底层适配状态
./scripts/hermes-mattermost-enhancer.sh check

# 2. 如果提示未应用，执行补充适配
./scripts/hermes-mattermost-enhancer.sh apply

# 3. 在外部终端重启 Hermes Gateway 生效
hermes gateway restart
```

🎉 **配置完成！** 现在回到 Mattermost，试试在 Thread 里发送 `/model` 或者给消息点个 🆕 表情体验吧！

---

## ❓ 常见问题

**Q: 点击卡片按钮或输入 `/model` 没有反应？**
- 检查 `MATTERMOST_CALLBACK_URL` 是否配置正确。如果是 Docker 运行 Mattermost，不能填 `127.0.0.1`（容器内部无法识别），必须填 `http://host.docker.internal:18065/mattermost/callback`。
- 确认 Mattermost 的 `config.json` 里 `ServiceSettings.AllowCorsFrom` 允许跨域或包含了本地主机。

**Q: 给消息点了 🆕 表情但没有分叉出新 Thread？**
1. 确认 Hermes 是否正在输出中——回复生成过程中为防止历史断层，会拒绝分叉操作；
2. 确认当前用户是否在 `MATTERMOST_ALLOWED_USERS` 允许名单内；
3. 检查是否设置了 `MATTERMOST_BRANCH_EMOJI=off`。

**Q: 想要让界面保持干净，不想看到长任务中反复弹出的中间阅读/搜索状态？**
- 在 `~/.hermes/.env` 中添加 `MATTERMOST_TASK_PROGRESS=off`（或在 `config.yaml` 的 `mattermost:` 段添加 `task_progress: off`），重启 Gateway 即可。

**Q: 升级 Hermes Agent 后，需要重新配置吗？**
- 插件的配置与环境变量永久保留。升级后建议在插件目录运行一次 `./scripts/hermes-mattermost-enhancer.sh check` 确认系统适配状态即可。

---

## 📁 项目结构

```text
mattermost-enhancer/
├── plugin.yaml              # 插件元信息与平台声明
├── __init__.py              # 插件入口与平台注册逻辑
├── adapter.py               # 核心适配逻辑与消息处理
├── cards.py                 # 交互卡片渲染模板
├── models.py                # 可用模型列表解析与匹配
├── session_actions.py       # 模型切换与会话重置执行
├── branching.py             # 消息级分支（🆕 表情触发处理）
├── callback_server.py       # 独立回调服务健康自检
├── scripts/
│   └── hermes-mattermost-enhancer.sh   # 配套补充适配脚本
├── tests/                   # 完整自动化回归测试套件
├── README.md                # 英文说明文档
├── README.zh-CN.md          # 中文说明文档
└── LICENSE                  # MIT 开源许可
```

---

## 📄 许可

MIT — 详见 [LICENSE](LICENSE)
