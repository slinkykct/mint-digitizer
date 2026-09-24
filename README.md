# mint-digitizer

A cross-platform embroidery digitizer for flat logos and simple artwork.

This project converts logo-style artwork into embroidery files such as `.dst`, `.pes`, `.jef`, and `.exp`.

## What this is for

- Flat art and vector-style logos
- High-contrast black-on-white or white-on-black artwork
- Simple text and icon marks
- Quick proofing before sending a final design to a sewing shop

## What to avoid

- Photos and realistic shading
- Dark backgrounds with lighting/shadows
- Busy mockups or product photos
- Thin anti-aliased lines unless cleaned up first

## Quick install from GitHub on Linux / ChromeOS

Use the included self-healing installer. It detects the OS, creates the proper virtual environment, installs every dependency, validates imports, and recreates the environment if anything fails.

```bash
git clone https://github.com/slinkykct/mint-digitizer.git
cd mint-digitizer
python3 install.py
```

This will create a local environment at `.mazeint_venv` and install the project with all required dependencies.

### Upgrade an existing Linux / ChromeOS install

Run this one command from any terminal:

```bash
cd /home/mint/websites/mazeint_embroidery_final && git pull --ff-only origin main && . .mazeint_venv/bin/activate && python -m pip install -e . && ./mazeint-update
```

For a clone stored somewhere else, replace the path after `cd` with your project folder.

### Upgrade an existing Windows install

Run this from PowerShell in the project folder:

```powershell
git pull --ff-only origin main; .\.mazeint_venv\Scripts\Activate.ps1; python -m pip install -e .; mazeint-update
```

If PowerShell blocks local scripts, run the same command from Command Prompt instead:

```bat
git pull --ff-only origin main && .mazeint_venv\Scripts\activate.bat && python -m pip install -e . && mazeint-update
```

### Next release notes

Copy and paste this section into the GitHub release description when publishing version `0.1.1`:

```markdown
## MazeInt v0.1.1

- Improved installer stability and self-healing setup
- Better Linux, ChromeOS, and Windows installation flow
- Added a branded splash screen, app icon, and polished GUI details
- Improved embroidery centering and alignment for cleaner output
- Added updater support for checking and applying the latest release
- Added validation to reduce invalid exports and file corruption risks

### Install

- Linux / ChromeOS: `python3 install.py`
- Windows: `py install.py`
- Launch: `./run_gui.sh` or `run_gui.bat`
```

### Launch after installation

#### Linux / ChromeOS

```bash
./run_gui.sh
```

Or launch from the command line:

```bash
./mazeint-cli your_logo.png output_name --width-mm 100
```

The repo also installs:

```bash
./mazeint-update
```

This checks GitHub for a newer release and can update the app.

### GitHub Pages / PWA app

The landing page is published at:

```text
https://slinkykct.github.io/mint-digitizer/
```

To enable Pages in GitHub:
1. Open your repo on GitHub
2. Go to Settings -> Pages
3. Set source to GitHub Actions
4. Push the repo and let the Pages workflow deploy the static site

The repo includes a ready-to-use workflow for that deploy.

## Install on Windows, Linux, or ChromeOS

### Recommended: self-healing installer

From the project folder:

#### Windows

```powershell
py install.py
```

#### Linux / ChromeOS

```bash
python3 install.py
```

This installer:
- detects the current OS automatically
- creates a project-local virtual environment
- installs the required Python dependencies from `requirements.txt`
- installs the package in editable mode
- validates that OpenCV, NumPy, Shapely, and pyembroidery all import correctly
- repairs the environment automatically if anything fails
- creates GUI and CLI launchers for the user

### Manual install (fallback)

If you prefer to install manually:

```bash
python3 -m venv .mazeint_venv
. .mazeint_venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -e .
```

On Windows:

```powershell
py -m venv .mazeint_venv
.\.mazeint_venv\Scripts\activate
py -m pip install --upgrade pip setuptools wheel
py -m pip install -r requirements.txt
py -m pip install -e .
```

### GUI launch commands

#### Windows

```powershell
run_gui.bat
```

#### Linux / ChromeOS

```bash
./run_gui.sh
```

### CLI launch commands

```bash
mazeint-digitizer your_logo.png output_name --width-mm 100
```

Or from the repo directly:

```bash
python -m mazeint_digitizer.core your_logo.png output_name --width-mm 100
```

## Using other logos

1. Open the GUI.
2. Choose any flat logo image.
3. Adjust width, spacing, and stitch threshold.
4. Click Generate embroidery files.
5. Export the generated stitch files to the selected folder.

For best results, prepare the logo as:

- clean black and white or a single-color silhouette
- transparent or plain background
- solid fills rather than grayscale shading
- consistent stroke thickness

The GUI also supports an optional text layer. Enter wording, choose a font style
and size, select its thread color, and preview it before exporting the embroidery files.

## CLI example

```bash
mazeint-digitizer logo.png my_logo --width-mm 100 --row-spacing-mm 0.5 --angle 45
```

## Basic development

```bash
python -m pip install -e .[dev]
python -m pytest
```

## Notes

This is an auto-digitizer, not a full manual-digitizing suite. It works best on simple, flat artwork and produces a proofing design rather than a production-perfect final file.

## Using other logos

1. Open the GUI.
2. Choose any flat logo image.
3. Adjust width, spacing, and stitch threshold.
4. Click Generate embroidery files.
5. Export the generated stitch files to the selected folder.

For best results, prepare the logo as:

- clean black and white or a single-color silhouette
- transparent or plain background
- solid fills rather than grayscale shading
- consistent stroke thickness

## CLI example

```bash
mazeint-digitizer logo.png my_logo --width-mm 100 --row-spacing-mm 0.5 --angle 45
```

## Basic development

```bash
python -m pip install -e .[dev]
python -m pytest
```

## Notes

This is an auto-digitizer, not a full manual-digitizing suite. It works best on simple, flat artwork and produces a proofing design rather than a production-perfect final file.