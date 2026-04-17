# RAG 网络协议问答 Demo（Python + Streamlit）

这是一个最小 RAG Demo：
- 本地文档：网络协议知识（Markdown/TXT）
- 向量库：Chroma（本地持久化）
- 模型：OpenAI API（Embedding + Chat）
  - 也支持第三方 OpenAI 兼容接口（通过 `OPENAI_BASE_URL` 配置）
- 页面：Streamlit

## 1. 环境准备
 
### 方式 A：conda（推荐）

```bash
conda create -n rag-demo python=3.11 -y
conda activate rag-demo
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2. 配置 API Key

1. 复制模板并填写 key：

```bash
cp .env.example .env
```

2. 编辑 `.env`，设置 `OPENAI_API_KEY=...`

如果你使用第三方兼容 OpenAI 的 API 网关，再设置：
- `OPENAI_BASE_URL=https://your-gateway.example.com/v1`

## 3. 准备知识库

示例文档放在 `data/protocols/` 下，你可继续添加 `.md` 或 `.txt` 文件。

如果你不想自己写内容，推荐采用“**教程型资料为主 + 少量 RFC 为辅**”的方式准备知识库，而不是只导入 RFC 原文。

### 推荐工作流

1. 下载精选资料（教程/规范可分开）

```bash
python scripts/download_protocols.py --kind tutorial
python scripts/download_protocols.py --kind spec
```

也可以按协议过滤，例如：

```bash
python scripts/download_protocols.py --kind tutorial --protocol tcp,http,dns
```

下载后的原始资料默认放到：
- `data/protocols/raw/`

2. 对下载资料做轻量清洗

```bash
python scripts/clean_protocol_docs.py
```

清洗后的输出默认放到：
- `data/protocols/cleaned/`

清洗脚本会：
- 去掉部分固定格式的 RFC 页眉/页脚冗余行
- 保留正文结构
- 为每个文件补充来源信息（protocol / kind / source_url）

3. 让建库使用 cleaned 目录（推荐）

你可以在 `.env` 中把：

```env
DATA_DIR=data/protocols/cleaned
```

然后再执行 `sync` 或 `rebuild`。

## 4. 构建向量索引

```bash
python -m src.ingest
```

成功后会生成 `chroma_db/`。
默认是 **rebuild 模式**：会先重建索引目录（删除旧的 `chroma_db/`），避免重复写入导致检索片段重复。

如需“让向量库与当前文件保持一致（新增/更新/删除）”，使用：

```bash
python -m src.ingest --mode sync
```

`sync` 模式会：
- 新增文件：写入向量库
- 已修改文件：先删除旧向量再写入新向量
- 已删除文件：删除对应旧向量

如需增量追加（保留旧库并添加新文档），使用：

```bash
python -m src.ingest --mode append
```

`append` 模式会按 `source`（文件路径）去重：
- 已在向量库中存在的来源文件会跳过
- 仅新增来源文件会被切分并写入
- 不会处理“文件内容更新”和“文件删除”

## 5. 网页端知识库管理（新增）

页面现在分为两个标签：
- `问答`：原有提问与回答流程
- `知识库管理`：管理原始文件并触发建库

在“知识库管理”中你可以：
- 查看当前配置和状态（`data_dir`、`chroma_dir`、chunk 参数、原始文档数、向量库就绪状态）
- 上传 `.md/.txt` 文件到知识库目录
- 删除指定原始文件（带确认）
- 选择 `sync` / `rebuild` / `append` 模式构建向量库
- 查看本次建库结果（总文档、写入/跳过、新增/更新/删除/未变化文档、写入/删除 chunk、持久化目录）

模式说明：
- `sync`：让向量库与当前源文件保持一致（新增/更新/删除都会同步）
- `rebuild`：会先删除旧向量库再重建
- `append`：仅追加新增来源文件（按 `source` 去重，不处理更新和删除）

## 6. 启动网页

```bash
streamlit run app.py
```

页面顶部有“测试 API 连通性”按钮：
- 成功：显示当前 chat/embedding model 与 base_url
- 失败：直接显示错误信息，便于排查 key、base_url、模型名是否可用

问答区域会展示可观测性信息：
- 实时执行日志（按阶段滚动）
- 各环节耗时明细（表格）
- 端到端总耗时（metric）

打开页面后输入问题，例如：
- TCP 三次握手是什么？
- UDP 和 TCP 的区别？
- HTTP 404 表示什么？
- DNS 解析流程是怎样的？

## 7. 项目结构

- `app.py`：Streamlit 入口
- `src/config.py`：环境配置读取
- `src/ingest.py`：离线建库
- `src/retriever.py`：向量检索封装
- `src/qa.py`：RAG 问答逻辑
- `data/protocols/`：协议知识文档

## 8. 注意事项

- `.env` 不要提交到仓库。
- 若提示找不到向量库，请先运行 `python -m src.ingest`。
- 若回答不理想，优先补充/改进文档质量。
