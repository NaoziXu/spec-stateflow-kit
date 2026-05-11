# Prompt Templates

---

## Installer (spec-stateflow-kit — Claw Agent)

### Scene 0: Install Spec Kit

Use this when setting up Spec for the first time. Replace the path with the actual kit location on your system.

```
Help me install the spec kit, the kit directory is at /Users/yourname/Desktop/spec-stateflow-kit
```

### Scene 1: Uninstall Spec Kit

Use this to remove the spec kit and all its components from your system.

```
Help me uninstall the spec kit
```

---

## Spec Workflow (spec-stateflow — Claude Code)

### Scene 2: Write Spec Documents

Use this when you have a new complex task and need to generate requirements, design, and task breakdown documents before coding.

```
Please write a complete set of spec documents for the following development task.
Task ID: {taskId}
Requirements: {requirements}
Please generate documents in the spec directory for this requirement.
```

### Scene 3: Execute Spec Tasks — Standard Mode (stop-and-wait for each task)

Use this when spec documents are ready and you want to review and approve each task one by one before it proceeds.

```
I have already generated documents through spec-stateflow. Please continue development based on the existing task documents.
Task ID: {taskId}
Please execute tasks one by one. After completing each task:
1. Update tasks.md and mark the corresponding task status
2. Fill in the Verification and Commit fields
3. Stop and wait for my review and explicit approval before proceeding to the next task. Do not auto-advance.
```

### Scene 4: Execute Spec Tasks — Continuous Mode (autonomous execution)

Use this when you want Claude Code to execute all tasks autonomously without stopping for confirmation. It is recommended to submit this prompt multiple times into the queue — if the session drops due to LLM provider instability, it will reconnect automatically.

```
I have already generated documents through spec-stateflow. Please continue development based on the existing task documents.
Task ID: {taskId}
You need to first check and update the spec documents to the latest progress, ensuring the task status in tasks matches the actual engineering state.
After that, continue implementation autonomously using continuous mode without requiring my confirmation.
Note: After completing each small task, promptly update the progress in tasks.md, submit a git commit, and then proceed to the next task.
```

---

## Progress Query (spec-task-progress — Claw Agent)

### Scene 5: Query Task Progress

Use this to check how many tasks are completed and what the next pending task is.

```
Help me check the development progress of the spec task
Task ID: {taskId}
```

### Scene 6: Test spec-task-progress Skill

Use this after installation or when troubleshooting to verify the progress query skill works correctly.

```
Test the spec-task-progress skill
```

---

## Spec Driver (claude-code-spec-driver — Claw Agent)

### Scene 7: Drive Task Development

Use this to have Claw Agent launch Claude Code and start or continue developing a specific task.

```
Help me launch Claude Code to develop the task
Task ID: {taskId}
```

### Scene 8: Test spec-driver Skill

Use this to verify the spec driver skill is installed and working correctly.

```
Test the claude-code-spec-driver skill
```

---

## Monitor (claude-code-spec-monitor — Claw Agent)

### Scene 9: Continuously Monitor Task Development

Use this when you want to step away while Claude Code keeps running. The monitor checks progress every 15 minutes and stops automatically when the task is complete.

```
Help me supervise Claude Code to continue developing the task until development is complete
Task ID: {taskId}
```

### Scene 10: Stop Monitoring

Use this to manually stop an active monitoring session.

```
Stop the spec supervision task for Claude Code
Task ID: {taskId}
```

### Scene 11: Check Monitor Status

Use this to check whether the monitoring daemon is running and view its current status.

```
Check the spec supervision task status for Claude Code
```

### Scene 12: Restart Monitoring

Use this when the monitoring daemon exited abnormally or was manually interrupted. The project directory does not need to be re-confirmed.

```
Restart the spec supervision task for Claude Code
Task ID: {taskId}
```

### Scene 13: Test Monitor Scripts

Use this after installation, after environment migration, or when troubleshooting to verify the monitor scripts work correctly.

```
Test whether the claude-code-spec-monitor scripts are working correctly
```

---
---
---

# 提示词模板

---

## 安装管理（spec-stateflow-kit — Claw Agent）

### 场景0：安装 Spec 套件

首次使用时执行。将路径替换为 kit 在你系统上的实际位置。

```
帮我安装spec套件，kit 目录在 /Users/yourname/Desktop/spec-stateflow-kit
```

### 场景1：卸载 Spec 套件

将 spec 套件及其所有组件从系统中彻底移除时使用。

```
帮我卸载spec套件
```

---

## Spec 工作流（spec-stateflow — Claude Code）

### 场景2：编写 Spec 文档

有新的复杂任务、需要在编码前生成需求、设计和任务分解文档时使用。

```
请为以下开发任务编写一套完整的 spec 文档。
任务编号：{taskId}
需求内容：{requirements}
请在spec文档目录中生成针对这个需求编写文档。
```

### 场景3：执行 Spec 任务 — 标准模式（逐条停等确认）

Spec 文档已就绪、希望逐条审批每个任务后再推进时使用。

```
我已经通过 spec-stateflow 生成了文档。请基于现有任务文档继续开发。
任务编号：{taskId}
请逐条执行任务。每完成一条后：
1. 更新 tasks.md，将对应任务状态进行标记
2. 填写 Verification 和 Commit 字段
3. 停下来，等我 review 并明确批准后再继续下一条，不要自动推进。
```

### 场景4：执行 Spec 任务 — 连续模式（自主执行）

希望 Claude Code 自主完成所有任务、无需逐条确认时使用。建议将提示词多次提交进入队列，LLM 服务中断后可自动重连。

```
我已经通过 spec-stateflow 生成了文档。请基于现有任务文档继续开发。
任务编号：{taskId}
你需要先检查并更新spec文档至最新进度，在确保tasks的任务状态和实际工程中一样。
之后你需要自主使用连续作业模式继续实现，过程不需要我确认。
注意每完成一个小任务后，及时更新tasks文档进度，并提交git commit，然后继续下一条。
```

---

## 进度查询（spec-task-progress — Claw Agent / Claude Code）

### 场景5：查询任务进度

查看某个任务已完成了多少条、下一条待执行的是什么时使用。

```
帮我看一下spec任务的开发进度
任务编号：{taskId}
```

### 场景6：测试 spec-task-progress skill

安装后或排查问题时，验证进度查询 skill 是否正常工作时使用。

```
测试一下spec-task-progress skill
```

---

## Spec 驱动（claude-code-spec-driver — Claw Agent）

### 场景7：驱动任务开发

让 Claw Agent 调起 Claude Code、开始或继续开发某个任务时使用。

```
帮我调起Claude Code，对任务进行开发
任务编号：{taskId}
```

### 场景8：测试 spec-driver skill

验证 spec 驱动 skill 已正确安装并可正常运行时使用。

```
测试一下claude-code-spec-driver skill
```

---

## 监控（claude-code-spec-monitor — Claw Agent）

### 场景9：持续监控任务开发

需要离开让 Claude Code 继续运行时使用。监控每 15 分钟检查一次进度，任务完成后自动停止。

```
帮我对Claude Code进行监督，对任务持续进行开发，直到开发完成为止
任务编号：{taskId}
```

### 场景10：停止监控

手动终止当前正在运行的监控任务时使用。

```
停止Claude Code的spec监督任务
任务编号：{taskId}
```

### 场景11：查看监控状态

查看监控 daemon 是否在运行、当前状态如何时使用。

```
查看Claude Code的spec的监督任务状态
```

### 场景12：重启监控

监控 daemon 异常退出或被手动中断、需要重新接管时使用。无需重新确认项目目录。

```
重启Claude Code的spec监督任务
任务编号：{taskId}
```

### 场景13：测试监控脚本

安装后、环境迁移后或排查异常时，验证监控脚本是否正常工作时使用。

```
测试一下claude-code-spec-monitor脚本是否正常
```
