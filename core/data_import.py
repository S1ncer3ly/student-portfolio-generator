import pandas as pd
import streamlit as st


def load_student_data(uploaded_data):
    try:
        if uploaded_data.name.endswith(".csv"):
            dataframe = pd.read_csv(uploaded_data)
        else:
            dataframe = pd.read_excel(uploaded_data)
    except Exception as error:
        st.error(f"An error occurred: {error}")
        return None

    if dataframe.empty:
        st.error("The uploaded file is empty.")
        return None
    return dataframe


def render_data_import():
    st.subheader("Step 1: Import Student List")
    uploaded_data = st.file_uploader("Upload Student CSV or Excel", type=["csv", "xlsx"])
    dataframe = None
    mapping = {}

    if uploaded_data:
        dataframe = load_student_data(uploaded_data)
        if dataframe is not None:
            st.write("### Preview of Student Data")
            st.dataframe(dataframe, use_container_width=True)
            st.divider()
            st.write("### Column Mapping")
            first_column, second_column = st.columns(2)
            with first_column:
                mapping["name"] = st.selectbox("Which column is the Student Name?", options=dataframe.columns)
                mapping["class"] = st.selectbox("Which column is the Class?", options=dataframe.columns)
            with second_column:
                mapping["section"] = st.selectbox("Which column is the Section?", options=dataframe.columns)
                mapping["theme"] = st.selectbox(
                    "Which column is the Theme? (Optional)",
                    options=[None] + list(dataframe.columns),
                )

    return uploaded_data, dataframe, mapping
