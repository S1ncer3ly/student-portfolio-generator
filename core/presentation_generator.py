import os

import pandas as pd
import streamlit as st
from pptx import Presentation

from core.config import COORD_MAP, WEEKS
from core.utils.portfolio_helpers import convert_heic_to_jpg, replace_text_recursive


def remove_photo_placeholders(slide):
    for shape in list(slide.shapes):
        if shape.is_placeholder and shape.placeholder_format.type == 18:
            element = shape._element
            element.getparent().remove(element)


def generate_presentations(root_path, template_path, dataframe, mapping, global_theme):
    output_folder = os.path.join(root_path, "Finished_PPTs")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    progress_bar = st.progress(0)
    status_text = st.empty()

    for index, row in dataframe.iterrows():
        name = str(row[mapping["name"]])
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
                slide_index = week + 2
                slide = presentation.slides[slide_index - 1]
                remove_photo_placeholders(slide)
                expected_filename = f"{name}_W{week}.heic"
                photo_path = os.path.join(root_path, f"Week {week}", expected_filename)
                if os.path.exists(photo_path):
                    temp_jpg = f"temp_{index}_{week}.jpg"
                    convert_heic_to_jpg(photo_path, temp_jpg)
                    left, top, width, height = COORD_MAP[slide_index]
                    slide.shapes.add_picture(temp_jpg, left, top, width, height)
                    os.remove(temp_jpg)

            save_path = os.path.join(output_folder, f"{name.replace(' ', '_')}.pptx")
            presentation.save(save_path)
        except Exception as error:
            st.error(f"Error for {name}: {error}")
        progress_bar.progress((index + 1) / len(dataframe))

    status_text.success(f"🎉 Done! {len(dataframe)} presentations created.")


def render_generation(root_path, uploaded_template, uploaded_data, dataframe, mapping, global_theme):
    st.subheader("Step 3: Generate Presentations")
    if st.button("🔥 GENERATE ALL PRESENTATIONS", type="primary", use_container_width=True):
        if not uploaded_template or not uploaded_data or not root_path or dataframe is None:
            st.error("Missing requirements!")
            return

        template_path = "temp_template.pptx"
        with open(template_path, "wb") as template_file:
            template_file.write(uploaded_template.getbuffer())
        generate_presentations(root_path, template_path, dataframe, mapping, global_theme)
