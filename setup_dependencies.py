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
        os.path.join(venv_path, "bin", "python"),          # Linux/Mac
        os.path.join(venv_path, "bin", "python3"),         # Linux/Mac fallback
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return os.path.abspath(path)
            
    # Fallback default if not created yet
    if sys.platform == "win32":
        return os.path.abspath(possible_paths[0])
    return os.path.abspath(possible_paths[1])

def setup_dependencies():
    """
    Uses uv to create a virtual environment and install nopywer.
    """
    plugin_dir = os.path.abspath(os.path.dirname(__file__))
    venv_path = get_venv_path()
    
    # 1. Create venv if needed
    if not os.path.exists(venv_path):
        print(f"Creating virtual environment at {venv_path}...")
        try:
            subprocess.check_call(["uv", "venv", venv_path], cwd=plugin_dir)
        except Exception as e:
            print(f"Failed to create venv: {e}")
            return False

    python_exe = get_venv_python()

    # 2. Check if nopywer is already installed and working
    try:
        subprocess.check_call([python_exe, "-c", "import nopywer"], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
        return True
    except:
        print("nopywer missing or venv broken. Installing...")

    # 3. Install nopywer from GitHub
    github_url = "git+https://github.com/vfinel/nopywer.git"
    print(f"Installing nopywer from {github_url}...")
    
    try:
        # Use uv pip install which is extremely fast and agnostic
        subprocess.check_call([
            "uv", "pip", "install", 
            "--python", python_exe,
            github_url
        ], cwd=plugin_dir)
        
        print("Successfully installed nopywer!")
        return True
    except Exception as e:
        print(f"Failed to install nopywer: {e}")
        return False

if __name__ == "__main__":
    setup_dependencies()
