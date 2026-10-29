# 验证与数据完整性

## 已保存的真实问答证据

2026-09-08，外部聊天服务与本地 BGE-M3 ONNX INT8 完成了商品资料问答验证。六次初始问答、两次提示词调整后的复测及重启后的历史记录检查保存在：

- [deepseek-live.json](qa/deepseek-live.json)
- [deepseek-answer-scope.json](qa/deepseek-answer-scope.json)
- [完整聊天](../snapshots/20261029/conversations.md)

这些记录使用真实外部模型，`uses_test_doubles=false`。它们是历史运行证据，本次公开整理没有重新调用付费聊天模型。

## 2026-10-29 公开整理

已只读比较原应用与快照中的 `chat_sessions`、`chat_messages`、`knowledge_documents`，所有行一致。保留 1 个用户、3 个会话、16 条消息、1 份文档。原快照的文件和完整消息均保留，不删除旧回答或失败改进的上下文。

公开副本重新运行隔离测试，并在新目录恢复快照、检查 SQLite 完整性、管理员密码重设与 Chroma 向量读取。结果见 [publication-check.json](publication-check.json)。测试使用模型替身，不将其视为真实模型正确性的证据。

前端源代码与已构建快照对应的本地版本一致；本次也重新构建公开副本，结果见同一检查记录。真实浏览器端的完整点击流程仍未验收。

## 验证边界

数据快照只能证明保存和恢复了当时的数据。小型知识库中的几个问题不能证明普遍问答准确率、复杂文档解析能力、并发性能或生产可用性。当前公开内容是代码与数据展示，不是公开运行的在线 API 服务。
