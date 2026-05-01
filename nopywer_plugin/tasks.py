# -*- coding: utf-8 -*-
import subprocess
import json
import os
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
            log_message(f"Backend Output:\n{self.output_data}")

        if result:
            log_message("Nopywer Analysis Finished Successfully!", Qgis.Success)
        else:
            # Log the error and stderr if it failed
            error_msg = f"Nopywer Analysis Failed: {self.exception}"
            log_message(error_msg, Qgis.Critical)

    def cancel(self):
        log_message("Nopywer Analysis Cancelled by user", Qgis.Info)
        super().cancel()
