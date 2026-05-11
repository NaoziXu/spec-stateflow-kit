# Implementation Plan

- [✓] 1. 分析现有代码结构
  - Scope: `src/legacy/`
  - Specifics: 梳理旧代码依赖关系，整理模块边界

- [✓] 2. 设计新接口
  - Scope: `src/api/interface.py`
  - Specifics: 定义新的抽象接口，与旧实现解耦

- [⏭] 3. 迁移旧版数据格式
  - Scope: `scripts/migrate_v1.py`
  - Specifics: 用户决定跳过历史数据迁移，直接使用新格式

- [⏭] 4. 向下兼容适配层
  - Scope: `src/compat/adapter.py`
  - Specifics: 用户决定不需要兼容旧版 API，直接切换新版本

- [ ] 5. 实现新接口
  - Scope: `src/api/impl.py`
  - Specifics: 按照新设计实现所有接口方法

- [ ] 6. 编写测试
  - Scope: `tests/test_new_api.py`
  - Specifics: 单元测试和集成测试覆盖新接口
