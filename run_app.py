import streamlit.web.bootstrap as bootstrap
import os
import sys
from pathlib import Path

def resolve_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        base_path = Path(os.getcwd())
    return str(base_path / relative_path)

if __name__ == "__main__":
    # The app file we want to run
    app_path = resolve_path("app.py")

    # We use the bootstrap module to launch streamlit programmatically
    # This mimics 'streamlit run app.py'
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
    ]

    bootstrap.run()
