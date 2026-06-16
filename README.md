# PCS Scrubber

Process raw CSV contact files, strip prefixes, assign channels, deduplicate contact IDs, and output a clean 3-column CSV.

## Build

The Windows `.exe` is built automatically via GitHub Actions on push to `main`. Download the artifact from the Actions tab.

To build manually on Windows:
```
pip install -r requirements.txt
pyinstaller --onefile --windowed --name "PCS Scrubber" --icon icon.ico --hidden-import tkinterdnd2 --hidden-import PIL --collect-all tkinterdnd2 --add-data "icon.png;." --add-data "icon.ico;." --version-file version_info.txt pcs_scrubber.py
```
