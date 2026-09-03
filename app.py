import streamlit as st

from core.config import GLOBAL_THEME_DEFAULT, PAGE_ICON, PAGE_TITLE
from core.data_import import render_data_import
from core.photo_checker import render_photo_check
from core.presentation_generator import render_generation


def render_sidebar():
    with st.sidebar:
        st.header("⚙️ Global Settings")
        root_path = st.text_input("Root Photo Folder Path", placeholder="/Users/name/Desktop/Grade 1")
        global_theme = st.text_input("Global Theme Name", value=GLOBAL_THEME_DEFAULT)
        uploaded_template = st.file_uploader("Upload PPTX Template", type="pptx")
        st.divider()
        st.warning("⚠️ **Strict Naming Required:** Photos must be named exactly `STUDENT NAME_W1.heic` etc.")
    return root_path, global_theme, uploaded_template


def main():
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")
    st.title("🎓 Student Portfolio Generator v2.0")
    st.success("🚀 FIXED COORDINATE MODE ACTIVE - Photos will now stay in place!")
    st.markdown("Automate your student presentations. **Strict Naming Mode Enabled.**")

    root_path, global_theme, uploaded_template = render_sidebar()
    tab1, tab2, tab3 = st.tabs(["📥 Data Import", "✅ Pre-Flight Check", "🚀 Generation"])

    with tab1:
        uploaded_data, dataframe, mapping = render_data_import()
    with tab2:
        render_photo_check(root_path, uploaded_data, dataframe, mapping.get("name"))
    with tab3:
        render_generation(root_path, uploaded_template, uploaded_data, dataframe, mapping, global_theme)


if __name__ == "__main__":
    main()
