---
title: "Spec Stateflow Kit — Installation Guide"
version: "1.0"
date: "2026-05-07"
description: "Spec Stateflow Kit 安装指南：一键安装、验证、故障排查与卸载。阅读时长约 3 分钟。"
---

# Spec Stateflow Kit — Installation Guide

> **中文 |** [跳转到中文版](#中文版安装指南)
> **TL;DR** — 告诉 Claw Agent kit 目录路径 → Claw Agent 自动读取 SKILL.md 并完成全部 7 步安装。

---

## Kit Contents

| Component | Description |
|-----------|-------------|
| `spec-stateflow-kit-installer` | Installer skill (includes claude-sample.md template) |
| `spec-task-progress` | Progress query skill |
| `claude-code-spec-driver` | Drive Claude Code to continue development |
| `claude-code-spec-monitor` | Monitor guard (stall restart / completion stop) |
| `spec-stateflow` | Claude Code side spec workflow skill |

---

## Prerequisites

- Claude Code installed and available (`claude --version` works)
- A claw agent that supports skills, installed

---

## Installation Steps

### 1. Tell your Claw Agent to install

Tell your Claw Agent where the kit is and ask it to install:

> "Please install the spec kit, the kit directory is at `/Users/yourname/Desktop/spec-stateflow-kit`"

No manual steps required — the installer handles everything.

Your Claw Agent reads `spec-stateflow-kit-installer/SKILL.md` directly from the kit directory you provide — no pre-installation of the installer skill is needed.

### 2. Follow the installer prompts

The installer will guide you through the following steps:

| Step | Action | Details |
|------|--------|---------|
| [0] | Kit directory | Confirmed from your message, or the installer will ask if not provided |
| [1/7] | Checking Claude Code... | Auto-detect |
| [2/7] | Configuring environment... | You need to confirm: Workspace root directory (must specify), Spec doc path (default: {WORKSPACE}/doc, auto-created), Claude Code path (auto-detected) |
| [3/7] | Installing Skills... | Auto-copy from kit directory |
| [4/7] | Validating paths... | Verifies path alignment and smoke-tests spec-env.json loading |
| [5/7] | Configuring Claude Code (claude.md)... | Auto-inject (with language auto-detection) |
| [6/7] | Configuring Claude Code (claude-reference.md)... | Auto-inject (same language) |
| [7/7] | Installing spec-stateflow + spec-task-progress (Claude Code side)... | Auto-copy both skills to `~/.claude/skills/` |

**IMPORTANT NOTES:**

- **Kit directory**: The folder you downloaded/cloned — can be anywhere on your system
- **Workspace root directory**: Must be specified by you. This is the parent directory of all projects and doc (e.g. `/Users/yourname/Projects`)
- **Spec doc directory**: Defaults to `{workspace}/doc`, auto-created if missing
- Each config item requires a second confirmation
- Step 5 auto-detects the language of your existing CLAUDE.md and translates the spec content to match

### 3. Verify installation

Run these commands and expect the following outputs:

```bash
$ cat {SKILLS_DIR}/../spec-env.json
{
  "WORKSPACE": "/Users/yourname/Projects",
  "DOC_DIR": "doc",
  "CLAUDE_CLI": "/Users/yourname/.local/bin/claude"
}

$ ls {SKILLS_DIR}/spec-task-progress/
SKILL.md  test-cases/  test-prompts.json

$ ls {SKILLS_DIR}/claude-code-spec-driver/
SKILL.md  scripts/  test-prompts.json

$ ls {SKILLS_DIR}/claude-code-spec-monitor/
SKILL.md  scripts/  test-prompts.json

$ ls ~/.claude/skills/spec-stateflow/
SKILL.md  test-prompts.json

$ ls ~/.claude/skills/spec-task-progress/
SKILL.md  test-cases/  test-prompts.json
```

If any of the above directories are missing or empty, the installation did not complete successfully. Re-run the installer.

---

## Custom Configuration

After installation, you can manually edit `{SKILLS_DIR}/../spec-env.json`:

```json
{
  "WORKSPACE": "/your/workspace/path",
  "DOC_DIR": "doc",
  "CLAUDE_CLI": "/your/path/to/claude"
}
```

All skills read this file dynamically at runtime; changes take effect immediately.

---

## Uninstall

The `spec-stateflow-kit-installer` supports 2 modes: **install**, **uninstall**.

### Uninstall

Tell your Claw Agent:
> "Uninstall spec kit" or "Remove spec"

The installer will remove:
- `{SKILLS_DIR}/../spec-env.json`
- `{SKILLS_DIR}/spec-task-progress/`
- `{SKILLS_DIR}/claude-code-spec-driver/`
- `{SKILLS_DIR}/claude-code-spec-monitor/`
- `{SKILLS_DIR}/spec-stateflow-kit-installer/`
- `~/.claude/skills/spec-stateflow/`
- `~/.claude/skills/spec-task-progress/`
- Spec content from `~/.claude/CLAUDE.md`
- `~/.claude/CLAUDE-reference.md`
- Monitor state files (`/tmp/claude-monitor-*.json`)

Your spec documents at `{WORKSPACE}/{DOC_DIR}` are **NOT** removed.

To re-install after uninstalling, tell your Claw Agent the kit directory path again (e.g. "install spec kit at ~/Desktop/spec-stateflow-kit"). Your Claw Agent reads the installer skill directly from the kit source — no manual copying required.

### Manual uninstall

⚠️ **WARNING**: These commands will permanently delete files. Make sure you have backups of any custom modifications before proceeding.

```bash
$ rm -rf {SKILLS_DIR}/spec-task-progress/
$ rm -rf {SKILLS_DIR}/claude-code-spec-driver/
$ rm -rf {SKILLS_DIR}/claude-code-spec-monitor/
$ rm -rf {SKILLS_DIR}/spec-stateflow-kit-installer/
$ rm {SKILLS_DIR}/../spec-env.json
$ rm -rf ~/.claude/skills/spec-stateflow/
$ rm -rf ~/.claude/skills/spec-task-progress/
$ rm -f /tmp/claude-monitor-*.json /tmp/claude-monitor-*.pid /tmp/claude-monitor-*.lock /tmp/claude-monitor-*-daemon.log /tmp/claude-spec-*.log
# Manually edit ~/.claude/CLAUDE.md, remove spec-related sections
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "spec-env.json not found" | Re-run the installer by telling your Claw Agent the kit directory path (e.g. "install spec kit at ~/Desktop/spec-stateflow-kit") |
| "Claude Code not installed" | Install Claude Code, verify with `claude --version`. If installed but not in PATH, specify full path during installation. |
| Scripts lack execute permission | `chmod +x {SKILLS_DIR}/*/scripts/*.sh` and `find {SKILLS_DIR}/ -type f -name "*.py" -exec chmod +x {} \;` |
| Paths incorrect | Edit `{SKILLS_DIR}/../spec-env.json`. Ensure `WORKSPACE` is the **parent** directory of all projects, not a specific project. |
| "CLAUDE.md already has spec content" | The installer will detect existing content via `<!-- SPEC_STATEFLOW_KIT_BEGIN -->` markers and ask whether to overwrite. If markers are missing (legacy install), use manual uninstall instructions. |
| Language detection wrong (e.g., Chinese CLAUDE.md detected as English) | The CJK ratio threshold is 0.3. If your CLAUDE.md has <30% CJK characters, it defaults to English. You can manually translate after installation. |
| "spec-stateflow already exists" during install | The installer will prompt for overwrite confirmation. Choose "y" to replace with the latest version, or "n" to skip. |
| Uninstaller leaves CLAUDE.md content behind | Legacy installations without BEGIN/END markers require manual review. The uninstaller will warn you and suggest 3-strategy removal. |
| Install fails at Step 5 (CLAUDE.md) | Ensure `~/.claude/CLAUDE.md` is writable. Check with `touch ~/.claude/CLAUDE.md`. If read-only, fix permissions first. |
| CLAUDE.md shows 方块/乱码 after install | The Claw Agent's file-write tool corrupted UTF-8 encoding. Re-run Step 5 using a safe write method: `cat <<'EOF' >> ~/.claude/CLAUDE.md` or Python `codecs.open(..., 'utf-8')`. Verify with `cat ~/.claude/CLAUDE.md` before continuing. |

---

## Quick Checklist

Before telling your Claw Agent to install, ensure:

- [ ] Claude Code is installed (`claude --version` returns a version number)
- [ ] You know the path to the `spec-stateflow-kit` folder on your system
- [ ] You know your workspace root directory (parent of all projects + doc)
- [ ] `~/.claude/` directory exists (or you are OK with it being created)
- [ ] You have backed up any custom content in `~/.claude/CLAUDE.md` (just in case)

After installation, verify:

- [ ] `{SKILLS_DIR}/../spec-env.json` contains correct paths
- [ ] All 4 skill directories exist under `{SKILLS_DIR}/`
- [ ] `~/.claude/skills/spec-stateflow/` exists
- [ ] `~/.claude/skills/spec-task-progress/` exists
- [ ] Saying "task progress" to your Claw Agent returns expected output (if no tasks exist yet, it should report "no tasks found" rather than an error)

---

## See Also

| Document | What You'll Find There |
|----------|------------------------|
| `README.md` | Architecture overview, state machine design, component descriptions |
| `spec-stateflow/SKILL.md` | How the 4-phase workflow works (requirements → design → tasks → execute) |
| `spec-task-progress/SKILL.md` | How to query task progress after installation |
| `claude-code-spec-driver/SKILL.md` | How to drive Claude Code to continue development |
| `claude-code-spec-monitor/SKILL.md` | How to set up autonomous monitoring |

---
---
---

<h1 id="中文版安装指南">Spec Stateflow Kit — 中文版安装指南</h1>

> **English |** [Back to English](#spec-stateflow-kit--installation-guide)
> **TL;DR** — 告诉 Claw Agent kit 目录路径 → Claw Agent 自动读取 SKILL.md 并完成全部 7 步安装。

---

## 套件内容

| 组件 | 说明 |
|-----------|-------------|
| `spec-stateflow-kit-installer` | 安装器技能（包含 claude-sample.md 模板） |
| `spec-task-progress` | 进度查询技能 |
| `claude-code-spec-driver` | 驱动 Claude Code 继续开发 |
| `claude-code-spec-monitor` | 监控守护（卡死重启 / 完成停止） |
| `spec-stateflow` | Claude Code 侧 spec 工作流技能 |

---

## 前置条件

- 已安装 Claude Code 且可用（`claude --version` 能执行）
- 已安装支持 skills 的 Claw Agent

---

## 安装步骤

### 1. 告诉 Claw Agent 安装

告诉 Claw Agent kit 所在位置并让它安装：

> "帮我安装 spec 套件，kit 目录在 `/Users/yourname/Desktop/spec-stateflow-kit`"

无需任何手动操作，安装器全程处理。

Claw Agent 直接从你提供的 kit 目录读取 `spec-stateflow-kit-installer/SKILL.md`，无需预先将安装器 skill 复制到任何位置。

### 2. 跟随安装器提示操作

安装器会引导你完成以下步骤：

| 步骤 | 动作 | 详情 |
|------|--------|---------|
| [0] | Kit 目录 | 从你的消息中确认，若未提供则安装器会询问 |
| [1/7] | 检查 Claude Code... | 自动检测 |
| [2/7] | 配置环境... | 需要你确认：工作区根目录（必须指定）、Spec 文档路径（默认：{WORKSPACE}/doc，自动创建）、Claude Code 路径（自动检测） |
| [3/7] | 安装技能... | 从 kit 目录自动复制 |
| [4/7] | 校验路径... | 验证路径对齐，并对 spec-env.json 加载进行冒烟测试 |
| [5/7] | 配置 Claude Code (claude.md)... | 自动注入（自动语言检测） |
| [6/7] | 配置 Claude Code (claude-reference.md)... | 自动注入（相同语言） |
| [7/7] | 安装 spec-stateflow + spec-task-progress（Claude Code 侧）... | 自动复制两个 skill 到 `~/.claude/skills/` |

**重要提示：**

- **Kit 目录**：你下载或克隆的文件夹，可以放在系统任意位置
- **工作区根目录**：必须由你指定。这是所有项目和文档的父目录（例如 `/Users/yourname/Projects`）
- **Spec 文档目录**：默认为 `{workspace}/doc`，如不存在则自动创建
- 每个配置项需要二次确认
- 第 5 步会自动检测你现有 CLAUDE.md 的语言，并将 spec 内容翻译为匹配语言

### 3. 验证安装

运行以下命令，预期输出如下：

```bash
$ cat {SKILLS_DIR}/../spec-env.json
{
  "WORKSPACE": "/Users/yourname/Projects",
  "DOC_DIR": "doc",
  "CLAUDE_CLI": "/Users/yourname/.local/bin/claude"
}

$ ls {SKILLS_DIR}/spec-task-progress/
SKILL.md  test-cases/  test-prompts.json

$ ls {SKILLS_DIR}/claude-code-spec-driver/
SKILL.md  scripts/  test-prompts.json

$ ls {SKILLS_DIR}/claude-code-spec-monitor/
SKILL.md  scripts/  test-prompts.json

$ ls ~/.claude/skills/spec-stateflow/
SKILL.md  test-prompts.json

$ ls ~/.claude/skills/spec-task-progress/
SKILL.md  test-cases/  test-prompts.json
```

如果上述任一目录缺失或为空，说明安装未完成。请重新运行安装器。

---

## 自定义配置

安装完成后，你可以手动编辑 `{SKILLS_DIR}/../spec-env.json`：

```json
{
  "WORKSPACE": "/your/workspace/path",
  "DOC_DIR": "doc",
  "CLAUDE_CLI": "/your/path/to/claude"
}
```

所有技能在运行时动态读取此文件；修改立即生效。

---

## 卸载

`spec-stateflow-kit-installer` 支持 2 种模式：**安装**、**卸载**。

### 卸载

告诉 Claw Agent：
> "卸载 spec kit" 或 "移除 spec"

安装器将移除：
- `{SKILLS_DIR}/../spec-env.json`
- `{SKILLS_DIR}/spec-task-progress/`
- `{SKILLS_DIR}/claude-code-spec-driver/`
- `{SKILLS_DIR}/claude-code-spec-monitor/`
- `{SKILLS_DIR}/spec-stateflow-kit-installer/`
- `~/.claude/skills/spec-stateflow/`
- `~/.claude/skills/spec-task-progress/`
- `~/.claude/CLAUDE.md` 中的 spec 相关内容
- `~/.claude/CLAUDE-reference.md`
- 监控状态文件（`/tmp/claude-monitor-*.json`）

`{WORKSPACE}/{DOC_DIR}` 中的 spec 文档**不会**被移除。

重新安装时，再次告诉 Claw Agent kit 目录路径即可（例如 "install spec kit at ~/Desktop/spec-stateflow-kit"）。Claw Agent 直接从 kit 源目录读取安装器 skill，无需手动复制。

### 手动卸载

⚠️ **警告**：以下命令将永久删除文件。执行前请确保你已备份所有自定义修改。

```bash
$ rm -rf {SKILLS_DIR}/spec-task-progress/
$ rm -rf {SKILLS_DIR}/claude-code-spec-driver/
$ rm -rf {SKILLS_DIR}/claude-code-spec-monitor/
$ rm -rf {SKILLS_DIR}/spec-stateflow-kit-installer/
$ rm {SKILLS_DIR}/../spec-env.json
$ rm -rf ~/.claude/skills/spec-stateflow/
$ rm -rf ~/.claude/skills/spec-task-progress/
$ rm -f /tmp/claude-monitor-*.json /tmp/claude-monitor-*.pid /tmp/claude-monitor-*.lock /tmp/claude-monitor-*-daemon.log /tmp/claude-spec-*.log
# 手动编辑 ~/.claude/CLAUDE.md，删除 spec 相关章节
```

---

## 故障排查

| 问题 | 解决方案 |
|---------|----------|
| "spec-env.json not found" | 重新告知 Claw Agent kit 目录路径以触发安装器（例如 "install spec kit at ~/Desktop/spec-stateflow-kit"） |
| "Claude Code not installed" | 安装 Claude Code，用 `claude --version` 验证 |
| 脚本缺少执行权限 | `chmod +x {SKILLS_DIR}/*/scripts/*.sh` 和 `find {SKILLS_DIR}/ -type f -name "*.py" -exec chmod +x {} \;` |
| 路径不正确 | 编辑 `{SKILLS_DIR}/../spec-env.json`。注意 `WORKSPACE` 必须是所有项目的**父目录**，而非某个具体项目 |
| "CLAUDE.md 已包含 spec 内容" | 安装器会通过 `<!-- SPEC_STATEFLOW_KIT_BEGIN -->` 标记检测现有内容并询问是否覆盖。如标记缺失（旧版安装），请使用手动卸载说明 |
| 语言检测错误（如中文 CLAUDE.md 被识别为英文） | CJK 比例阈值为 0.3。如 CLAUDE.md 中 CJK 字符 <30%，默认使用英文。可在安装后手动翻译 |
| 安装时提示 "spec-stateflow already exists" | 安装器会提示是否覆盖。选择 "y" 替换为最新版本，或 "n" 跳过 |
| 卸载器残留 CLAUDE.md 内容 | 无 BEGIN/END 标记的旧版安装需要手动审查。卸载器会警告并建议 3 策略移除 |
| 安装时在 Step 5 (CLAUDE.md) 失败 | 确保 `~/.claude/CLAUDE.md` 可写。检查：`touch ~/.claude/CLAUDE.md`。如只读，请先修复权限 |

---

## 快速检查清单

在告诉 Claw Agent 安装前，请确认以下事项：

- [ ] Claude Code 已安装（`claude --version` 返回版本号）
- [ ] 已知 `spec-stateflow-kit` 文件夹在系统中的路径
- [ ] 已知工作区根目录（所有项目 + doc 的父目录）
- [ ] `~/.claude/` 目录存在（或允许自动创建）
- [ ] 已备份 `~/.claude/CLAUDE.md` 中的自定义内容（以防万一）

安装后验证：

- [ ] `{SKILLS_DIR}/../spec-env.json` 包含正确路径
- [ ] `{SKILLS_DIR}/` 下 4 个技能目录均存在
- [ ] `~/.claude/skills/spec-stateflow/` 存在
- [ ] `~/.claude/skills/spec-task-progress/` 存在
- [ ] 对 Claw Agent 说 "task progress" 能返回预期输出（如尚无任务，应返回"未找到任务"而非报错）

---

## 相关文档

| 文档 | 内容 |
|------|------|
| `README.md` | 架构总览、状态机设计、组件说明 |
| `spec-stateflow/SKILL.md` | 四阶段工作流详细规范（需求→设计→任务→执行） |
| `spec-task-progress/SKILL.md` | 安装后如何查询任务进度 |
| `claude-code-spec-driver/SKILL.md` | 如何驱动 Claude Code 继续开发 |
| `claude-code-spec-monitor/SKILL.md` | 如何设置自主监控 |
