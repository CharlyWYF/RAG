from __future__ import annotations

from pathlib import Path

import streamlit as st

st.set_page_config(page_title="来源预览", layout="wide")

query_params = st.query_params
raw_path = str(query_params.get("path", "")).strip()

if not raw_path:
    st.title("来源预览")
    st.info("未提供来源文件路径。请从主问答页点击“预览”进入此页面。")
else:
    target = Path(raw_path).expanduser().resolve()
    st.page_link("app.py", label="← 返回主页面")
    st.title(target.name)
    st.caption(str(target))

    if not target.exists():
        st.error(f"文件不存在：{target}")
    elif not target.is_file():
        st.error(f"目标不是文件：{target}")
    else:
        try:
            content = target.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            st.error(f"读取文件失败：{exc}")
        else:
            st.markdown("### 文件内容")
            if target.suffix.lower() == ".md":
                with st.container(border=True):
                    st.markdown(content)
            else:
                st.text_area("文件内容", value=content, height=760)
