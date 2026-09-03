import pillow_heif
import streamlit as st
from PIL import Image


def convert_heic_to_jpg(heic_path, output_path):
    """Convert a HEIC photo to JPEG for PowerPoint compatibility."""
    try:
        heif_file = pillow_heif.read_heif(heic_path)
        image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
            heif_file.mode,
            heif_file.stride,
        )
        image.save(output_path, "JPEG")
        return True
    except Exception as error:
        st.error(f"Error converting {heic_path}: {error}")
        return False


def replace_text_recursive(shapes, replacements):
    """Deep search and replace tags like {{NAME}} inside groups."""
    for shape in shapes:
        if shape.has_text_frame:
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    for key, value in replacements.items():
                        if key in run.text:
                            run.text = run.text.replace(key, str(value))
        if shape.shape_type == 6:
            replace_text_recursive(shape.shapes, replacements)
