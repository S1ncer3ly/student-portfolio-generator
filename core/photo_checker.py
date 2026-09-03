import os

import pandas as pd
import streamlit as st

from core.config import WEEKS
from core.utils.google_drive import get_all_photos_from_weeks, get_all_photos_from_weeks_oauth

def scan_student_photos(root_path, folder_id, api_key, drive_service, dataframe, name_column):
    results = []

    # Case 1: Google Drive OAuth
    if drive_service:
        st.info("Scanning Google Drive (OAuth) sub-folders for photos...")
        files_map = get_all_photos_from_weeks_oauth(drive_service, folder_id)

        if not files_map:
            st.warning("No files found on Drive. Please check your permissions.")
        else:
            st.success(f"Found {len(files_map)} total files on Drive.")
            with st.expander("View detected files on Drive"):
                st.write(list(files_map.keys()))

    # Case 2: Google Drive API Key
    elif folder_id and api_key:
        st.info("Scanning Google Drive (API Key) sub-folders for photos...")
        files_map = get_all_photos_from_weeks(folder_id, api_key)

        if not files_map:
            st.warning("No files found on Drive. Please check your permissions.")
        else:
            st.success(f"Found {len(files_map)} total files on Drive.")
            with st.expander("View detected files on Drive"):
                st.write(list(files_map.keys()))

    # Case 3: Local Path
    elif root_path:
        # Local scan uses a different logic as it checks folders on the fly
        # We handle it below
        files_map = None
    else:
        return []

    # If we are using Drive, process the results
    if 'files_map' in locals() and files_map is not None:
        for _, row in dataframe.iterrows():
            name = str(row[name_column]).strip()
            status = {"Student": name, "Week 1": "❌", "Week 2": "❌", "Week 3": "❌", "Week 4": "❌", "Overall": "🔴"}
            all_found = True
            for week in WEEKS:
                expected_filename = f"{name}_W{week}.heic"
                if expected_filename in files_map:
                    status[f"Week {week}"] = "✅"
                else:
                    all_found = False
            status["Overall"] = "🟢" if all_found else "🟡"
            results.append(status)
        return results

    # Process Local Path
    if root_path:
        for _, row in dataframe.iterrows():
            name = str(row[name_column]).strip()
            status = {"Student": name, "Week 1": "❌", "Week 2": "❌", "Week 3": "❌", "Week 4": "❌", "Overall": "🔴"}
            all_found = True
            for week in WEEKS:
                expected_filename = f"{name}_W{week}.heic"
                folder = os.path.join(root_path, f"Week {week}")
                if os.path.exists(folder) and expected_filename in os.listdir(folder):
                    status[f"Week {week}"] = "✅"
                else:
                    all_found = False
            status["Overall"] = "🟢" if all_found else "🟡"
            results.append(status)
        return results

    return []

def render_photo_check(root_path, folder_id, api_key, drive_service, uploaded_data, dataframe, name_column):
    st.subheader("Step 2: Verify Photos")

    if "photo_check_results" not in st.session_state:
        st.session_state.photo_check_results = None

    if st.button("🔍 Scan Folders for Photos"):
        if (not root_path and not folder_id) or uploaded_data is None or dataframe is None:
            st.warning("Please provide the Root Folder Path or Google Drive ID and upload a valid Student List first!")
        elif folder_id and not api_key and not drive_service:
            st.warning("Please provide your Google API Key or authenticate via OAuth!")
        else:
            st.session_state.photo_check_results = scan_student_photos(root_path, folder_id, api_key, drive_service, dataframe, name_column)

    if st.session_state.photo_check_results is not None:
        results_df = pd.DataFrame(st.session_state.photo_check_results)
        st.table(results_df)

        csv = results_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Pre-Flight Report (CSV)",
            data=csv,
            file_name="pre_flight_check_report.csv",
            mime="text/csv",
        )
