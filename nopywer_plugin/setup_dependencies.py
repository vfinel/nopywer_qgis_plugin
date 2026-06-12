import sys
import subprocess
import os
import shutil
import traceback
import configparser

# Attempt to import log_message from .utils
try:
    from .utils import log_message as _original_log_message
except (ImportError, ValueError):
    # Fallback to a simple print if utils is not available (e.g. standalone run)
    def _original_log_message(msg, level=None):
        print(msg)


def log_message(msg, level=None):
    """Wrapper that logs to both QGIS message bar and persistent file."""
    if level is None:
        level = 0  # 0 corresponds to Qgis.Info in the QGIS API
    _original_log_message(msg, level)
    write_to_log_file(msg)


def _load_config():
    """Load nopywer configuration from nopywer.cfg file."""
    config = configparser.ConfigParser()
    config_file = os.path.join(os.path.dirname(__file__), "nopywer.cfg")

    # Default values
    defaults = {"version": "0.3.1", "local_path": ""}

    try:
        if os.path.exists(config_file):
            config.read(config_file)
            if "nopywer" in config:
                version = config.get("nopywer", "version", fallback=defaults["version"])
                local_path = config.get(
                    "nopywer", "local_path", fallback=defaults["local_path"]
                ).strip()
                return version, local_path if local_path else None
    except Exception as e:
        log_message(f"Warning: Could not read config file {config_file}: {e}")

    return defaults["version"], None


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


def _step_ensure_pip(venv_python, env):
    """STEP 2B: Ensure pip is available in the venv."""
    log_message("Ensuring pip is available in venv...")

    # First, check if pip is already available
    result = subprocess.run(
        [venv_python, "-m", "pip", "--version"],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode == 0:
        log_message(f"✓ pip is available: {result.stdout.strip()}")
        return True

    # If not, try ensurepip
    log_message("Attempting to bootstrap pip with ensurepip...")
    try:
        result = subprocess.run(
            [venv_python, "-m", "ensurepip", "--upgrade"],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        if result.returncode == 0:
            log_message("✓ pip bootstrapped successfully")
            return True
        else:
            log_message(f"Warning: ensurepip failed. Attempting pip verification...")
            # Check again if pip is available despite the error
            result = subprocess.run(
                [venv_python, "-m", "pip", "--version"],
                capture_output=True,
                text=True,
                env=env,
            )
            if result.returncode == 0:
                log_message(
                    f"✓ pip is available despite ensurepip warning: {result.stdout.strip()}"
                )
                return True
            else:
                log_message(f"Error: pip is not available in venv")
                return False
    except subprocess.TimeoutExpired:
        log_message("Error: ensurepip timed out")
        return False
    except Exception as e:
        log_message(f"Error: Failed to ensure pip: {e}")
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
    log_message(f"{installed_version=}")
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


def _validate_local_nopywer(local_path):
    """Validate that a local nopywer installation exists and is valid.

    Supports both flat layout (nopywer/__init__.py) and src-layout (src/nopywer/__init__.py).
    Returns the path to add to PYTHONPATH, or None if invalid.
    """
    log_message(f"Validating local nopywer at {local_path}")
    if not local_path or not os.path.isdir(local_path):
        log_message(f"Invalid NOPYWER_LOCAL_PATH: {local_path} (directory not found)")
        return None

    # Check if it's a src-layout project: src/nopywer/__init__.py
    src_nopywer = os.path.join(local_path, "src", "nopywer", "__init__.py")
    if os.path.isfile(src_nopywer):
        pythonpath = os.path.join(local_path, "src")
        log_message(f"✓ Found nopywer package (src-layout) at {local_path}/src")
        return pythonpath

    # Check if it's a directory containing nopywer/: nopywer/__init__.py
    nopywer_init = os.path.join(local_path, "nopywer", "__init__.py")
    if os.path.isfile(nopywer_init):
        log_message(f"✓ Found nopywer package (flat layout) at {local_path}/nopywer")
        return local_path

    # Check if the path itself IS the nopywer package: __init__.py
    if os.path.isfile(os.path.join(local_path, "__init__.py")):
        log_message(f"✓ Found nopywer package at {local_path}")
        return local_path

    log_message(f"Invalid local nopywer: no nopywer package found at {local_path}")
    return None


def _get_site_packages_path(venv_path):
    """Get the site-packages directory path for the venv."""
    if sys.platform == "win32":
        return os.path.join(venv_path, "Lib", "site-packages")
    else:
        # For Unix, we need to find the specific Python version directory
        lib_path = os.path.join(venv_path, "lib")
        if os.path.isdir(lib_path):
            # Find pythonX.Y directories
            for item in os.listdir(lib_path):
                if item.startswith("python"):
                    return os.path.join(lib_path, item, "site-packages")
        return None


def _get_pth_file_path(venv_path):
    """Get the path to the .pth file for local nopywer."""
    site_packages = _get_site_packages_path(venv_path)
    if site_packages:
        return os.path.join(site_packages, "nopywer_local.pth")
    return None


def _cleanup_local_pth_file(venv_path):
    """Remove the .pth file if it exists (for switching between local and wheel mode)."""
    pth_file = _get_pth_file_path(venv_path)
    if pth_file and os.path.isfile(pth_file):
        try:
            os.remove(pth_file)
            log_message(f"Cleaned up local .pth file: {pth_file}")
        except Exception as e:
            log_message(f"Warning: Could not clean up .pth file: {e}")


def _write_local_pth_file(venv_path, pythonpath_to_add):
    """Write a .pth file to persist PYTHONPATH for subprocesses."""
    pth_file = _get_pth_file_path(venv_path)
    if not pth_file:
        log_message("Warning: Could not determine site-packages path")
        return False

    try:
        os.makedirs(os.path.dirname(pth_file), exist_ok=True)
        with open(pth_file, "w", encoding="utf-8") as f:
            f.write(f"# Temporary .pth file for local nopywer development\n")
            f.write(f"# This file is auto-generated by setup_dependencies\n")
            f.write(f"# It will be removed when switching back to wheel installation\n")
            f.write(f"{pythonpath_to_add}\n")
        log_message(f"✓ Created .pth file for local nopywer: {pth_file}")
        return True
    except Exception as e:
        log_message(f"Warning: Could not write .pth file: {e}")
        return False


def _step_setup_local_nopywer(local_path, venv_path, env):
    """STEP 4A: Use local nopywer from provided path via .pth file."""
    log_message(f"Using local nopywer from: {local_path}")

    pythonpath_to_add = _validate_local_nopywer(local_path)
    if not pythonpath_to_add:
        return False

    # Add to PYTHONPATH for current session
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = pythonpath_to_add + os.pathsep + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = pythonpath_to_add

    # Write .pth file so subprocesses can find it
    if not _write_local_pth_file(venv_path, pythonpath_to_add):
        log_message(
            "Warning: Could not write .pth file, but continuing with session PYTHONPATH"
        )

    log_message(f"✓ Local nopywer configured for current and future sessions")
    return True


def _step_install_wheel(venv_python, plugin_dir, env, force):
    """STEP 4B: Download and install nopywer from pre-built wheel."""
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


def _step_verify_installation(venv_python, check_env):
    """STEP 5: Final verification that nopywer.cli imports successfully."""
    result = _check_nopywer_import(venv_python, check_env)

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
    Orchestrates the installation of nopywer from a pre-built wheel or local path.

    :param force: If True, forces reinstall of nopywer.
    :param clean: If True, deletes the existing venv entirely first.
    :return: True if successful, False otherwise.
    """
    log_message("seting up nopywer plugin dependencies...")
    try:
        # Load configuration from nopywer.cfg
        global NOPYWER_VERSION
        NOPYWER_VERSION, NOPYWER_LOCAL_PATH = _load_config()

        plugin_dir = os.path.abspath(os.path.dirname(__file__))
        venv_path = get_venv_path()
        qgis_python = get_qgis_python_executable()

        # Isolate environment to prevent QGIS and conda path bleeding
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        # Clear conda-related variables that can cause DLL conflicts
        env.pop("CONDA_PREFIX", None)
        env.pop("CONDA_DEFAULT_ENV", None)
        env.pop("CONDA_SHLVL", None)
        for key in list(env.keys()):
            if key.startswith("CONDA_"):
                env.pop(key, None)

        # Execute installation steps in sequence
        if clean and not _step_cleanup_venv(venv_path):
            return False

        if not _step_create_venv(qgis_python, venv_path, plugin_dir, env):
            return False

        venv_python = get_venv_python()
        log_message(f"Using venv Python: {venv_python}")

        # Determine installation method
        if NOPYWER_LOCAL_PATH:
            # Using local path: set up .pth file for subprocesses
            if not _step_setup_local_nopywer(NOPYWER_LOCAL_PATH, venv_path, env):
                return False
            check_env = env
        else:
            # Using wheel installation: clean up local .pth file if it exists
            _cleanup_local_pth_file(venv_path)

            # Ensure pip is available first
            if not _step_ensure_pip(venv_python, env):
                return False

            # Check if already installed, then install if needed
            if _step_verify_nopywer(venv_python, force, env):
                return True
            if not _step_install_wheel(venv_python, plugin_dir, env, force):
                return False
            check_env = env

        return _step_verify_installation(venv_python, check_env)

    except Exception as e:
        log_message(f"Unexpected error during setup_dependencies: {e}")
        log_message(f"Traceback:\n{traceback.format_exc()}")
        return False


if __name__ == "__main__":
    setup_dependencies()
