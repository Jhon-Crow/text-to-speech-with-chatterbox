# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Text-to-Speech with Chatterbox.

To build the executable:
    pyinstaller tts_chatterbox.spec

To build with debug console (shows errors):
    pyinstaller tts_chatterbox.spec -- --debug

The resulting executable will be in dist/tts_chatterbox/
"""

import sys
from pathlib import Path

block_cipher = None

# Get the project root directory
project_root = Path(SPECPATH)

# Check for debug mode via command line
# Use: pyinstaller tts_chatterbox.spec -- --debug
DEBUG_MODE = '--debug' in sys.argv

a = Analysis(
    [str(project_root / 'src' / 'tts_app' / 'main.py')],
    pathex=[str(project_root / 'src')],
    binaries=[],
    datas=[
        # Include any data files if needed
    ],
    hiddenimports=[
        # Application modules (explicit imports for PyInstaller)
        'tts_app',
        'tts_app.gui',
        'tts_app.gui.app',
        'tts_app.readers',
        'tts_app.readers.base',
        'tts_app.readers.registry',
        'tts_app.readers.pdf_reader',
        'tts_app.readers.doc_reader',
        'tts_app.readers.docx_reader',
        'tts_app.readers.text_reader',
        'tts_app.readers.markdown_reader',
        'tts_app.readers.rtf_reader',
        'tts_app.preprocessors',
        'tts_app.preprocessors.base',
        'tts_app.preprocessors.pipeline',
        'tts_app.preprocessors.footnotes',
        'tts_app.preprocessors.page_numbers',
        'tts_app.tts',
        'tts_app.tts.base',
        'tts_app.tts.chatterbox',
        # TTS imports
        'chatterbox',
        'chatterbox.tts',
        'chatterbox.tts_turbo',
        'chatterbox.mtl_tts',
        'torchaudio',
        'torch',
        # Scientific computing (required by chatterbox)
        'scipy',
        'scipy.signal',
        'scipy.io',
        'scipy.io.wavfile',
        # Document readers
        'pdfplumber',
        'docx',
        'markdown',
        'striprtf',
        # GUI
        'customtkinter',
        'CTkMessagebox',
        # Standard library
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
    ],
    hookspath=[str(project_root / 'pyinstaller_hooks')],
    hooksconfig={},
    runtime_hooks=[str(project_root / 'pyinstaller_hooks' / 'rthook_tts_app.py')],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'matplotlib',
        'numpy.testing',
        # Note: scipy is required by chatterbox-tts, do not exclude it
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='tts_chatterbox',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=DEBUG_MODE,  # Set DEBUG_MODE=True or use -- --debug for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='tts_chatterbox',
)
