# Hermes Mattermost Enhancer Plugin

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Hermes](https://img.shields.io/badge/Hermes-%E2%89%A5%20v0.23-blue)](https://github.com/nousresearch/hermes-agent)
[![Release](https://img.shields.io/github/v/release/a-nomad-studio/hermes-plugin-mattermost-enhancer?label=release)](https://github.com/a-nomad-studio/hermes-plugin-mattermost-enhancer/releases)

English Version | [中文版本](./README.zh-CN.md)

Makes your Hermes AI assistant smarter, safer, and easier to use inside Mattermost.

---

## 💡 What Is This?

**In one sentence:** If you use Hermes AI Assistant in Mattermost, this plugin brings you all the native interaction capabilities you've been missing.

Vanilla Hermes is great in a terminal or web UI, but inside Mattermost chat it lacks crucial interaction features — you cannot switch models directly, dangerous commands run without confirmation cards, long tasks flood the chat with progress bubbles, and you cannot branch conversations from past messages like in modern AI desktop apps.

This plugin bridges Hermes with Mattermost's native capabilities, delivering a fluid AI conversational experience on desktop, mobile, and web.

---

## ✨ Core Features (Ranked by Utility)

### 🧠 1. Switch AI Models Anytime (`/model` Command & Channel Inheritance)

**Pain Point & Improvement:**
- **Pain Point:** Different tasks require different models (coding models for development, lightweight models for casual chat). Previously, switching models meant editing server config files and restarting the gateway — tedious and disruptive 💀
- **Improvement:** Type `/model` in any Thread or DM, and a dropdown card appears immediately. Pick your model, and **only the current Thread switches instantly** — other conversations remain completely untouched ✅

![Model switching card effect](images/model.webp)

> 💡 **Channel → Thread Inheritance:**
> If you run `/model` in a **channel's main chat window**, any subsequent Thread created by clicking reply will **automatically inherit** that model setting. Existing custom-configured Threads will not be overwritten.

---

### 🛡️ 2. Dangerous Command Safety Approval (DM Confirmation Cards)

**Pain Point & Improvement:**
- **Pain Point:** When AI runs destructive commands (deleting files, dropping databases, running dangerous shell commands), a single misunderstanding can cause irreversible damage before you can stop it in chat 😱
- **Improvement:** For any dangerous action, Hermes sends a **private DM confirmation card** directly to the user who issued the prompt, offering 4 clear options:
  - **Allow Once** (approve this single execution)
  - **Allow This Session** (approve for the duration of this session)
  - **Always Allow** (permanently whitelist this command)
  - **Deny** (reject execution)

![Approval card effect](images/approve.webp)

> 🔒 **Precise Requester Routing:** Even in busy multi-user channels, the approval card is routed specifically to the actual requester's DM — never spamming the channel or mistakenly pinging admins.

---

### ❓ 3. Decision Guidance & AI Questions (Interactive Cards)

**Pain Point & Improvement:**
- **Pain Point:** When Hermes needs clarification during complex tasks (e.g. "Found two approaches: A is faster, B is more reliable. Please pick 1 or 2"), plain text questions easily get lost in chat. If missed, Hermes idles indefinitely until timeout 💀
- **Improvement:** Questions render as **prominent interactive button cards**:
  - Click any choice button to confirm instantly; the card updates in-place with a checkmark ✅
  - Click "✍️ Other" to type free-form feedback directly in chat
  - Open-ended prompts display clean instruction text, ready for direct text replies

![AI questions card effect](images/clarify.webp)

---

### 🌿 4. Fork Conversations from Any Message (🆕 Reaction Branching)

**Pain Point & Improvement:**
- **Pain Point:** 10 turns deep into debugging, you realize you'd like to return to turn 3 and explore a different approach. Clearing context loses everything; cloning the whole conversation creates mess 💀
- **Improvement:** React to any historical message with a 🆕 (`:new:`) emoji. Hermes automatically creates a **brand-new sibling Thread** rooted at that message, carrying forward conversation history up to that point. The original Thread remains intact, allowing parallel exploration without conflict ✅

| Reacted Message | Inherited History | Typical Use Case |
| :--- | :--- | :--- |
| **Your Prompt** | History strictly **before** that prompt | "Let me rephrase this question" or "test with different parameters" |
| **Hermes' Reply** | Entire turn up to that reply (including tool calls & outputs) | "Great solution; let's explore another direction based on this result" |

> 📱 **Native Everywhere:** Long-press on mobile or hover-click on desktop/web — no Mattermost server webapp plugins required.

---

### 🙈 5. Hide Task Thinking & Execution Progress (`task_progress` Toggle)

**Pain Point & Improvement:**
- **Pain Point:** When Hermes conducts web searches, reads long files, or executes multi-step scripts, intermediate progress bubbles (`🔍 Searching the web for ...`, `📖 Reading file ...`) repeatedly pop up and update. In routine Q&A, this creates visual clutter and chat spam 💀
- **Improvement:** Provides a `task_progress` configuration (defaults to `on`). Setting it to `off` completely hides intermediate thinking and tool execution messages while keeping the active typing indicator, delivering only the clean final reply ✅

**Configuration (Choose One):**
- **Method 1: Environment Variable (`~/.hermes/.env`)**
  ```dotenv
  MATTERMOST_TASK_PROGRESS=off
  ```
- **Method 2: Config File (`~/.hermes/config.yaml`)**
  ```yaml
  mattermost:
    task_progress: off
  ```
  *(Restart Gateway after updating)*

---

### 🧠 6. Adjust Reasoning Effort (`/reasoning` Command)

**Pain Point & Improvement:**
- **Pain Point:** Simple questions don't need deep thinking; complex debugging warrants maximal reasoning. Previously, there was no way to adjust reasoning depth temporarily from chat.
- **Improvement:** Send commands directly in the Thread to adjust reasoning depth for the current conversation:
  - `/reasoning low` (quick, light reasoning)
  - `/reasoning high` (deep, rigorous thinking)
  - `/reasoning none` (turn reasoning off when model supports it)
  - `/reasoning` (inspect current session's effective level)
  - `/reasoning reset` (clear session override and inherit default)

---

### 🔄 7. Reset Current Conversation Context (`/new` Command)

**Pain Point & Improvement:**
- **Pain Point:** The current Thread has wandered off-topic. You want to keep chatting in the same window without carrying stale context forward.
- **Improvement:** Type `/new` in any Thread or DM, click the confirmation card, and a fresh conversation session begins immediately.

![New session card effect](images/new.webp)

> 💡 In thread mode, sending a new message in the main channel automatically starts a fresh Thread — no need to run `/new`.

---

### 🗜️ 8. Compress Long Conversation Context (`/compress` / `/compact`)

**Pain Point & Improvement:**
- **Pain Point:** After dozens of turns, conversation context nears the model's window limit, degrading speed and increasing token costs.
- **Improvement:** Run `/compress`, and Hermes summarizes earlier discussions into key takeaways while keeping you in the **same Thread**:

```text
/compress                               # Automatic intelligent compression
/compress focus on architecture and tasks # Custom-focused summary
/compress --preview                     # Preview compression plan without applying
```

---

### 🏷️ 9. Model & Context Reply Footer

**Pain Point & Improvement:**
- **Pain Point:** With multiple Threads open, it's easy to forget which model is running in which conversation.
- **Improvement:** Once enabled, every reply concludes with a subtle monospace footer (e.g. `── deepseek-v4-pro 34% ──`), showing active model and context usage at a glance.

![Model footnote effect](images/footer.webp)

> 💡 **How to Enable:** In `~/.hermes/config.yaml`, under `display`:
> ```yaml
> display:
>   runtime_footer:
>     enabled: true
>     fields:
>       - model
>       - context_pct
> ```

---

### ⌨️ 10. In-Thread Typing Indicator

**Pain Point & Improvement:**
- **Pain Point:** Vanilla systems post "typing..." indicators at the channel level rather than inside the Thread you're watching, making you think Hermes is stuck or frozen 😕
- **Improvement:** Correctly routes typing indicators into the active Thread so you know Hermes is actively working on your request ✅

![Typing indicator example](images/typing.webp)

---

## 🐛 Core Issues Solved

| Category | Issue Encountered | User Impact | Plugin Solution |
| :--- | :--- | :--- | :--- |
| **Command Routing** | Slash commands intercepted by Mattermost | Commands like `/model` and `/new` error out in chat | Dedicated local callback server routes commands smoothly |
| **Status Feedback** | Typing indicator displayed in wrong place | User sees no feedback in Thread, assuming bot is frozen | Typing indicator accurately routed to current Thread footer |
| **Safety Approval** | Multi-user approval sent to wrong person | Dangerous commands run by members sent approval DM to admin | Precise sender tracking routes cards to actual requester |
| **Network Stability** | WebSocket frequent disconnects | Reconnect loops every ~50s causing dropped or delayed messages | Heartbeat optimized to 15s for rock-solid connection |
| **Decision Prompting** | Plain text questions buried in stream | Critical clarify questions missed, stalling background tasks | Interactive button cards with optional custom text entry |
| **Branching** | Inability to fork from past messages | Cannot branch alternative exploration without losing context | Native 🆕 reaction branching creates clean sibling Threads |

---

## 🚀 Quick Start (4 Steps)

### Prerequisites
- ✅ [Hermes Agent](https://github.com/nousresearch/hermes-agent) installed (version ≥ v0.23.0)
- ✅ Active Mattermost server with a configured Bot account
- ✅ Python 3.11+ environment

---

### Step 1: Install the Plugin

```bash
hermes plugins install a-nomad-studio/hermes-plugin-mattermost-enhancer --enable
```

---

### Step 2: Register Mattermost Custom Slash Commands

In Mattermost, go to **Product menu → Integrations → Slash Commands** and add the following (Request Method: **POST**):

| Trigger Word (no slash) | Display Title | Request URL |
| :--- | :--- | :--- |
| `model` | Switch AI Model | `http://<Hermes-Host-IP>:18065/mm-command` |
| `new` | Reset Conversation | `http://<Hermes-Host-IP>:18065/mm-command` |
| `reasoning` | Adjust Reasoning Effort | `http://<Hermes-Host-IP>:18065/mm-command` |
| `compress` | Compress Conversation Context | `http://<Hermes-Host-IP>:18065/mm-command` |
| `compact` | Compress Context (Alias) | `http://<Hermes-Host-IP>:18065/mm-command` |

> 🔧 **Docker Tip:** When Mattermost runs in Docker and Hermes runs on host, use: `http://host.docker.internal:18065/mm-command`.

After saving, copy the generated token for each command.

---

### Step 3: Configure Environment Variables

Add to `~/.hermes/.env`:

```dotenv
# ── Callback Server ──
MATTERMOST_CALLBACK_BIND=0.0.0.0
MATTERMOST_CALLBACK_PORT=18065

# ── Callback URL (for Mattermost to reach host) ──
# Docker setup requires host.docker.internal:
MATTERMOST_CALLBACK_URL=http://host.docker.internal:18065/mattermost/callback

# ── Security Secret (Recommended 32-char random string) ──
MATTERMOST_CALLBACK_SECRET=replace-with-a-long-random-secret

# ── Slash Command Tokens (Map triggers to copied tokens) ──
MATTERMOST_SLASH_COMMAND_TOKENS="model=token1;new=token2;reasoning=token3;compress=token4;compact=token5"

# ── Optional: Task Progress Display (Default: on; set off to hide tool bubbles) ──
# MATTERMOST_TASK_PROGRESS=on

# ── Optional: Branch Reaction Emoji (Default: new; set off to disable) ──
# MATTERMOST_BRANCH_EMOJI=new
```

---

### Step 4: Run Companion Script & Restart Gateway

```bash
cd ~/.hermes/plugins/mattermost-enhancer

# 1. Check environment & patch status
./scripts/hermes-mattermost-enhancer.sh check

# 2. If prompted, apply companion fixes
./scripts/hermes-mattermost-enhancer.sh apply

# 3. Restart Hermes Gateway in an external terminal
hermes gateway restart
```

🎉 **All done!** Try sending `/model` in a Mattermost Thread or react to a message with 🆕!

---

## ❓ FAQ

**Q: Clicking card buttons or typing `/model` has no response?**
- Verify `MATTERMOST_CALLBACK_URL`. If Mattermost runs in Docker, `127.0.0.1` refers to the container itself; you must use `http://host.docker.internal:18065/mattermost/callback`.
- Ensure Mattermost's `config.json` has `ServiceSettings.AllowCorsFrom` configured.

**Q: Reacting with 🆕 doesn't branch the conversation?**
1. Check if Hermes is currently generating a response (branching mid-run is prevented to avoid corrupt history);
2. Ensure your account is in `MATTERMOST_ALLOWED_USERS`;
3. Check whether `MATTERMOST_BRANCH_EMOJI=off` is set.

**Q: How do I hide intermediate progress bubbles during complex tasks?**
- Set `MATTERMOST_TASK_PROGRESS=off` in `~/.hermes/.env` (or `task_progress: off` in `config.yaml` under `mattermost:`) and restart the Gateway.

**Q: Do I need to reconfigure when upgrading Hermes?**
- Configurations in `.env` and `config.yaml` persist across updates. After major Hermes upgrades, simply run `./scripts/hermes-mattermost-enhancer.sh check` to verify compatibility.

---

## 📁 Project Structure

```text
mattermost-enhancer/
├── plugin.yaml              # Plugin metadata and platform declaration
├── __init__.py              # Entry point and registration
├── adapter.py               # Core adapter and messaging logic
├── cards.py                 # Interactive card templates
├── models.py                # Model listing and provider resolution
├── session_actions.py       # Model switching and session resets
├── branching.py             # Message branching (:new: reaction handling)
├── callback_server.py       # Callback server health probe
├── scripts/
│   └── hermes-mattermost-enhancer.sh   # Companion gateway patches
├── tests/                   # Regression test suite
├── README.md                # English documentation
├── README.zh-CN.md          # Chinese documentation
└── LICENSE                  # MIT License
```

---

## 📄 License

[MIT License](LICENSE)
