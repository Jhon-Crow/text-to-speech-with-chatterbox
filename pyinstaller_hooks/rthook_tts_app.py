"""PyInstaller runtime hook for tts_app.

This runtime hook runs at application startup before any imports,
ensuring the Python path is correctly set up for the bundled environment.
"""

import sys
import os

def setup_tts_app_path():
    """Ensure tts_app package can be imported in PyInstaller bundle."""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        # sys._MEIPASS is the path where PyInstaller extracts bundled files
        base_path = sys._MEIPASS

        # Ensure base_path is in sys.path at the beginning
        if base_path not in sys.path:
            sys.path.insert(0, base_path)

        # Also add the tts_app package path explicitly
        tts_app_path = os.path.join(base_path, 'tts_app')
        if os.path.exists(tts_app_path) and tts_app_path not in sys.path:
            sys.path.insert(0, tts_app_path)

# Execute the path setup
setup_tts_app_path()
