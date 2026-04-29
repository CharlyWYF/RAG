# 自动化脚本接口文档

本文档整理当前项目中已经完成前后端分离、适合被自动化脚本直接调用的核心接口。

目标：
- 方便后续编写批量实验脚本
- 明确哪些逻辑已经不依赖 Streamlit 页面
- 给后续 runner / evaluation / batch pipeline 提供可复用入口说明

---

## 1. 推荐调用层次

当前项目已经基本形成三层结构：

### 1.1 基础能力层
负责底层能力，不建议直接作为首选自动化入口：

- `src/config.py`
- `src/retriever.py`
- `src/qa.py`
- `src/ingest.py`
- `src/file_ops.py`
- `src/presentation.py`

### 1.2 业务编排层
这是自动化脚本最推荐直接调用的层：

- `src/qa_service.py`
- `src/ingest_service.py`
- `src/corpus_service.py`

### 1.3 前端层
- `app.py`

`app.py` 主要用于 Streamlit 页面交互，不建议自动化脚本直接依赖。

---

## 2. 问答业务接口

文件：`src/qa_service.py`

### 2.1 `execute_qa_flow(...)`

```python
execute_qa_flow(
    question: str,
    progress_callback: Callable[[str], None] | None = None,
    stream_handler: AnswerStreamHandler | None = None,
) -> dict[str, Any]
```

#### 作用
执行完整问答流程，包括：
- 加载配置
- 查询改写
- 初始化检索器
- 多路检索
- 文档去重
- 调用大模型生成最终回答
- 记录耗时与日志结构

#### 输入参数
- `question`：用户问题
- `progress_callback`：可选，执行阶段进度回调
- `stream_handler`：可选，用于接收流式输出事件

#### 返回结构
返回 `dict[str, Any]`，当前包含：

- `answer`：最终回答文本
- `contexts`：检索到的片段列表
- `sources`：来源文件列表
- `rewritten_queries`：查询改写生成的子查询列表
- `timings`：阶段耗时列表
- `total_seconds`：总耗时
- `logs`：流程阶段日志标记列表

#### `timings` 示例
```python
[
  {"stage": "load_settings", "seconds": 0.01},
  {"stage": "rewrite_query", "seconds": 1.23},
  {"stage": "init_retriever", "seconds": 0.15},
  {"stage": "retrieve", "seconds": 0.42},
  {"stage": "init_llm", "seconds": 0.05},
  {"stage": "first_token", "seconds": 2.11},
  {"stage": "generate_answer", "seconds": 5.38},
  {"stage": "total", "seconds": 7.29},
]
```

#### 典型用途
- 批量测试问题集
- 记录问答耗时
- 比较不同问题类型的系统表现
- 做论文实验数据采样

#### 最小示例
```python
from src.qa_service import execute_qa_flow

result = execute_qa_flow("HTTP/3 和 HTTP/2 的主要区别是什么？")
print(result["answer"])
print(result["sources"])
print(result["timings"])
```

---

### 2.2 `AnswerStreamHandler`

```python
class AnswerStreamHandler:
    def on_setup(self, question: str) -> None: ...
    def on_chunk(self, text: str) -> None: ...
    def on_first_token(self, seconds: float) -> None: ...
    def on_complete(self, answer: str) -> None: ...
```

#### 作用
给前端或脚本提供流式输出挂钩。

#### 适合场景
- 页面实时展示回答
- CLI 中实时打印 token / chunk
- 记录首字响应时间

#### 说明
如果自动化实验只关心最终结果，可以不传这个 handler。

---

## 3. 建库业务接口

文件：`src/ingest_service.py`

### 3.1 `run_ingest(...)`

```python
run_ingest(
    mode: str,
    chunk_strategy: str,
    progress_callback: Callable[[str, float | None], None] | None = None,
) -> tuple[dict[str, Any] | None, list[str], str | None]
```

#### 作用
执行完整向量库构建流程，并统一返回：
- 构建统计信息
- 运行日志
- 错误信息

#### 输入参数
- `mode`：`"sync" | "rebuild" | "append"`
- `chunk_strategy`：`"fixed" | "section" | "hybrid"`
- `progress_callback`：可选，接收阶段消息与进度百分比

#### 返回值
返回一个三元组：

```python
(stats, logs, error_message)
```

- `stats`：成功时为构建统计字典，失败时为 `None`
- `logs`：带时间戳的运行日志列表
- `error_message`：失败时错误文本，成功时为 `None`

#### `stats` 当前关键字段
- `mode`
- `docs_total`
- `docs_indexed`
- `skipped_docs`
- `added_docs`
- `updated_docs`
- `deleted_docs`
- `unchanged_docs`
- `chunks_written`
- `deleted_chunks`
- `timings`
- `total_seconds`
- `seconds_per_doc`
- `persist_dir`

#### `timings` 当前阶段
可能包括：
- `load_docs`
- `load_chroma`
- `split_docs`
- `write_chunks`

#### 最小示例
```python
from src.ingest_service import run_ingest

stats, logs, error = run_ingest(mode="sync", chunk_strategy="hybrid")
if error:
    print("构建失败:", error)
else:
    print(stats["chunks_written"])
    print(stats["total_seconds"])
```

---

## 4. 文档处理业务接口

文件：`src/corpus_service.py`

这些接口适合后续写：
- 数据准备脚本
- 文档清洗批处理脚本
- 原始文件管理工具

---

### 4.1 `summarize_raw_docs(...)`

```python
summarize_raw_docs(raw_dir: Path, cleaned_dir: Path) -> dict[str, Any]
```

#### 作用
统计 raw 文档当前状态。

#### 返回字段
- `docs`：原始文档路径列表
- `cleaned_count`：已清洗数量
- `uncleaned_count`：未清洗数量

---

### 4.2 `save_raw_upload(...)`

```python
save_raw_upload(raw_dir: Path, file_name: str, content: bytes, overwrite: bool) -> tuple[bool, str]
```

#### 作用
保存上传到 raw 目录的文件。

#### 返回值
- `bool`：是否成功
- `str`：结果说明文本

---

### 4.3 `build_raw_doc_rows(...)`

```python
build_raw_doc_rows(raw_dir: Path, cleaned_dir: Path) -> list[dict[str, Any]]
```

#### 作用
生成 raw 文档列表展示数据。

#### 典型返回字段
- `原始文件`
- `大小(KB)`
- `修改时间`
- `清洗状态`
- `cleaned 文件`

这个函数更偏页面展示数据准备，但自动化脚本如果想导出表格也可复用。

---

### 4.4 `clean_single_raw_file(...)`

```python
clean_single_raw_file(raw_dir: Path, cleaned_dir: Path, selected_raw: str) -> tuple[bool, str]
```

#### 作用
对一个 raw 文件执行清洗。

#### 返回值
- `bool`：是否成功
- `str`：结果说明文本

#### 最小示例
```python
from pathlib import Path
from src.corpus_service import clean_single_raw_file

ok, message = clean_single_raw_file(
    Path("data/protocols/raw"),
    Path("data/protocols/cleaned"),
    "http/rfc9114.txt",
)
print(ok, message)
```

---

### 4.5 `summarize_kb_source_docs(...)`

```python
summarize_kb_source_docs(data_dir: Path) -> tuple[list[Path], list[dict[str, Any]]]
```

#### 作用
汇总知识库源文件列表及展示数据。

#### 返回值
- `docs`：文件路径列表
- `rows`：适合表格展示的行数据

---

### 4.6 `save_kb_upload(...)`

```python
save_kb_upload(data_dir: Path, file_name: str, content: bytes, overwrite: bool) -> tuple[bool, str]
```

#### 作用
向知识库目录保存文件。

---

### 4.7 `delete_kb_file(...)`

```python
delete_kb_file(data_dir: Path, delete_target: str) -> tuple[bool, str]
```

#### 作用
删除知识库目录中的指定文件。

---

## 5. 底层工具接口（可选直接使用）

### `src/file_ops.py`
适合脚本直接使用的函数：

- `read_env_file(env_path: Path) -> dict[str, str]`
- `write_env_file(env_path: Path, updates: dict[str, str]) -> None`
- `list_raw_docs(data_dir: Path) -> list[Path]`
- `list_processable_raw_docs(data_dir: Path) -> list[Path]`
- `cleaned_target_for(raw_file, raw_base, cleaned_base) -> Path`
- `is_cleaned(raw_file, raw_base, cleaned_base) -> bool`
- `is_chroma_ready(chroma_dir: Path) -> bool`
- `resolve_source_path(file_path: str, project_root: Path) -> Path`

这些更偏底层工具，不是首选业务入口，但在实验脚本中很实用。

---

## 6. 推荐自动化脚本调用方式

### 6.1 批量问答实验
优先使用：
- `src.qa_service.execute_qa_flow`

### 6.2 索引构建实验
优先使用：
- `src.ingest_service.run_ingest`

### 6.3 文档准备/清洗脚本
优先使用：
- `src.corpus_service.clean_single_raw_file`
- 或直接使用 `scripts/clean_protocol_docs.py`

---

## 7. 典型实验脚本组织建议

后续如果要写自动化 runner，建议组织为：

```python
from src.ingest_service import run_ingest
from src.qa_service import execute_qa_flow

# 1. 建库
stats, logs, error = run_ingest(mode="sync", chunk_strategy="hybrid")

# 2. 批量问答
questions = [
    "什么是 ALPN？",
    "HTTP/3 和 HTTP/2 的区别是什么？",
]
results = []
for q in questions:
    results.append(execute_qa_flow(q))
```

---

## 8. 当前接口文档的定位

这份文档面向的是：
- 自动化实验脚本
- 批量评测脚本
- 数据采样脚本
- 后续非 Streamlit 前端接入

它不是最终 API 文档（因为项目还不是 HTTP 服务架构），但已经足够作为“后端可调用接口说明”使用。
