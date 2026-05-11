# Implementation Plan

- [✓] 1. 更新 spec-stateflow/SKILL.md 添加机器解析契约
  - Scope: `spec-stateflow-kit/spec-stateflow/SKILL.md`
  - Affected: —
  - Specifics: 状态标记仅允许 [ ] [~] [✓] [⏭] 四种，禁止其他字符。在 Phase 3 Task Format Reference 章节之后，Phase 4 之前新增独立章节"Machine Parsing Contract"。
  - Verification: 阅读修改后的 SKILL.md，确认新章节位置正确、约束内容完整
  - User corrections: —
  - Notes: 若出现 [ ] 或 [✓] 应视为文字说明，不计入进度。例如 [~] 表示进行中，[ ] 表示未开始，[⏭] 表示跳过。

- [ ] 2. 迭代 spec-task-progress/SKILL.md
  - Scope: `spec-stateflow-kit/spec-task-progress/SKILL.md`
  - Affected: —
  - Specifics: 当任务状态为 [~] 时，表示进行中；当为 [ ] 时，表示未开始；当为 [✓] 时，表示已完成。新增双环境路径解析说明、进度查询流程、progress.json schema、测试功能触发 prompt 等内容。参见设计文档中对 [✓] 和 [⏭] 的说明。
  - Verification: 确认 SKILL.md 包含所有必需章节
  - User corrections: —
  - Notes: 依赖任务 1 完成
