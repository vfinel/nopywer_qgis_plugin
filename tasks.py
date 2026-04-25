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

            # Check if the executable exists
            if not os.path.exists(analyze_exe):
                raise Exception(f"Analysis tool not found: {analyze_exe}")

            # Run nopywer-analyze <input_geojson>
            cmd = [analyze_exe, self.input_geojson]
            
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
            
            if process.returncode != 0:
                raise Exception(f"Nopywer failed: {stderr}")
            
            # We expect the output to be the resulting GeoJSON
            self.output_data = stdout
            return True
            
        except Exception as e:
            self.exception = e
            return False

    def finished(self, result):
        """
        This runs in the main GUI thread when run() returns.
        """
        if result:
            QgsMessageLog.logMessage(
                f"Nopywer Analysis Finished!", 
                "Nopywer", Qgis.Success
            )
            # Here we will eventually load the result into QGIS
        else:
            QgsMessageLog.logMessage(
                f"Nopywer Analysis Failed: {self.exception}", 
                "Nopywer", Qgis.Critical
            )

    def cancel(self):
        QgsMessageLog.logMessage(
            f"Nopywer Analysis Cancelled by user", 
            "Nopywer", Qgis.Info
        )
        super().cancel()
