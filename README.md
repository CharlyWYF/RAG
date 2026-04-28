# RAG 网络协议问答 系统

这是一个 RAG 系统：

- 本地文档：网络协议知识（Markdown/TXT）
- 向量库：Chroma（本地持久化）
- 模型：OpenAI API（Embedding + Chat）
  - 也支持第三方 OpenAI 兼容接口（通过 `OPENAI_BASE_URL` 配置）
- 页面：Streamlit

## 0. 当前知识库策略

当前项目采用“纯 RFC”路线，知识库仅使用 RFC 标准文档，不引入教程型资料作为正式语料。

当前分阶段范围如下：

- 第一批核心协议：`TCP`、`DNS`、`HTTP`
- 第二批补充协议：`IP`、`UDP`
- 第三批扩展协议：`TLS`、`HTTP/2`

详细范围说明见：

- `docs/rfc_scope.md`
- `docs/rfc_cleaning_rules.md`

## 1. 环境准备

### 方式 A：conda（推荐）

```bash
conda create -n rag-demo python=3.11 -y
conda activate rag-demo
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2. 配置 API Key

1. 如果仓库中已提供模板文件，复制模板并填写 key：

```bash
cp .env.example .env
```

2. 如果仓库中暂未提供 `.env.example`，请手动创建 `.env`

3. 编辑 `.env`，设置 `OPENAI_API_KEY=...`

可选但支持：

- `OPENAI_BASE_URL=https://your-gateway.example.com/v1`
- `QUERY_REWRITE_MODEL` 用于控制查询改写阶段所使用的模型

## 3. 准备知识库

当前项目优先处理本地 `data/protocols/raw/` 下的 RFC 文档。

### 推荐工作流

1. 按 `docs/rfc_scope.md` 确定当前纳入范围的 RFC
2. 对 RFC 原文做轻量清洗

```bash
python scripts/clean_protocol_docs.py --raw-dir data/protocols/raw --output-dir data/protocols/cleaned
```

清洗后的输出默认放到：

- `data/protocols/cleaned/`

清洗脚本会：

- 去掉部分 RFC 页眉、页脚、分页和目录等噪音
- 保留正文结构和章节信息
- 为每个文件补充来源信息（protocol / kind / source_url）

3. 让建库使用 cleaned 目录（推荐）

你可以在 `.env` 中把：

```env
DATA_DIR=data/protocols/cleaned
```

然后再执行 `sync` 或 `rebuild`。

## 4. 构建向量索引

推荐从项目根目录运行：

```bash
python -m src.ingest
```

成功后会生成 `chroma_db/`。
默认是 **rebuild + fixed chunk** 模式：会先重建索引目录（删除旧的 `chroma_db/`），避免重复写入导致检索片段重复。

### Chunk 策略

当前建库支持三种 chunk 策略：

- `fixed`：固定长度切分，保留现有通用方案
- `section`：按 Markdown 标题切分，适合清洗后的 RFC 文档
- `hybrid`：先按标题切分，再对过长 section 做固定长度二次切分

推荐对清洗后的 RFC 文档优先尝试：

- `fixed`：作为基线方案
- `hybrid`：作为主推荐方案

例如：

```bash
python -m src.ingest --mode rebuild --chunk-strategy fixed
python -m src.ingest --mode rebuild --chunk-strategy section
python -m src.ingest --mode rebuild --chunk-strategy hybrid
```

如需“让向量库与当前文件保持一致（新增/更新/删除）”，使用：

```bash
python -m src.ingest --mode sync --chunk-strategy fixed
```

`sync` 模式会：

- 新增文件：写入向量库
- 已修改文件：先删除旧向量再写入新向量
- 已删除文件：删除对应旧向量

如需增量追加（保留旧库并添加新文档），使用：

```bash
python -m src.ingest --mode append --chunk-strategy fixed
```

`append` 模式会按 `source`（文件路径）去重：

- 已在向量库中存在的来源文件会跳过
- 仅新增来源文件会被切分并写入
- 不会处理“文件内容更新”和“文件删除”

## 5. 网页端知识库管理

页面现在分为三个标签：

- `问答`：原有提问与回答流程
- `知识库管理`：管理原始文件并触发建库
- `系统配置`：查看当前生效配置并编辑 `.env` 中的关键字段

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

当前仓库的正式知识库方向仍是“纯 RFC”。上述上传与建库能力支持通用 `.md`/`.txt` 文件处理，但在正式语料选择上，应优先遵循 `docs/rfc_scope.md` 与 `docs/rfc_cleaning_rules.md`。

## 6. 启动网页

```bash
streamlit run app.py
```

页面顶部有“测试 API 连通性”按钮：

- 成功：显示当前 chat/embedding model 与 base\_url
- 失败：直接显示错误信息，便于排查 key、base\_url、模型名是否可用

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
- `data/protocols/raw/`：原始协议文档
- `data/protocols/cleaned/`：清洗后的协议文档

## 8. 注意事项

- `.env` 不要提交到仓库。
- 若提示找不到向量库，请先运行 `python -m src.ingest`。
- 若回答不理想，优先补充/改进文档质量。

 