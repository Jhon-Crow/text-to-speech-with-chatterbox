"""Main entry point for the Text-to-Speech application."""

import logging
import sys
import os


def _setup_package_path():
    """Set up the Python path for PyInstaller compatibility.

    When running as a PyInstaller-bundled executable, the package context
    may not be properly established. This function ensures the src directory
    is in sys.path so that absolute imports like 'from tts_app.xxx' work correctly.

    For PyInstaller, sys._MEIPASS contains the path to the extracted bundle.
    For normal execution, we add the parent of the tts_app package to the path.
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running from source
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if base_path not in sys.path:
        sys.path.insert(0, base_path)


# Set up package path before any tts_app imports
_setup_package_path()


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Run the TTS application."""
    setup_logging()

    from tts_app.gui.app import run_app
    run_app()


if __name__ == "__main__":
    main()
