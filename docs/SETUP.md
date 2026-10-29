# 安装、恢复数据和启动

## 换电脑或从 GitHub 恢复

### 1. 获取仓库并安装依赖

准备 Git、Python 3.12、uv、Node.js 20 与 npm。安装依赖需要联网；Windows 安装 Chroma 的 hnswlib 如果需要本地编译，还需 Microsoft C++ Build Tools。

仓库与 Release 附件均公开。在 PowerShell 中执行：

```powershell
git clone https://github.com/2672232769/ecommerce-rag-showcase.git
cd ecommerce-rag-showcase
.\setup_local.bat
```

安装脚本会创建 Python 虚拟环境，用锁定文件安装依赖并构建前端。确认没有报错后继续。

### 2. 创建本机私密配置

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\init_local_config.py
```

按提示设置新的管理员密码。脚本生成随机 JWT 密钥；已有 `backend/.env` 时退出，不覆盖配置。然后编辑 `backend/.env`，填写自己的聊天服务 API 密钥：

```dotenv
OPENAI_API_KEY=填写自己的密钥
OPENAI_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-v4-flash
LLM_THINKING=disabled
EMBEDDING_PROVIDER=local_onnx
EMBEDDING_LOCAL_PATH=../models/bge-m3-onnx-int8
ADMIN_USERNAME=admin
```

`LLM_MODEL` 是此项目保存的配置名称，必须确保你的服务商账号实际支持；可以换成支持的聊天模型。换其他兼容服务时，一并修改 API 根地址，并按服务商要求调整或清空 `LLM_THINKING`。保留新生成的 `JWT_SECRET` 和刚设置的 `ADMIN_PASSWORD`。**不要把 .env 提交到 GitHub。**

### 3. 恢复本地模型

任选一种方式：

- 在 [Release 页面](https://github.com/2672232769/ecommerce-rag-showcase/releases/tag/local-snapshot-20261029)下载 `bge-m3-onnx-int8.zip`，放到项目根目录后执行：

  ```powershell
  Expand-Archive .\bge-m3-onnx-int8.zip -DestinationPath .
  ```

- 或从固定上游版本下载并校验：

  ```powershell
  .\backend\.venv\Scripts\python.exe .\scripts\download_embedding_model.py
  ```

最终应有 `models/bge-m3-onnx-int8/onnx/model_int8.onnx`、`tokenizer.json`、`tokenizer_config.json`、`config.json`。模型约 558 MiB，使用 CPU，启动时加载到内存。逐文件校验见 [embedding-model.json](embedding-model.json)，Release 压缩包校验见 [github-backup.json](github-backup.json)。

### 4. 恢复知识库、数据库和聊天

**先恢复，后启动。backend/data 必须不存在或为空。**

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\restore_snapshot.py .\snapshots\20261029
```

脚本校验压缩包、文件 SHA-256、数据库完整性和记录数量，将数据恢复到 `backend/data/`，并将快照中的 `admin` 密码设为本机 `.env` 的 `ADMIN_PASSWORD`。原历史消息、引用和知识库会保留，旧密码不会恢复。

脚本拒绝覆盖已有数据。如果已有数据，请先停服并另行保存旧数据；也可以先恢复到新的检查目录：

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\restore_snapshot.py .\snapshots\20261029 --target .\restored-preview\data
```

本次快照只有一个管理员。其他快照如果含普通用户，普通用户的密码需要另行重设。

### 5. 启动并体验

```powershell
.\start_local.bat
```

打开 <http://127.0.0.1:8018/>，使用 `admin` 和刚设置的密码登录。先查看已有历史会话，再试着提问“请列出知识库中的商品及价格”。示例商品资料为虚构学习数据。

服务仅监听本机 `127.0.0.1:8018`。新回答需要可用的外部模型 API 和网络；本地向量计算、历史会话浏览使用本地数据。API 文档：<http://127.0.0.1:8018/docs>。


## 同机已有旧版本时

本项目默认使用 8018 端口。如果已有另一个版本占用该端口，先用那个版本自己的停止脚本关闭它，再启动本副本。公开副本不会停止其他项目进程。不同副本各自保留数据目录。

## 修改与检查

前端修改后，在 `frontend` 执行 `npm run build`。后端修改后用本副本的 `stop_local.bat`、`start_local.bat` 重启。停止不会删除数据。

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q
```

这些测试使用隔离数据库和模型替身。`/api/health` 只描述配置状态；需要真实模型连通验证时，可运行 `scripts/check_model.py`，它会使用你配置的模型服务。

## 更新数据快照

停止本副本后运行 `scripts/create_snapshot.py`。导出前后应检查新增聊天与上传资料是否适合公开。已有展示快照中的会话及文档已获项目所有者授权发布；今后新增内容不会自动获得相同授权。
