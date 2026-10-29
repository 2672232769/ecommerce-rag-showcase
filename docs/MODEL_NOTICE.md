# 模型来源与许可材料

本项目使用 **BAAI/bge-m3** 的 **onnx-community/bge-m3-ONNX** 转换版本，仅下载并调用模型，没有进行训练或微调。

- 转换版本：[固定提交](https://huggingface.co/onnx-community/bge-m3-ONNX/tree/25b9af8e87a38eb120cfe87125383677b9cd309e)。
- 基础模型：[BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3)。
- 2026-10-29 查询到两个模型卡均标注 MIT，元数据保存于 [model-license-metadata.json](model-license-metadata.json)。
- 模型上游相关实现 FlagEmbedding 的 MIT 原始文本保存在 [LICENSE-FlagEmbedding.txt](LICENSE-FlagEmbedding.txt)，其中的版权信息保持原样；该文件的来源是 [FlagOpen/FlagEmbedding/LICENSE](https://github.com/FlagOpen/FlagEmbedding/blob/master/LICENSE)。模型仓库本身未单独提供 LICENSE 文件，故明确保留模型卡与相关实现许可的区别。

Release 的 `bge-m3-onnx-int8.zip` 内为未经修改的 4 个模型文件，逐文件 SHA-256 见 [embedding-model.json](embedding-model.json)。本说明及许可文本同时作为 Release 附件提供。模型的 MIT 信息不表示本仓库所有应用代码也采用 MIT。

压缩包 SHA-256：`c03fec1d1a17ffbce902a7cfde52e08fff150803002b259422fd7925255be005`。
