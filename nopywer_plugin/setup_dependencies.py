import sys
import subprocess
import os
import shutil
import traceback

# Attempt to import log_message from .utils
try:
    from .utils import log_message
except (ImportError, ValueError):
    # Fallback to a simple print if utils is not available (e.g. standalone run)
    def log_message(msg, level=None):
        print(msg)


def write_to_log_file(msg):
    """Writes messages to a physical log file to survive QGIS crashes."""
    if sys.platform == "win32":
        log_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "nopywer")
    else:
        log_dir = os.path.join(os.path.expanduser("~"), ".nopywer")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "install.log")
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    except Exception:
        pass


# Intercept all log_message calls and also write them to the physical file
original_log_message = log_message


def log_message(msg, level=None):
    if level is None:
        level = 0  # 0 corresponds to Qgis.Info in the QGIS API
    original_log_message(msg, level)
    write_to_log_file(msg)


def get_qgis_python_executable():
    """Finds the real Python executable, avoiding the QGIS sys.executable quirk (qgis-bin.exe)."""
    executable = sys.executable
    if "python" in os.path.basename(executable).lower():
        return executable
    if sys.platform == "win32":
        py_path = os.path.join(sys.exec_prefix, "python.exe")
        if os.path.exists(py_path):
            return py_path
        py_path_bin = os.path.join(sys.exec_prefix, "bin", "python.exe")
        if os.path.exists(py_path_bin):
            return py_path_bin
    return os.path.join(sys.exec_prefix, "bin", "python3")


def get_venv_path():
    """Returns the absolute path to the virtual environment folder."""
    if sys.platform == "win32":
        base_dir = os.path.join(
            os.path.expanduser("~"), "AppData", "Roaming", "nopywer"
        )
    else:
        base_dir = os.path.join(os.path.expanduser("~"), ".nopywer")

    return os.path.abspath(os.path.join(base_dir, "venv"))


def get_venv_python():
    """Returns the absolute path to the Python executable inside the virtual environment."""
    venv_path = get_venv_path()
    if sys.platform == "win32":
        return os.path.join(venv_path, "Scripts", "python.exe")
    return os.path.join(venv_path, "bin", "python")


def get_venv_uv():
    """Returns the absolute path to the uv executable inside the virtual environment."""
    venv_path = get_venv_path()
    if sys.platform == "win32":
        return os.path.join(venv_path, "Scripts", "uv.exe")
    return os.path.join(venv_path, "bin", "uv")


def setup_dependencies(force=False, clean=False):
    """
    Creates a venv, installs uv via pip, and uses uv to install nopywer.
    :param force: If True, forces uv to reinstall nopywer.
    :param clean: If True, deletes the existing venv entirely first.
    """
    try:
        plugin_dir = os.path.abspath(os.path.dirname(__file__))
        venv_path = get_venv_path()
        qgis_python = get_qgis_python_executable()

        # Isolate environment to prevent QGIS path bleeding
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)

        # --- STEP 1: CLEANUP (If requested) ---
        if clean and os.path.exists(venv_path):
            log_message(f"Cleaning: Removing existing venv at {venv_path}...")
            try:
                shutil.rmtree(venv_path)
            except Exception as e:
                log_message(f"Could not remove venv: {e}")
                return False

        # --- STEP 2: CREATE VENV ---
        if not os.path.exists(venv_path):
            log_message("Creating virtual environment...")
            os.makedirs(os.path.dirname(venv_path), exist_ok=True)
            try:
                subprocess.check_call(
                    [qgis_python, "-m", "venv", venv_path],
                    cwd=plugin_dir,
                    env=env,
                )
            except Exception as e:
                log_message(f"Failed to create venv: {e}")
                return False

        venv_python = get_venv_python()
        uv_exe = get_venv_uv()

        # --- STEP 3: INSTALL UV (Via native pip) ---
        if not os.path.exists(uv_exe):
            log_message("Bootstrapping 'uv' package manager inside venv...")
            try:
                result = subprocess.run(
                    [venv_python, "-m", "pip", "install", "uv"],
                    capture_output=True,
                    text=True,
                    cwd=plugin_dir,
                    env=env,
                )
                if result.returncode != 0:
                    log_message(
                        f"Failed to install uv. STDOUT: {result.stdout} STDERR: {result.stderr}"
                    )
                    return False
            except Exception as e:
                log_message(f"Failed to install uv: {e}")
                return False

        # --- STEP 4: VERIFY NOPYWER STATUS ---
        if not force:
            try:
                # CRITICAL FIX: We must check nopywer.cli to ensure it's not a broken/empty folder
                result = subprocess.run(
                    [venv_python, "-c", "import nopywer.cli"],
                    capture_output=True,
                    text=True,
                    env=env,
                )
                if result.returncode == 0:
                    return True  # It's fully installed and working!
                else:
                    log_message(
                        f"nopywer check failed (this is normal on fresh install). Output: {result.stderr.strip()}"
                    )
                    log_message(
                        "nopywer missing or incomplete. Proceeding to install..."
                    )
            except Exception as e:
                log_message(f"nopywer verification exception: {e}")
                log_message("nopywer missing or incomplete. Proceeding to install...")

        # --- STEP 5: INSTALL NOPYWER (Via blazing fast uv) ---
        branch = "qgis_plugin"
        zip_url = f"https://github.com/vfinel/nopywer/archive/refs/heads/{branch}.zip"

        log_message(f"Installing nopywer from branch '{branch}' using uv...")

        cmd = [
            uv_exe,
            "pip",
            "install",
            "--python",
            venv_python,
            "--force-reinstall",
            zip_url,
        ]

        if force:
            cmd.append("--refresh")

        result = subprocess.run(
            cmd, cwd=plugin_dir, capture_output=True, text=True, env=env
        )

        if result.returncode != 0:
            log_message(f"uv pip install failed with exit code {result.returncode}")
            log_message(f"STDOUT: {result.stdout}")
            log_message(f"STDERR: {result.stderr}")
            return False

        log_message("Successfully installed/updated nopywer!")
        return True

    except Exception as e:
        log_message(f"Unexpected error during setup_dependencies: {e}")
        log_message(f"Traceback:\n{traceback.format_exc()}")
        return False


if __name__ == "__main__":
    setup_dependencies()
