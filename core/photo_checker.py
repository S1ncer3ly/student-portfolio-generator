import os

import pandas as pd
import streamlit as st

from core.config import WEEKS


def scan_student_photos(root_path, dataframe, name_column):
    results = []
    for _, row in dataframe.iterrows():
        name = str(row[name_column])
        status = {
            "Student": name,
            "Week 1": "❌",
            "Week 2": "❌",
            "Week 3": "❌",
            "Week 4": "❌",
            "Overall": "🔴",
        }
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


def render_photo_check(root_path, uploaded_data, dataframe, name_column):
    st.subheader("Step 2: Verify Photos")
    if st.button("🔍 Scan Folders for Photos"):
        if not root_path or uploaded_data is None or dataframe is None:
            st.warning("Please provide the Root Folder Path and upload a valid Student List first!")
        else:
            st.table(pd.DataFrame(scan_student_photos(root_path, dataframe, name_column)))
