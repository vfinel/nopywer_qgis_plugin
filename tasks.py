# -*- coding: utf-8 -*-
import subprocess
import json
import os
from qgis.core import QgsTask, QgsMessageLog, Qgis

class NopywerAnalysisTask(QgsTask):
    def __init__(self, description, python_exe, input_geojson):
        super().__init__(description, QgsTask.CanCancel)
        self.python_exe = python_exe
        self.input_geojson = input_geojson
        self.exception = None
        self.output_data = None

    def run(self):
        """
        This runs in a background thread.
        """
        QgsMessageLog.logMessage("Task started: run() executing...", "Nopywer", Qgis.Info)
        try:
            # We must isolate the environment. QGIS sets PYTHONPATH/PYTHONHOME
            # which can cause conflicts ("SRE module mismatch") in the venv.
            env = os.environ.copy()
            env.pop('PYTHONPATH', None)
            env.pop('PYTHONHOME', None)

            # Determine the path to the nopywer-analyze executable
            executable_dir = os.path.dirname(self.python_exe)
            analyze_exe = os.path.join(executable_dir, "nopywer-analyze")
            if os.name == "nt":
                analyze_exe += ".exe"

            QgsMessageLog.logMessage(f"Executing command: {analyze_exe} {self.input_geojson}", "Nopywer", Qgis.Info)

            # Check if the executable exists
            if not os.path.exists(analyze_exe):
                raise Exception(f"Analysis tool not found: {analyze_exe}")

            # Run nopywer-analyze -v <input_geojson>
            cmd = [analyze_exe, "-v", self.input_geojson]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            stdout, stderr = process.communicate()
            
            # Combine both for the log output
            self.output_data = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}".strip()
            
            if not self.output_data:
                self.output_data = "(No output captured from backend)"

            if process.returncode != 0:
                raise Exception(f"Nopywer failed with return code {process.returncode}")

            QgsMessageLog.logMessage("Subprocess finished successfully", "Nopywer", Qgis.Info)
            return True
            
        except Exception as e:
            self.exception = e
            QgsMessageLog.logMessage(f"Subprocess failed with exception: {e}", "Nopywer", Qgis.Critical)
            return False

    def finished(self, result):
        """
        This runs in the main GUI thread when run() returns.
        """
        print(f"DEBUG: Task finished. Result: {result}")
        QgsMessageLog.logMessage(f"Task finished. result={result}", "Nopywer", Qgis.Info)

        if self.output_data:
            # Print to the Python Console
            print("\n" + "="*20 + " NOPYWER OUTPUT " + "="*20)
            print(self.output_data)
            print("="*56 + "\n")
            
            # Log to the Nopywer tab in QGIS Log Messages
            QgsMessageLog.logMessage(
                f"Backend Output:\n{self.output_data}", 
                "Nopywer", Qgis.Info
            )

        if result:
            QgsMessageLog.logMessage(
                "Nopywer Analysis Finished Successfully!", 
                "Nopywer", Qgis.Success
            )
        else:
            # Log the error and stderr if it failed
            error_msg = f"Nopywer Analysis Failed: {self.exception}"
            print(f"ERROR: {error_msg}")
            QgsMessageLog.logMessage(error_msg, "Nopywer", Qgis.Critical)

    def cancel(self):
        QgsMessageLog.logMessage(
            f"Nopywer Analysis Cancelled by user", 
            "Nopywer", Qgis.Info
        )
        super().cancel()
