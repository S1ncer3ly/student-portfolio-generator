import streamlit as st
import os

from core.config import GLOBAL_THEME_DEFAULT, PAGE_ICON, PAGE_TITLE
from core.data_import import render_data_import
from core.photo_checker import render_photo_check
from core.presentation_generator import render_generation


def render_sidebar():
    with st.sidebar:
        st.header("⚙️ Global Settings")

        source_type = st.radio("Photo Source", ["Local Folder", "Google Drive (OAuth)"], index=0)

        if source_type == "Local Folder":
            root_path = st.text_input("Root Photo Folder Path", placeholder="/Users/name/Desktop/Grade 1")
            folder_id = None
            api_key = None
            drive_service = None
        else:
            root_path = None
            folder_id = st.text_input("Google Drive Folder ID", placeholder="1AbC...xyz")
            api_key = None

            # Check if credentials.json already exists in the project root
            creds_exists = os.path.exists("credentials.json")

            if creds_exists:
                st.info("✅ `credentials.json` found in project folder.")
            else:
                creds_file = st.file_uploader("Upload credentials.json", type="json")
                if creds_file:
                    with open("credentials.json", "wb") as f:
                        f.write(creds_file.getbuffer())
                    st.success("Credentials saved to project folder!")

            # Use session state to persist the drive service across reruns
            if "drive_service" not in st.session_state:
                st.session_state.drive_service = None

            if st.button("Connect to Google Drive"):
                if os.path.exists("credentials.json"):
                    try:
                        from core.utils.google_drive import get_drive_service
                        st.session_state.drive_service = get_drive_service(None)
                        st.success("Connected successfully!")
                    except Exception as e:
                        st.error(f"Connection failed: {e}")
                else:
                    st.error("Please upload `credentials.json` first.")

            drive_service = st.session_state.drive_service

        st.divider()
        save_destination = st.radio("Save Final PPTs to:", ["Local Computer", "Google Drive"], index=0)

        global_theme = st.text_input("Global Theme Name", value=GLOBAL_THEME_DEFAULT)
        uploaded_template = st.file_uploader("Upload PPTX Template", type="pptx")
        st.divider()
        st.warning("⚠️ **Strict Naming Required:** Photos must be named exactly `STUDENT NAME_W1.heic` etc.")
    return root_path, folder_id, api_key, drive_service, save_destination, global_theme, uploaded_template


def main():
    st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")
    st.title("🎓 Student Portfolio Generator")
    st.success("🚀 FIXED COORDINATE MODE ACTIVE - Photos will now stay in place!")
    st.markdown("Automate your student presentations. **Strict Naming Mode Enabled.**")

    root_path, folder_id, api_key, drive_service, save_destination, global_theme, uploaded_template = render_sidebar()
    tab1, tab2, tab3 = st.tabs(["📥 Data Import", "✅ Pre-Flight Check", "🚀 Generation"])

    with tab1:
        uploaded_data, dataframe, mapping = render_data_import()
    with tab2:
        render_photo_check(root_path, folder_id, api_key, drive_service, uploaded_data, dataframe, mapping.get("name"))
    with tab3:
        render_generation(root_path, folder_id, api_key, drive_service, save_destination, uploaded_template, uploaded_data, dataframe, mapping, global_theme)


if __name__ == "__main__":
    main()
