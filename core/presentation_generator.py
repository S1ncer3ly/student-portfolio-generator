import os

import pandas as pd
import streamlit as st
from pptx import Presentation

from core.config import COORD_MAP, WEEKS
from core.utils.portfolio_helpers import convert_heic_to_jpg, replace_text_recursive
from core.utils.google_drive import (
    get_all_photos_from_weeks,
    get_all_photos_from_weeks_oauth,
    download_public_file
)

def remove_photo_placeholders(slide):
    for shape in list(slide.shapes):
        if shape.is_placeholder and shape.placeholder_format.type == 18:
            element = shape._element
            element.getparent().remove(element)


def generate_presentations(root_path, folder_id, api_key, drive_service, template_path, dataframe, mapping, global_theme):
    # Output folder: use root_path if available, else local directory
    output_folder = os.path.join(root_path, "Finished_PPTs") if root_path else "Finished_PPTs"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    progress_bar = st.progress(0)
    status_text = st.empty()

    # Log area with scrollview via CSS
    st.markdown(
        """
        <style>
        .scroll-container {
            max-height: 400px;
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 10px;
            border-radius: 5px;
            background-color: #f9f9f9;
            font-family: monospace;
            font-size: 12px;
            color: #333;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    with st.expander("Detailed Generation Log", expanded=True):
        log_placeholder = st.empty()
        all_logs = []

    def write_log(message):
        all_logs.append(message)
        # Join logs with newlines and wrap in the scrollable div
        log_content = f"<div class='scroll-container'>" + "<br>".join(all_logs) + "</div>"
        log_placeholder.markdown(log_content, unsafe_allow_html=True)

    # Pre-fetch file list if using Google Drive
    files_map = {}
    if drive_service:
        st.info("Scanning Google Drive (OAuth) sub-folders for photos...")
        files_map = get_all_photos_from_weeks_oauth(drive_service, folder_id)
    elif folder_id and api_key:
        st.info("Scanning Google Drive (API Key) sub-folders for photos...")
        files_map = get_all_photos_from_weeks(folder_id, api_key)

    files_map_lower = {k.lower(): v for k, v in files_map.items()} if files_map else {}

    for index, row in dataframe.iterrows():
        # STOP CHECK
        if st.session_state.get("stop_generation", False):
            st.warning("🛑 Generation stopped by user.")
            break

        name = str(row[mapping["name"]]).strip()
        student_class = str(row[mapping["class"]])
        section = str(row[mapping["section"]])
        theme_column = mapping["theme"]
        theme = str(row[theme_column]) if theme_column and pd.notna(row[theme_column]) else global_theme
        status_text.text(f"Processing {index + 1}/{len(dataframe)}: {name}...")

        try:
            presentation = Presentation(template_path)
            replacements = {
                "{{NAME}}": name,
                "{{CLASS}}": student_class,
                "{{SECTION}}": section,
                "{{THEME}}": theme,
            }
            replace_text_recursive(presentation.slides[1].shapes, replacements)

            for week in WEEKS:
                # STOP CHECK inside week loop
                if st.session_state.get("stop_generation", False):
                    break

                slide_index = week + 2
                slide = presentation.slides[slide_index - 1]
                remove_photo_placeholders(slide)
                expected_filename = f"{name}_W{week}.heic"

                photo_path = None
                if drive_service:
                    file_id = None
                    if expected_filename in files_map:
                        file_id = files_map[expected_filename]
                    elif expected_filename.lower() in files_map_lower:
                        file_id = files_map_lower[expected_filename.lower()]

                    if file_id:
                        temp_heic = f"temp_{index}_{week}.heic"
                        write_log(f"⏳ {name} W{week}: Downloading (OAuth)...")
                        import io
                        from googleapiclient.http import MediaIoBaseDownload
                        try:
                            request = drive_service.files().get_media(fileId=file_id)
                            with io.FileIO(temp_heic, 'wb') as fh:
                                downloader = MediaIoBaseDownload(fh, request)
                                done = False
                                while not done:
                                    _, done = downloader.next_chunk()
                            photo_path = temp_heic
                        except Exception as e:
                            write_log(f"❌ {name} W{week}: OAuth Download failed ({e})")

                elif folder_id and api_key:
                    file_id = None
                    if expected_filename in files_map:
                        file_id = files_map[expected_filename]
                    elif expected_filename.lower() in files_map_lower:
                        file_id = files_map_lower[expected_filename.lower()]

                    if file_id:
                        temp_heic = f"temp_{index}_{week}.heic"
                        write_log(f"⏳ {name} W{week}: Downloading (API Key)...")
                        success, error = download_public_file(file_id, api_key, temp_heic)
                        if success:
                            photo_path = temp_heic
                        else:
                            write_log(f"❌ {name} W{week}: Download failed ({error})")

                elif root_path:
                    local_path = os.path.join(root_path, f"Week {week}", expected_filename)
                    if os.path.exists(local_path):
                        photo_path = local_path
                    else:
                        write_log(f"❌ {name} W{week}: Not found locally.")

                if photo_path:
                    temp_jpg = f"temp_{index}_{week}.jpg"
                    write_log(f"⚙️ {name} W{week}: Converting HEIC to JPG...")
                    if convert_heic_to_jpg(photo_path, temp_jpg):
                        left, top, width, height = COORD_MAP[slide_index]
                        slide.shapes.add_picture(temp_jpg, left, top, width, height)
                        write_log(f"✅ {name} W{week}: Added to slide.")
                    else:
                        write_log(f"❌ {name} W{week}: Conversion failed.")

                    # Cleanup
                    if os.path.exists(temp_jpg):
                        os.remove(temp_jpg)
                    if photo_path.startswith("temp_") and os.path.exists(photo_path):
                        os.remove(photo_path)

            save_path = os.path.join(output_folder, f"{name.replace(' ', '_')}.pptx")
            presentation.save(save_path)
        except Exception as error:
            st.error(f"Error for {name}: {error}")
            write_log(f"💥 {name}: Critical Error - {error}")
        progress_bar.progress((index + 1) / len(dataframe))

    if not st.session_state.get("stop_generation", False):
        status_text.success(f"🎉 Done! {len(dataframe)} presentations created.")
    else:
        status_text.info("Generation process was stopped.")


def render_generation(root_path, folder_id, api_key, drive_service, uploaded_template, uploaded_data, dataframe, mapping, global_theme):
    st.subheader("Step 3: Generate Presentations")

    # Initialize session state for stop button
    if "stop_generation" not in st.session_state:
        st.session_state.stop_generation = False

    col1, col2 = st.columns([3, 1])

    with col1:
        generate_btn = st.button("🔥 GENERATE ALL PRESENTATIONS", type="primary", use_container_width=True)

    with col2:
        if st.button("🛑 STOP", use_container_width=True):
            st.session_state.stop_generation = True
            st.rerun()

    if generate_btn:
        # Reset stop flag before starting
        st.session_state.stop_generation = False

        if not uploaded_template or not uploaded_data or (not root_path and not folder_id) or dataframe is None:
            st.error("Missing requirements!")
            return

        if folder_id and not api_key and not drive_service:
            st.error("Please provide your Google API Key or authenticate via OAuth!")
            return

        template_path = "temp_template.pptx"
        with open(template_path, "wb") as template_file:
            template_file.write(uploaded_template.getbuffer())
        generate_presentations(root_path, folder_id, api_key, drive_service, template_path, dataframe, mapping, global_theme)
