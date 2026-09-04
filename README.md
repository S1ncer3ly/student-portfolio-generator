# Student Portfolio Generator

A Streamlit application that creates individualized student portfolio presentations from a CSV or Excel student list, a PowerPoint template, and weekly student photos.

## Features

- Import student data from CSV or Excel.
- Map student, class, section, and theme columns.
- Check for each student's Week 1 through Week 4 photos.
- Convert HEIC photos to JPEG for PowerPoint compatibility.
- Generate one PowerPoint presentation per student.

## Workflow

1. Enter the root folder containing `Week 1` through `Week 4`.
2. Upload the student list and map its columns.
3. Upload the PowerPoint template.
4. Scan the folders to verify the required photos.
5. Generate the finished presentations in `Finished_PPTs`.

Photos should follow the naming convention `STUDENT NAME_W1.heic` through `STUDENT NAME_W4.heic`.

## Project structure

- `app.py`: Streamlit entrypoint and page layout.
- `data_import.py`: Student file upload and column mapping.
- `photo_checker.py`: Weekly photo verification.
- `presentation_generator.py`: PowerPoint generation workflow.
- `portfolio_helpers.py`: HEIC conversion and template text replacement.
- `config.py`: Shared settings and slide coordinates.

## Run locally

You can install the required dependencies using the `requirements.txt` file:

```bash
pip install -r requirements.txt
streamlit run app.py
```
