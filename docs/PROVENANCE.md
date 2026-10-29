# 来源与协作说明

本仓库用于展示电商问答需求下的 AI 协作实践、运行适配与验证结果。

## 基础代码

- 基础仓库：[Manchenlin/Itcast_dianshang_RAG_vibeCoding](https://github.com/Manchenlin/Itcast_dianshang_RAG_vibeCoding)。原用户名为 `linmanhzy`，旧链接当前重定向到上述地址。
- 基线提交：`1ee3b35e7e38deb370376ad3134af61578d3ab16`；本机获取日期为 2026-09-08。原始来源记录见 [source.json](source.json)。
- 这是原作者公开的课程实践代码。登录、多会话、知识库管理及前后端基础结构来自该基线；本仓库没有把这些基础模块重新声明为本人从零独立编写。
- 本机后续版本增加运行适配、本地向量模型、错误处理、隔离测试和可恢复快照等。公开副本进一步整理作品说明与可直接阅读的问答证据。
- 本人负责需求描述、试用反馈和方向选择；机械实现、环境配置与验证有 AI 协助。各项具体改动以代码和验证记录为准。

上游未提供明确的仓库级许可证，本展示仓库不另行授予上游代码的开源许可，也不代表上游作者或官方产品。

## 向量模型

- 转换模型：[onnx-community/bge-m3-ONNX](https://huggingface.co/onnx-community/bge-m3-ONNX/tree/25b9af8e87a38eb120cfe87125383677b9cd309e)。
- 固定版本：`25b9af8e87a38eb120cfe87125383677b9cd309e`。
- 基础模型：[BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3)。上游模型卡标注 MIT。
- 模型文件未训练或修改；仅将其中的稠密向量能力接入本地项目。逐文件校验值见 [embedding-model.json](embedding-model.json)。
- 模型及相关许可材料见 [MODEL_NOTICE.md](MODEL_NOTICE.md)。

## 演示数据

商品与售后规则是合成演示资料。公开的问答为真实模型调用后保存的记录；此次公开整理没有改写历史回答。完整消息、来源片段、数据库和索引与原快照保持一致。
