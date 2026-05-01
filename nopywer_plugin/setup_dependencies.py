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


def get_venv_path():
    """Returns the absolute path to the virtual environment folder.

    This is stored OUTSIDE the plugin directory to prevent QGIS from scanning it
    as a data source, which would cause crashes and errors.
    """
    # Use QGIS config directory or fallback to home
    if sys.platform == "win32":
        # Windows: use AppData\Roaming\nopywer
        base_dir = os.path.join(
            os.path.expanduser("~"), "AppData", "Roaming", "nopywer"
        )
    else:
        # Linux/Mac: use ~/.nopywer
        base_dir = os.path.join(os.path.expanduser("~"), ".nopywer")

    venv_path = os.path.abspath(os.path.join(base_dir, "venv"))
    print(f"{venv_path=}")

    return venv_path


def get_venv_python():
    """Returns the absolute path to the Python executable inside the virtual environment."""
    venv_path = get_venv_path()

    # Platform agnostic path discovery
    possible_paths = [
        os.path.join(venv_path, "Scripts", "python.exe"),  # Windows
        os.path.join(venv_path, "bin", "python"),  # Linux/Mac
        os.path.join(venv_path, "bin", "python3"),  # Linux/Mac fallback
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return os.path.abspath(path)

    # Fallback default if not created yet
    if sys.platform == "win32":
        return os.path.abspath(possible_paths[0])
    return os.path.abspath(possible_paths[1])


def find_uv():
    """Tries to find the uv executable in common paths."""
    # 1. Check if already in PATH
    uv_cmd = shutil.which("uv")
    if uv_cmd:
        return uv_cmd

    # 2. Check common installation paths
    user_home = os.path.expanduser("~")
    common_paths = [
        os.path.join(user_home, ".local", "bin", "uv.exe"),
        os.path.join(user_home, ".local", "bin", "uv"),
        os.path.join(user_home, ".cargo", "bin", "uv.exe"),
        os.path.join(user_home, ".cargo", "bin", "uv"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "uv", "uv.exe"),
    ]

    for path in common_paths:
        if os.path.exists(path):
            return path

    return "uv"  # Fallback to name and hope for the best


def setup_dependencies(force=False, clean=False):
    """
    Uses uv to create a virtual environment and install nopywer.
    :param force: If True, runs the install command even if nopywer is present (updates).
    :param clean: If True, deletes the existing venv first.
    """
    try:
        plugin_dir = os.path.abspath(os.path.dirname(__file__))
        venv_path = get_venv_path()
        uv_path = find_uv()

        # Create parent directory for venv if it doesn't exist
        venv_parent = os.path.dirname(venv_path)
        os.makedirs(venv_parent, exist_ok=True)

        # Isolate environment
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)

        if clean and os.path.exists(venv_path):
            log_message(f"Cleaning: Removing existing venv at {venv_path}...")
            try:
                shutil.rmtree(venv_path)
            except Exception as e:
                log_message(f"Could not remove venv: {e}")
                return False

        # 1. Create venv if needed
        if not os.path.exists(venv_path):
            # Try uv first (faster), then fall back to standard venv
            uv_available = (
                shutil.which(uv_path) is not None if uv_path != "uv" else False
            )

            if uv_available:
                log_message("Creating virtual environment using uv...")
                try:
                    subprocess.check_call(
                        [uv_path, "venv", venv_path], cwd=plugin_dir, env=env
                    )
                except Exception as e:
                    log_message(
                        f"uv venv creation failed, falling back to standard venv: {e}"
                    )
                    uv_available = False

            if not uv_available:
                log_message(
                    "Creating virtual environment using Python's venv module..."
                )
                try:
                    subprocess.check_call(
                        [sys.executable, "-m", "venv", venv_path],
                        cwd=plugin_dir,
                        env=env,
                    )
                except Exception as e:
                    log_message(f"Failed to create venv: {e}")
                    return False

                # Try to install uv into the new venv for faster future operations
                log_message("Installing uv into venv for faster future operations...")
                try:
                    subprocess.check_call(
                        [get_venv_python(), "-m", "pip", "install", "uv"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        cwd=plugin_dir,
                        env=env,
                    )
                    log_message("uv installed successfully!")
                    # Update uv_path to use the venv's uv for subsequent operations
                    if sys.platform == "win32":
                        uv_path = os.path.join(venv_path, "Scripts", "uv.exe")
                    else:
                        uv_path = os.path.join(venv_path, "bin", "uv")
                except Exception as e:
                    log_message(f"Could not install uv (optional): {e}")
                    # This is non-critical, we can still proceed

        python_exe = get_venv_python()

        # 2. Check if nopywer is already installed (skip if not forcing)
        if not force:
            try:
                subprocess.check_call(
                    [python_exe, "-c", "import nopywer"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                )
                return True
            except Exception:
                log_message("nopywer missing or venv broken. Installing...")

        else:
            log_message("nopywer missing or venv broken. Installing...")

        # 3. Install/Update nopywer from GitHub ZIP
        try:
            branch = "qgis_plugin"
            zip_url = (
                f"https://github.com/vfinel/nopywer/archive/refs/heads/{branch}.zip"
            )
            log_message(f"Refreshing nopywer from branch {branch}...")

            # Determine if uv is available (system or venv)
            uv_available = False
            if os.path.exists(uv_path):
                uv_available = True
            elif shutil.which(uv_path) is not None and uv_path != "uv":
                uv_available = True

            if uv_available:
                cmd = [
                    uv_path,
                    "pip",
                    "install",
                    "--python",
                    python_exe,
                    "--force-reinstall",
                    zip_url,
                ]

                if force:
                    cmd.append("--refresh")

                log_message("Installing with uv...")
                result = subprocess.run(
                    cmd, cwd=plugin_dir, capture_output=True, text=True, env=env
                )

                if result.returncode != 0:
                    log_message(
                        "uv pip install failed, falling back to standard pip..."
                    )
                    uv_available = False

            if not uv_available:
                cmd = [
                    python_exe,
                    "-m",
                    "pip",
                    "install",
                    "--force-reinstall",
                    "--upgrade",
                    zip_url,
                ]

                log_message("Installing with pip...")
                result = subprocess.run(
                    cmd, cwd=plugin_dir, capture_output=True, text=True, env=env
                )

            if result.returncode != 0:
                log_message(f"pip install failed with exit code {result.returncode}")
                log_message(f"STDOUT: {result.stdout}")
                log_message(f"STDERR: {result.stderr}")
                return False

            log_message("Successfully installed/updated nopywer!")
            return True

        except Exception as e:
            log_message(f"Unexpected error during nopywer installation: {e}")
            log_message(f"Traceback:\n{traceback.format_exc()}")
            return False

    except Exception as e:
        log_message(f"Unexpected error during setup_dependencies: {e}")
        log_message(f"Traceback:\n{traceback.format_exc()}")
        return False


if __name__ == "__main__":
    setup_dependencies()
