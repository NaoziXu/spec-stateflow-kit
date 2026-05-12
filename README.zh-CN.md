[![English](https://img.shields.io/badge/README-English-blue)](README.md)

# Spec Stateflow Kit

> 面向 AI 编程 Agent 的状态驱动结构化开发工作流套件。以 `tasks.md` 作为唯一可信来源，彻底解决"我做到哪了？"——会话压缩免疫、卡死自动处理、范围蔓延受控。

## 快速安装

告诉你的 Agent：

> "帮我安装 spec 套件，kit 目录在 `/path/to/spec-stateflow-kit`"

无需任何手动操作。→ [完整安装指南](Installation.md)

---

## Spec 工作原理

Spec 是一种**状态驱动的结构化开发工作流**。它不直接跳入代码编写，而是将每个复杂任务强制通过一条规范化的流水线：

```
需求分析 → 方案设计 → 任务拆解 → 执行开发 → 进度追踪
```

核心洞察：**任务追踪器 (`tasks.md`) 是唯一可信来源**。每次代码变更都与已追踪的任务绑定。进度由追踪器的状态定义，而非对话记忆。

### 为什么有效

| 痛点 | Spec 的解法 |
|---------|--------------|
| "我做到哪了？" | 查看 `tasks.md` — 状态标记一目了然 |
| 会话被压缩/中断 | 恢复流程读取追踪器，验证最后完成的任务，然后续接 |
| 范围蔓延 | 每个任务都有 Scope/Specifics 字段；变更计入 Notes + 用户修正次数 |
| "我完成了吗？" | 追踪器显示 `[✓]` 才算完成。没有例外。 |
| 多任务并行 | 每个需求一个 `tasks.md`。使用独立的 `{SPEC_PATH}` 目录。绝不混用。 |

---

## 套件架构

```
spec-stateflow-kit/
├── spec-stateflow-kit-installer/    ← 安装器（负责部署全部组件）
│   ├── SKILL.md                     ← 安装 / 卸载逻辑
│   ├── spec-env.json.example        ← 环境配置模板
│   ├── test-cases/                  ← 逻辑测试夹具（语言/标记检测）
│   ├── test-prompts.json
│   └── scripts/
│       ├── spec-stop-anchor.sh      ← Stop Hook 脚本
│       └── spec-state-guard.sh      ← PostToolUse Hook 脚本
│
├── spec-stateflow/                  ← 核心工作流引擎（运行在 Claude Code 内）
│   ├── SKILL.md                     ← 四阶段工作流 + 状态机
│   └── test-prompts.json
│
├── spec-router/                     ← 常驻路由层（运行在 Claude Code 内）
│   └── SKILL.md                     ← 任务分类 + 命令路由 + 会话恢复
│
├── spec-task-progress/              ← 进度查询（运行在 Claw Agent + Claude Code 内）
│   ├── SKILL.md
│   ├── test-cases/                  ← LLM 解析测试夹具
│   └── test-prompts.json
│
├── claude-code-spec-driver/         ← 驱动 Claude Code 继续开发
│   ├── SKILL.md
│   ├── test-cases/                  ← 决策逻辑测试夹具
│   ├── scripts/launch_claude_spec.sh
│   └── test-prompts.json
│
├── claude-code-spec-monitor/        ← 监控守护（卡死重启 / 完成停止）
│   ├── SKILL.md
│   ├── scripts/snapshot.py          ← 卡死检测状态机
│   └── test-prompts.json
│
├── Installation.md                  ← 安装指南
└── README.md                        ← 本文件（中文版）
```

### 部署拓扑

```
┌─────────────────────────────────┐     ┌──────────────────────────────────┐
│         Claw Agent Side         │     │        Claude Code Side          │
│                                 │     │                                  │
│  {SKILLS_DIR}/                  │     │  ~/.claude/                      │
│    spec-stateflow-kit-installer │     │    spec-env.json                 │
│    spec-task-progress           │     │    settings.json  (hooks)        │
│    claude-code-spec-driver      │     │    skills/spec-stateflow/        │
│    claude-code-spec-monitor     │     │    skills/spec-task-progress/    │
│                                 │     │    skills/spec-router/           │
│  {SKILLS_DIR}/../spec-env.json  │     │    scripts/spec-stop-anchor.sh   │
└─────────────────────────────────┘     │    scripts/spec-state-guard.sh   │
                                        └──────────────────────────────────┘
```

安装器 (`spec-stateflow-kit-installer`) 管理完整的生命周期 — 复制技能、写入配置、安装 Hook 脚本 — 用户无需手动触碰任何路径。

---

## spec-stateflow：状态设计模式

核心技能 `spec-stateflow` 实现了一个**有限状态机**，包含 4 个宏状态，每个宏状态内部有各自的状态转换：

### 宏状态

```
[已分类] ──(复杂/修复)──→ [规划中] ──(已确认)──→ [执行中] ──(全部完成)──→ [已完成]
      │                            │                          │
  (简单/常规)                    (被拒绝)                     (出错)
      │                            │                          │
      ↓                            ↓                          ↓
  [直接执行]                    [修订方案]                 [诊断 → 修复]
                                                              ↑
                                                              │
                                                            [恢复] ←──(会话被压缩/中断)
```

| 宏状态 | 内部阶段 | 进入条件 | 退出条件 |
|-------------|----------------|-----------------|----------------|
| **规划中** | 阶段1（需求分析）→ 阶段2（方案设计）→ 阶段3（任务拆解） | 任务被分类为复杂/修复 | 用户确认 `tasks.md` |
| **执行中** | 阶段4 — 顺序执行任务 | `tasks.md` 已确认 | 所有任务 `[✓]` 或 `[⏭]` |
| **已完成** | 生成最终总结 | 所有任务完成 | 用户确认总结 |
| **恢复中** | 压缩恢复（6步流程） | 会话被压缩/中断 | 追踪器与代码状态对账一致 |

### 任务级状态机

`tasks.md` 中的每个任务都遵循严格的生命周期：

```
[ ] 未开始 ──(开始)──→ [~] 进行中 ──(完成并通过验证)──→ [✓] 已完成
                           │                   │
                     (会话被压缩)            (验证失败)
                           │                   │
                           ↓                   ↓
                       [ ] 重新验证          [~] 返工
```

| 状态 | 含义 | 转换规则 |
|--------|---------|----------------|
| `[ ]` | 未开始 | → `[~]` 必须在编辑代码之前 |
| `[~]` | 进行中 / 已暂停 | → `[✓]` 验证通过后；→ `[ ]` 会话被压缩且状态不确定时 |
| `[✓]` | 已完成 | 仅在 Verification 字段填写后设置；绝不追溯 |
| `[⏭]` | 已跳过 | 仅由用户决定；agent 不能自行跳过 |

### 状态保障规则

1. **追踪器即真相** — 如果记忆与追踪器冲突，以追踪器为准；暂停并对账
2. **及时性** — 状态必须在提交代码**之前**更新，而非之后
3. **Specifics 字段至关重要** — 必须精确到方法/字段级别；恢复流程依赖它
4. **禁止追溯写入** — 压缩前未记录的进度不可靠；应重新验证
5. **用户修正计数器** — ≥2 次触发升级处理

---

## 技能说明

### spec-stateflow
**角色：** 核心工作流引擎（运行在 Claude Code 内部）
**功能：** 实现完整的四阶段结构化开发工作流：
- 阶段1：使用 EARS 语法进行需求分析 → `requirements.md`
- 阶段2：技术方案设计（架构、API、数据库） → `design.md`
- 阶段3：任务拆解，精确到字段级别 → `tasks.md`
- 阶段4：顺序执行，带状态追踪、压缩恢复和上下文切换

**关键设计：** 状态驱动执行 — 每个动作都映射为 `tasks.md` 中的状态转换。追踪器是唯一可信来源。

### spec-stateflow-kit-installer
**角色：** 生命周期管理器
**功能：** 以 2 种模式安装或卸载整个套件：
- **安装**（7步）：检查 Claude Code → 配置环境 → 复制 4 个 Claw Agent 技能 → 校验路径 → 安装 Claude Code 侧技能（spec-stateflow + spec-task-progress + spec-router）→ 安装 Hook 脚本 → 配置 settings.json
- **卸载**（10步）：确认 → 停止监控进程 → 移除所有组件 → 移除 Hook 脚本 → 移除 settings.json 条目 → 清理

**关键设计：** 路径对齐校验防止 spec-env.json 路径错误，监控器脚本自测在安装时验证，卸载时完整清理（安装器本身也会被移除）。

### spec-router
**角色：** 常驻路由层（运行在 Claude Code 内部）
**功能：** 在每次 Claude Code 会话中加载（`alwaysApply: true`），提供三项服务：
1. **任务分类** — 将用户输入映射为 Complex / Fix / Simple / Routine 并按类路由
2. **命令路由** — 处理 `continue` / `resume` / `check progress`，无需用户主动提及 spec-stateflow
3. **Step 0 会话恢复** — 会话启动时读取 `~/.claude/spec-session.json`；若最近且未完成，预加载上下文并直接跳转到压缩恢复 Step 2

**关键设计：** 仅为薄路由层，不包含工作流逻辑。所有执行立即委托给 `spec-stateflow`。读取 `~/.claude/spec-env.json` 进行路径解析。

### spec-task-progress
**角色：** 进度查询（LLM 驱动）
**功能：** LLM 解析 `tasks.md` 并写入结构化 `progress.json`：
- 检查现有 `progress.json` 是否新鲜（≤15 分钟阈值）— 新鲜则直接返回缓存
- 否则：读取 `tasks.md`，统计 `[✓]`/`[⏭]`/`[~]`/`[ ]` 标记，写入 7 字段的 `progress.json`
- 双环境部署（agent 侧 `{SKILLS_DIR}` + Claude Code 侧 `~/.claude/skills/`）— daemon 通过 `claude -p` 调用进行进度检查

**关键设计：** 纯 LLM 解析，无正则脚本。原子写入（临时文件+重命名）防止竞态条件。双环境路径解析（Claude Code 读 CLAUDE.md，agent 读 spec-env.json）。被 spec-driver 和 spec-monitor 消费。

### claude-code-spec-driver
**角色：** Claude Code 启动器
**功能：** 基于任务进度生成提示词，并在非交互后台模式下启动 Claude Code：
1. 查询进度 → 2. 定位 spec 文档 + 确认项目 → 3. 生成提示词（用户确认 ⛔）→ 4. 启动 Claude Code → 5. 报告 PID + 日志路径

**关键设计：** `progress.json` 中的 `project_name` 字段实现项目目录持久化，工作区保护（有未提交变更 → 在提示词中附加警告），支持 worktree 隔离执行（通过 `spec-env.json` 配置）。

### claude-code-spec-monitor
**角色：** 自主监控守护
**功能：** 用户离开时监控 Claude Code 执行。每 15 分钟检查一次，完成后自动停止：
1. 预检查 → 2. 初始化状态 → 3. 启动监控守护进程（15 分钟周期）→ 4. 报告状态

**周期逻辑 (snapshot.py cycle)：**
- 读取 `progress.json`（新鲜 = ≤15 分钟）；每个周期通过 `claude -p` 调用 LLM 进度检查器
- 新鲜 + is_complete=true → `ACTION: STOP` → 守护进程干净退出
- 降级（progress.json 过期/缺失）→ 调用检查器，记录 git/日志活动信号，不触发 STOP
- 通过 `ps` 中命令行包含 task_id 识别工作进程 — 无需 PID 文件

**关键设计：** 与 spec-driver 解耦。进度检查器是独立的 `claude -p` 进程（spec-task-progress skill）。所有运行时文件统一存于 `{SPEC_PATH}/`（`monitor-state.json`、`worker.log`、`daemon.pid`、`daemon.lock`）；`/tmp` 仅作为测试用 task ID 的降级回退。

---

## 最佳实践：使用 Spec 进行长周期开发

### 驱动 Claude Code 稳健执行任务

Spec 通过**状态驱动执行**机制实现可靠的长周期开发。以下是有效使用方式：

#### 执行模式

| 模式 | 触发方式 | 行为 | 适用场景 |
|------|---------|------|----------|
| **标准模式**（默认） | 用户每完成一个任务后说 "continue" / "next" | Claude Code 执行一个任务 → 更新 `tasks.md` → **停下来等待**用户审阅后再执行下一个 | 每步都需要审阅的复杂任务 |
| **连续模式** | 用户明确授权："你可以继续实现，不用问我" | Claude Code 自动推进 `[ ]` 任务。自动暂停条件：编译失败、用户修正≥2次、范围扩大、危险操作 | 用户要离开的已信任任务 |

> ⚠️ **重要**：模糊的确认如 "OK" / "继续" / "好的" **不会**激活连续模式。必须使用明确授权。授权不会在会话压缩后保留。

#### 长周期工作流

```
用户："实现支付网关 T-12345"
    ↓
Claude Code：判断为复杂类型 → 阶段1 (requirements.md)
    ↓
用户：确认 → 阶段2 (design.md)
    ↓
用户：确认 → 阶段3 (tasks.md，例如 8 个任务)
    ↓
用户："continue" → 任务1 [~] → 编码 → 验证 → [✓] → 提交 → 停止
    ↓
用户："next" → 任务2 [~] → 编码 → 验证 → [✓] → 提交 → 停止
    ↓
...（重复直到全部完成）
    ↓
Claude Code：全部 [✓] → 生成最终总结 → 停止等待用户确认
```

**为什么长周期开发有效：**
- **压缩免疫**：会话中断时，压缩恢复（6步流程）从 `tasks.md` + git 验证重构状态
- **不丢失进度**：`tasks.md` 是唯一可信来源；记忆是次要的
- **粒度控制**：标准模式下用户审阅每次提交；连续模式下任何异常自动暂停

---

### 通过 Agent 进行远程监督

当你需要离开但希望 Claude Code 继续工作时，使用 **monitor** 组件：

#### 简单语音指令

| 你想做什么 | 告诉 Agent |
|---------------|----------------|
| 查看任务进度 | "task progress" / "586742 progress" |
| 让 Claude Code 继续开发 | "continue 586742" / "keep going" |
| **启动远程监督** | "monitor 586742" / "watch dog" |
| 查看监督状态 | "monitor status" |
| 停止监督 | "stop monitor 586742" |

#### 监督机制如何工作

```
用户："monitor 586742"（进度：3/8，37%）
    ↓
Agent：1) 验证任务和进度  2) 检查 Claude Code 可用性
    ↓
Agent：启动监控守护进程（15 分钟周期）
    ↓
监控守护进程（每 15 分钟）：
    ├─ progress.json 新鲜 + is_complete=true？ → STOP（守护进程退出）
    ├─ progress.json 新鲜 + 进行中？           → 终止旧检查器 → 调用新检查器
    └─ progress.json 过期或缺失？              → 调用新检查器，记录活动信号
    ↓
全部任务完成 → 停止：守护进程干净退出
```

**监督期间发生了什么：**
- Claude Code 以**连续模式**自主运行（自动推进任务）
- 每 15 分钟，守护进程调用 LLM 进度检查器并读取 `progress.json`
- 进度检查器解析 `tasks.md` 并原子写入结构化 `progress.json`
- 全部任务完成时，守护进程检测到新鲜 progress.json 中 `is_complete=true` → 退出

**关键设计要点：**
- 无重启逻辑 — 守护进程负责监控，Claude Code 工作进程自主驱动
- 通过命令行中的 task_id 识别工作进程（无 PID 文件）
- 工作区保护：未提交变更会在启动提示词中触发警告

---

### 端到端示例：35 任务重构项目

```
第1天  上午：用户创建 spec T-586742（解除 service-foundation 依赖）
         ↓
         阶段1-3：requirements.md → design.md → tasks.md（35 个任务）
         ↓
第1天  下午：用户说 "continue 586742" → 标准模式
         ↓
         任务 1-5：执行 → [✓] → 提交 → 等待 "next"
         ↓
第2天  上午：用户说 "monitor 586742" → 去开会
         ↓
         Claude Code（连续模式）：任务 6-20 自动执行
         监督：每 15 分钟检查，每个周期调用 LLM 进度检查器
         ↓
第2天  傍晚：用户查看 "monitor status" → 进度 20/35（57%）
         用户说 "stop monitor" → 审阅变更 → "continue 586742"
         ↓
第3-4天：      标准模式：任务 21-35，每步用户审阅
         ↓
第4天  傍晚：  全部 [✓] → 最终总结 → spec 完成
```

> **经验法则**：前几个任务用标准模式建立信任。中间批量用 monitor 监督。最后关键任务回到标准模式。

---

## 设计原则

在自定义或扩展 Spec Stateflow Kit 之前，应理解以下架构原则：

1. **追踪器即真相** — `tasks.md` 是唯一可信来源。记忆和对话是次要的。冲突时暂停并对账。
2. **确认关卡** — 每个阶段转换（1→2→3→4）都需要用户明确确认。不允许自主跳过阶段。
3. **压缩免疫** — 会话中断不会丢失进度。6 步压缩恢复流程从 `tasks.md` + git 验证重构状态。
4. **连续模式是 opt-in** — 仅当用户明确授权（"你可以不用问就继续"）时才自动推进。模糊的 "OK" 被忽略。
5. **一个追踪器对应一个需求** — 绝不在一个 `tasks.md` 中混合不同需求的任务。使用独立的 `{SPEC_PATH}` 目录。
6. **验证先于 [✓]** — 任务仅在程序化验证通过后才标记完成（编译、测试、grep）。绝不追溯。
7. **监控解耦** — monitor 依赖 driver 生成提示词，但不依赖其监控逻辑。两者可独立替换。

---

## 快速开始示例

以下是典型任务在 Spec 系统中的完整流程，从分类到完成：

### 场景："添加新的支付网关集成"

**步骤1 — 分类** → Agent 判断：多模块 / API 变更 / 需要设计 → **复杂类型 → 进入 Spec 工作流**

**步骤2 — 阶段1（需求）** → Agent 用 EARS 语法编写 `requirements.md` → 用户确认 → ✅ 继续

**步骤3 — 阶段2（设计）** → Agent 编写 `design.md`，包含架构、API 签名、数据库模式 → 用户确认 → ✅ 继续

**步骤4 — 阶段3（任务）** → Agent 拆解为 `tasks.md` 中的 8 个任务：
```
- [ ] 1. 创建 PaymentGateway 接口
- [ ] 2. 实现 Stripe 适配器
- [ ] 3. 添加 webhook 端点
- [ ] 4. 编写单元测试
- [ ] 5. 更新 API 文档
- [ ] 6. 添加数据库迁移
- [ ] 7. 沙箱集成测试
- [ ] 8. 更新部署配置
```
用户确认 → ✅ 继续

**步骤5 — 阶段4（执行）** → Agent 顺序执行任务：
```
任务1：标记 [~] → 编码 → 验证 → 标记 [✓] → 提交 → 停止等待审阅
用户："next"
任务2：标记 [~] → 编码 → 验证 → 标记 [✓] → 提交 → 停止等待审阅
...
```

**步骤6 — 完成** → 全部 `[✓]`。Agent 生成总结。用户确认。Spec 工作流完成。

---

## 相关文档

| 文档 | 内容 |
|------|------|
| `Installation.md` | 分步安装、验证与卸载 |
| `spec-stateflow/SKILL.md` | 完整四阶段工作流规范、状态机、压缩恢复 |
| `spec-task-progress/SKILL.md` | 查询任务进度的命令 |
| `claude-code-spec-driver/SKILL.md` | 如何启动 Claude Code 进行持续开发 |
| `claude-code-spec-monitor/SKILL.md` | 完成时自动停止，降级模式下记录活动信号 |
| `spec-stateflow-kit-installer/SKILL.md` | 生命周期管理：安装/卸载 |

---

## 术语表

| 术语 | 定义 |
|------|------|
| **Spec** | "specification" 的简称。一种结构化开发工作流，强制复杂任务经过需求→设计→任务→执行流程。 |
| **tasks.md** | 任务进度的唯一可信来源。包含带状态标记的任务列表（`[ ]`、`[~]`、`[✓]`、`[⏭]`）、范围、具体内容和验证方式。 |
| **压缩恢复** | 会话中断或记忆压缩后恢复上下文的 6 步流程。读取 `tasks.md`，验证最后完成的任务，然后续接。 |
| **连续操作模式** | 一种 opt-in 执行模式，Claude Code 在每次提交后自动推进到下一个任务，无需等待用户确认。 |
| **EARS** | Easy Approach to Requirements Syntax。结构化需求格式："当 [触发条件] 时，[系统] 应 [响应]。" |
| **{SPEC_PATH}** | 单个 spec 的完整目录路径：`{WORKSPACE}/{DOC_DIR}/{TaskID}-{Description}/`。 |
| **卡死检测** | monitor 的降级模式活动检查：当 progress.json 缺失或过期时，守护进程记录 git 提交变化、工作区变化和日志文件增长作为活动信号 — 仅供参考，不触发重启。 |
| **用户修正** | 计数器，记录用户纠正 Agent 假设的次数。≥2 触发升级处理。 |

---

## 常见问题与常见误区

### 常见问题

| 问题 | 回答 |
|----------|--------|
| 简单的配置变更可以用 Spec 吗？ | 不行。简单变更（单文件/单方法/无需设计）应直接执行，无需 Spec。参见 `spec-stateflow` skill 中的**任务分类**。 |
| `tasks.md` 损坏了怎么办？ | 遵循 `spec-stateflow` 阶段4 中的**压缩恢复**。Agent 会从 `design.md` 手动重建 `tasks.md`（不存在自动化脚本）。重大变更前务必备份 `tasks.md`。 |
| 可以并行运行多个 spec 吗？ | 不行。每个需求一个 `tasks.md`。创建独立的 `{SPEC_PATH}` 目录。绝不在一个追踪器中混合不同 spec 的任务。 |
| 如何在两个活跃 spec 之间切换？ | 暂停当前（标记 `[~]`），为新工作创建新追踪器。返回时，按压缩恢复步骤2重新验证最后一个 `[✓]` 行。 |
| 没有 git 时 monitor 能工作吗？ | 能。卡死检测在无 git 时回退到仅追踪进度。但 git 状态变更检测将被禁用。 |

### 常见误区

1. **追溯更新追踪器** — 会话压缩后未先验证代码状态就写 `[✓]`。务必先按压缩恢复步骤2重新验证。
2. **跳过阶段1-2** — 未经确认的需求/设计直接跳到 `tasks.md`。这会导致范围蔓延和返工。
3. **混用 spec 目录** — 把多个需求放进一个 `tasks.md`。务必将不同需求分离到不同的 `{SPEC_PATH}` 目录。
4. **模糊激活连续模式** — 说 "OK" 或 "继续" **不会**激活连续模式。必须明确说 "你可以不用问就继续实现"。
5. **忽略未提交变更警告** — driver 会在提示词中附加工作区保护，但 Claude Code 如不注意仍可能意外丢弃变更。务必先检查 `git status`。
