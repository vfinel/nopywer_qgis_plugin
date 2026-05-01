# -*- coding: utf-8 -*-
from qgis.core import QgsMessageLog, Qgis


def log_message(message, level=Qgis.Info):
    """
    Logs a message to the Nopywer tab in QGIS Log Messages,
    ensuring tab characters and multiple spaces are preserved for correct rendering.
    """
    if not isinstance(message, str):
        message = str(message)

    # 1. Replace tabs with 4 spaces
    message = message.replace("\t", "    ")

    # 2. Replace standard spaces with non-breaking spaces to prevent QGIS Log Panel from collapsing them
    # We use the Unicode non-breaking space \u00A0
    clean_message = message.replace(" ", "\u00a0")

    QgsMessageLog.logMessage(clean_message, "Nopywer", level)

    # Also print to python console for debugging (using original message for better console behavior)
    if level == Qgis.Critical:
        print(f"ERROR: {message}")
    else:
        print(message)
