import sys
import subprocess
import os
import shutil


def get_venv_path():
    """Returns the absolute path to the virtual environment folder."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".venv"))


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
            
    return "uv" # Fallback to name and hope for the best

def setup_dependencies(force=False, clean=False):
    """
    Uses uv to create a virtual environment and install nopywer.
    :param force: If True, runs the install command even if nopywer is present (updates).
    :param clean: If True, deletes the existing venv first.
    """
    plugin_dir = os.path.abspath(os.path.dirname(__file__))
    venv_path = get_venv_path()
    uv_path = find_uv()
    
    # Isolate environment
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    
    if clean and os.path.exists(venv_path):
        print(f"Cleaning: Removing existing venv at {venv_path}...")
        try:
            shutil.rmtree(venv_path)
        except Exception as e:
            print(f"Could not remove venv: {e}")
            return False

    # 1. Create venv if needed
    if not os.path.exists(venv_path):
        print(f"Creating virtual environment using {uv_path}...")
        try:
            subprocess.check_call([uv_path, "venv", venv_path], cwd=plugin_dir, env=env)
        except Exception as e:
            print(f"Failed to create venv: {e}")
            return False

    python_exe = get_venv_python()

    # 2. Check if nopywer is already installed (skip if not forcing)
    if not force:
        try:
            subprocess.check_call(
                [python_exe, "-c", "import nopywer"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env
            )
            return True
        except:
            print("nopywer missing or venv broken. Installing...")

    # 3. Install/Update nopywer from GitHub ZIP
    branch = "qgis_plugin"
    zip_url = f"https://github.com/vfinel/nopywer/archive/refs/heads/{branch}.zip"

    if force:
        print(f"Refreshing nopywer from {zip_url}...")
    else:
        print(f"Installing nopywer from {zip_url}...")

    try:
        # Use uv pip install on the ZIP URL
        cmd = [uv_path, "pip", "install", "--python", python_exe, zip_url]
        
        # If forcing, we want to ensure we get the latest ZIP content
        if force:
            cmd.append("--refresh")

        result = subprocess.run(
            cmd, 
            cwd=plugin_dir,
            capture_output=True,
            text=True,
            env=env
        )
        
        if result.returncode != 0:
            print(f"uv pip install failed with exit code {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False

        print("Successfully installed nopywer!")
        return True
    except Exception as e:
        print(f"Failed to execute install command: {e}")
        return False


if __name__ == "__main__":
    setup_dependencies()
