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
    """Bootstraps uv and installs nopywer directly from GitHub."""
    python_exe = get_python_executable()

    # 1. Ensure 'uv' is installed in the QGIS Python environment
    try:
        importlib.import_module("uv")
    except ImportError:
        print("Installing the 'uv' package manager in QGIS...")
        try:
            subprocess.check_call([python_exe, "-m", "pip", "install", "uv"])
        except subprocess.CalledProcessError:
            print("Critical Error: Failed to install uv via pip.")
            return False

    # 2. Check if 'nopywer' is already installed
    try:
        importlib.import_module("nopywer")
        return True
    except ImportError:
        print("nopywer not found. Installing from GitHub using uv...")
        github_url = "git+https://github.com/vfinel/nopywer.git"

        try:
            # Execute: uv pip install git+https://...
            subprocess.check_call(
                [python_exe, "-m", "uv", "pip", "install", github_url]
            )
            print("Successfully installed nopywer!")
            return True
        except subprocess.CalledProcessError:
            print("Failed to install nopywer from GitHub.")
            return False
