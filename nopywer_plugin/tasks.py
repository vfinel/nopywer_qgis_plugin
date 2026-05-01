# -*- coding: utf-8 -*-
import subprocess
import json
import os
import sys
from qgis.core import QgsTask, QgsMessageLog, Qgis


from .utils import log_message


class NopywerAnalysisTask(QgsTask):
    def __init__(self, description, python_exe, input_geojson, output_geojson):
        super().__init__(description, QgsTask.CanCancel)
        self.python_exe = python_exe
        self.input_geojson = input_geojson
        self.output_geojson = output_geojson
        self.exception = None
        self.output_data = None

    def run(self):
        """
        This runs in a background thread.
        """
        log_message("Task started: run() executing...")
        try:
            # We must isolate the environment. QGIS sets PYTHONPATH/PYTHONHOME
            # which can cause conflicts ("SRE module mismatch") in the venv.
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            env.pop("PYTHONHOME", None)

            # Determine the path to the nopywer-analyze executable
            executable_dir = os.path.dirname(self.python_exe)
            analyze_exe = os.path.join(executable_dir, "nopywer-analyze")
            if os.name == "nt":
                analyze_exe += ".exe"

            log_message(f"Executing command: {analyze_exe} {self.input_geojson}")

            # Check if the executable exists
            if not os.path.exists(analyze_exe):
                raise Exception(f"Analysis tool not found: {analyze_exe}")

            # Run nopywer-analyze -v <input_geojson>
            cmd = [
                analyze_exe,
                "-v",
                self.input_geojson,
                "-o",  # this prevents to print to geojson in the console
                self.output_geojson,
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0,
            )

            stdout, stderr = process.communicate()

            # Combine both for the log output
            self.output_data = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}".strip()

            if not self.output_data:
                self.output_data = "(No output captured from backend)"

            if process.returncode != 0:
                raise Exception(f"Nopywer failed with return code {process.returncode}")

            log_message("Subprocess finished successfully")
            return True

        except Exception as e:
            self.exception = e
            log_message(f"Subprocess failed with exception: {e}", Qgis.Critical)
            return False

    def finished(self, result):
        """
        This runs in the main GUI thread when run() returns.
        """
        log_message(f"Task finished. result={result}")

        if self.output_data:
            # log_message already handles tab replacement and printing to console
            log_message(f"nopywer output:\n{self.output_data}")

        if result:
            log_message("Nopywer Analysis Finished Successfully!", Qgis.Success)
        else:
            # Log the error and stderr if it failed
            error_msg = f"Nopywer Analysis Failed: {self.exception}"
            log_message(error_msg, Qgis.Critical)

    def cancel(self):
        log_message("Nopywer Analysis Cancelled by user", Qgis.Info)
        super().cancel()


class NopywerOptimizeTask(QgsTask):
    def __init__(self, description, python_exe, input_geojson, output_geojson):
        super().__init__(description, QgsTask.CanCancel)
        self.python_exe = python_exe
        self.input_geojson = input_geojson
        self.output_geojson = output_geojson
        self.exception = None
        self.output_data = None

    def run(self):
        """
        This runs in a background thread.
        """
        log_message("Task started: Optimization running...")
        try:
            # Isolate environment to avoid conflicts with QGIS's Python
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            env.pop("PYTHONHOME", None)

            # Read input GeoJSON
            with open(self.input_geojson, "r") as f:
                geojson_data = json.load(f)

            # Execute optimization in a subprocess to avoid conflicts
            cmd = [
                self.python_exe,
                "-c",
                f"""
import json
import sys
sys.path.insert(0, {repr(os.path.dirname(self.python_exe))})

from nopywer.models import PowerGrid
from nopywer.optimize import optimize_layout

# Load GeoJSON
with open({repr(self.input_geojson)}, 'r') as f:
    geojson = json.load(f)

# Convert to PowerGrid
grid = PowerGrid.from_geojson(geojson)

# Optimize the layout
optimized_grid = optimize_layout(grid)

# Convert back to GeoJSON and save
output_geojson = optimized_grid.to_geojson()
with open({repr(self.output_geojson)}, 'w') as f:
    json.dump(output_geojson, f)

print("Optimization completed successfully")
""",
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW
                if hasattr(subprocess, "CREATE_NO_WINDOW")
                else 0,
            )

            stdout, stderr = process.communicate()
            self.output_data = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}".strip()

            if not self.output_data:
                self.output_data = "(No output captured from backend)"

            if process.returncode != 0:
                raise Exception(
                    f"Optimization failed with return code {process.returncode}"
                )

            log_message("Optimization subprocess finished successfully")
            return True

        except Exception as e:
            self.exception = e
            log_message(f"Optimization failed with exception: {e}", Qgis.Critical)
            return False

    def finished(self, result):
        """
        This runs in the main GUI thread when run() returns.
        """
        log_message(f"Optimization task finished. result={result}")

        if self.output_data:
            log_message(f"nopywer optimization output:\n{self.output_data}")

        if result:
            log_message("Nopywer Optimization Finished Successfully!", Qgis.Success)
        else:
            error_msg = f"Nopywer Optimization Failed: {self.exception}"
            log_message(error_msg, Qgis.Critical)

    def cancel(self):
        log_message("Nopywer Optimization Cancelled by user", Qgis.Info)
        super().cancel()
