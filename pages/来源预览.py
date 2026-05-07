from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.i18n import t

st.set_page_config(page_title=t("preview.title"), layout="wide")

query_params = st.query_params
raw_path = str(query_params.get("path", "")).strip()

if not raw_path:
    st.title(t("preview.title"))
    st.info(t("preview.no_path"))
else:
    target = Path(raw_path).expanduser().resolve()
    st.page_link("app.py", label=t("preview.back"))
    st.title(target.name)
    st.caption(str(target))

    if not target.exists():
        st.error(t("preview.file_not_found", target=target))
    elif not target.is_file():
        st.error(t("preview.not_file", target=target))
    else:
        try:
            content = target.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            st.error(t("preview.read_failed", exc=exc))
        else:
            st.markdown(t("preview.content_title"))
            if target.suffix.lower() == ".md":
                with st.container(border=True):
                    st.markdown(content)
            else:
                st.text_area(t("preview.content_label"), value=content, height=760)
