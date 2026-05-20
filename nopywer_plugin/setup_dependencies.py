import sys
import subprocess
import os
import shutil
import traceback

# Attempt to import log_message from .utils
try:
    from .utils import log_message as _original_log_message
except (ImportError, ValueError):
    # Fallback to a simple print if utils is not available (e.g. standalone run)
    def _original_log_message(msg, level=None):
        print(msg)


# Nopywer version to download and install
# UPDATE THIS WHEN RELEASING A NEW NOPYWER VERSION
NOPYWER_VERSION = "0.2.1"


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


def log_message(msg, level=None):
    """Wrapper that logs to both QGIS message bar and persistent file."""
    if level is None:
        level = 0  # 0 corresponds to Qgis.Info in the QGIS API
    _original_log_message(msg, level)
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


def _check_nopywer_import(venv_python, env, command="import nopywer.cli"):
    """Helper: Run a command in venv and return the result."""
    try:
        result = subprocess.run(
            [venv_python, "-c", command],
            capture_output=True,
            text=True,
            env=env,
        )
        return result
    except Exception as e:
        log_message(f"Import check exception: {e}")
        return None


def _step_cleanup_venv(venv_path):
    """STEP 1: Remove existing venv if requested."""
    if not os.path.exists(venv_path):
        return True
    log_message(f"Cleaning: Removing existing venv at {venv_path}...")
    try:
        shutil.rmtree(venv_path)
        return True
    except Exception as e:
        log_message(f"Could not remove venv: {e}")
        return False


def _step_create_venv(qgis_python, venv_path, plugin_dir, env):
    """STEP 2: Create venv from QGIS Python if it doesn't exist."""
    if os.path.exists(venv_path):
        return True

    log_message("Creating virtual environment...")
    os.makedirs(os.path.dirname(venv_path), exist_ok=True)
    try:
        subprocess.check_call(
            [qgis_python, "-m", "venv", venv_path],
            cwd=plugin_dir,
            env=env,
        )
        return True
    except Exception as e:
        log_message(f"Failed to create venv: {e}")
        return False


def _get_installed_version(venv_python, env):
    """Get the installed nopywer version, or None if not installed."""
    result = _check_nopywer_import(
        venv_python, env, "import nopywer; print(nopywer.__version__)"
    )
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None


def _step_verify_nopywer(venv_python, force, env):
    """STEP 3: Check if nopywer is already installed with correct version (unless force=True)."""
    if force:
        log_message("Force flag set. Reinstalling nopywer...")
        return False

    installed_version = _get_installed_version(venv_python, env)
    if installed_version:
        if installed_version == NOPYWER_VERSION:
            log_message(
                f"✓ nopywer {NOPYWER_VERSION} is already installed and working!"
            )
            return True
        else:
            log_message(
                f"nopywer {installed_version} is installed, but {NOPYWER_VERSION} is required. "
                f"Upgrading..."
            )
            return False
    else:
        log_message("nopywer not found. Proceeding to install...")
        return False


def _step_install_wheel(venv_python, plugin_dir, env, force):
    """STEP 4: Download and install nopywer from pre-built wheel."""
    wheel_url = f"https://github.com/vfinel/nopywer/releases/download/v{NOPYWER_VERSION}/nopywer-{NOPYWER_VERSION}-py3-none-any.whl"

    log_message(f"Installing nopywer {NOPYWER_VERSION}...")
    log_message(f"Wheel URL: {wheel_url}")

    install_cmd = [
        venv_python,
        "-m",
        "pip",
        "install",
        "--force-reinstall" if force else "--upgrade",
        wheel_url,
    ]

    log_message(f"Running: {' '.join(install_cmd)}")
    result = subprocess.run(
        install_cmd, cwd=plugin_dir, capture_output=True, text=True, env=env
    )

    if result.returncode != 0:
        log_message(f"Installation failed with exit code {result.returncode}")
        log_message(f"STDOUT: {result.stdout}")
        log_message(f"STDERR: {result.stderr}")
        return False

    log_message("nopywer wheel installation output:")
    log_message(result.stdout)
    return True


def _step_verify_installation(venv_python, env):
    """STEP 5: Final verification that nopywer.cli imports successfully."""
    result = _check_nopywer_import(venv_python, env)

    if result and result.returncode == 0:
        log_message("✓ Successfully installed nopywer!")
        log_message(result.stdout)
        return True

    log_message("✗ Installation verification failed!")
    if result:
        log_message(f"STDERR: {result.stderr}")
    return False


def setup_dependencies(force=False, clean=False):
    """
    Orchestrates the installation of nopywer from a pre-built wheel.

    :param force: If True, forces reinstall of nopywer.
    :param clean: If True, deletes the existing venv entirely first.
    :return: True if successful, False otherwise.
    """
    try:
        plugin_dir = os.path.abspath(os.path.dirname(__file__))
        venv_path = get_venv_path()
        qgis_python = get_qgis_python_executable()

        # Isolate environment to prevent QGIS path bleeding
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)

        # Execute installation steps in sequence
        if clean and not _step_cleanup_venv(venv_path):
            return False

        if not _step_create_venv(qgis_python, venv_path, plugin_dir, env):
            return False

        venv_python = get_venv_python()
        log_message(f"Using venv Python: {venv_python}")

        # Check if already installed (return early if so)
        if _step_verify_nopywer(venv_python, force, env):
            return True

        # Install and verify
        if not _step_install_wheel(venv_python, plugin_dir, env, force):
            return False

        return _step_verify_installation(venv_python, env)

    except Exception as e:
        log_message(f"Unexpected error during setup_dependencies: {e}")
        log_message(f"Traceback:\n{traceback.format_exc()}")
        return False


if __name__ == "__main__":
    setup_dependencies()
