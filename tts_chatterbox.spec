# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Text-to-Speech with Chatterbox.

To build the executable:
    pyinstaller tts_chatterbox.spec

The resulting executable will be in dist/tts_chatterbox/
"""

import sys
from pathlib import Path

block_cipher = None

# Get the project root directory
project_root = Path(SPECPATH)

a = Analysis(
    [str(project_root / 'src' / 'tts_app' / 'main.py')],
    pathex=[str(project_root / 'src')],
    binaries=[],
    datas=[
        # Include any data files if needed
    ],
    hiddenimports=[
        # TTS imports
        'chatterbox',
        'chatterbox.tts',
        'chatterbox.tts_turbo',
        'chatterbox.mtl_tts',
        'torchaudio',
        'torch',
        # Document readers
        'pdfplumber',
        'docx',
        'markdown',
        # GUI
        'customtkinter',
        'CTkMessagebox',
        # Standard library
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'matplotlib',
        'numpy.testing',
        'scipy',
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
    console=False,  # Set to True for debugging
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
