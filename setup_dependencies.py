import sys
import subprocess
import importlib
import os


def get_python_executable():
    """Finds the real Python executable, avoiding the QGIS sys.executable quirk."""
    executable = sys.executable

    # If it's already Python (standard on Mac/Linux), we are good
    if "python" in os.path.basename(executable).lower():
        return executable

    # On Windows QGIS, sys.executable is qgis-bin.exe
    # sys.exec_prefix points to the OSGeo4W Python installation
    if os.name == "nt":
        # Try standard OSGeo4W Python path
        py_path = os.path.join(sys.exec_prefix, "python.exe")
        if os.path.exists(py_path):
            return py_path

        # Try bin directory just in case
        py_path_bin = os.path.join(sys.exec_prefix, "bin", "python.exe")
        if os.path.exists(py_path_bin):
            return py_path_bin

    # Fallback for Mac/Linux if sys.executable somehow points to 'qgis'
    return os.path.join(sys.exec_prefix, "bin", "python3")


def setup_dependencies():
    python_exe = get_python_executable()

    try:
        importlib.import_module("nopywer")
        return True
    except ImportError:
        print("nopywer not found. Installing from GitHub using pip...")

        # Download the ZIP directly using native pip
        github_zip_url = "https://github.com/vfinel/nopywer/archive/refs/heads/main.zip"

        try:
            # We use standard pip here because it handles zip URLs much better than uv
            subprocess.check_call(
                [python_exe, "-m", "pip", "install", "--user", github_zip_url]
            )
            print("Successfully installed nopywer!")
            importlib.invalidate_caches()
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to install nopywer from GitHub. {e}")
            return False
