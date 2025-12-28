"""Main entry point for the Text-to-Speech application."""

import logging
import sys


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
