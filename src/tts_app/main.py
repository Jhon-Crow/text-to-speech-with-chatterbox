"""Main entry point for the Text-to-Speech application."""

import logging
import sys
import os
from datetime import datetime


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


def _get_log_file_path():
    """Get the path for the log file next to the executable.

    Returns:
        Path to the log file, or None if not applicable.
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle - put log next to exe
        exe_dir = os.path.dirname(sys.executable)
    else:
        # Running from source - put log in current directory
        exe_dir = os.getcwd()

    return os.path.join(exe_dir, "tts_chatterbox.log")


# Set up package path before any tts_app imports
_setup_package_path()


def setup_logging():
    """Configure logging for the application with both console and file output."""
    log_file = _get_log_file_path()

    handlers = [
        logging.StreamHandler(sys.stdout)
    ]

    # Add file handler for error logging
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.WARNING)  # Log warnings and errors to file
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s\n"
            "    File: %(pathname)s:%(lineno)d\n"
        ))
        handlers.append(file_handler)
    except (OSError, PermissionError) as e:
        # If we can't write to log file, continue without it
        print(f"Warning: Could not create log file: {e}")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )


def main():
    """Run the TTS application."""
    setup_logging()

    from tts_app.gui.app import run_app
    run_app()


if __name__ == "__main__":
    main()
