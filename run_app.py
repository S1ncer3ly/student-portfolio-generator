import os
import sys
import subprocess
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

    # Use subprocess to launch streamlit. This is the most stable way to
    # mimic 'streamlit run app.py' from within a Python script.
    try:
        subprocess.run([
            "streamlit",
            "run",
            app_path,
            "--global.developmentMode=false",
        ], check=True)
    except Exception as e:
        with open("crash_log.txt", "w") as f:
            import traceback
            f.write(traceback.format_exc())

