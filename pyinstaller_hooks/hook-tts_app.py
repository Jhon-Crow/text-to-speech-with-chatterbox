"""PyInstaller hook for tts_app package.

This hook ensures all tts_app submodules are properly collected and included
in the PyInstaller bundle, preventing import errors at runtime.
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all submodules of tts_app to ensure they're included in the bundle
hiddenimports = collect_submodules('tts_app')

# Collect any data files if present
datas = collect_data_files('tts_app')
