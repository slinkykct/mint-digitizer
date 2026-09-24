MAZE.INT — Auto-Digitized Embroidery Files (v2, bug-fixed)
=============================================================

Fixed in this pass:
- Crash on some source images: self-intersecting traced shapes were being
  auto-repaired into a MultiPolygon by Shapely, but the code assumed every
  shape was a plain Polygon and crashed. Fixed by flattening MultiPolygons
  into separate simple shapes. Verified against all 4 of your uploaded
  images -- no crashes now.
- Confirmed (not a code bug, a source-material limit): the black debossed
  coin mockup and the gray woven-patch photo do NOT digitize well -- their
  shading/lighting gets picked up as false edges. Only the flat vector logo
  (the one with a plain white background, no photo lighting) is suitable
  input. Always digitize from flat art, never from a rendered mockup photo.

Files:
  mazeint_100mm.{dst,pes,jef,exp}   -> 100mm-wide version
  mazeint_150mm.{dst,pes,jef,exp}   -> 150mm-wide version (caption line reads better)
  mazeint_100mm_stitch_preview.png  -> stitch-path preview
  digitize_v2.py                    -> the tool
  requirements.txt                  -> exact dependencies (pinned, tested clean install)

Still NOT included: .emb (Wilcom's closed format, no public spec -- no tool
can write it). .dst is the universal format every shop/machine reads.

============================================================
HOW TO RUN digitize_v2.py
============================================================

You need Python 3.9+ somewhere. Three options, easiest first:

OPTION 1 — Your own computer (recommended, free, no ongoing cost)
  1. Install Python: https://python.org/downloads (Windows/Mac) or it's
     already on most Linux/Mac systems (`python3 --version` to check).
  2. Open a terminal (Command Prompt/PowerShell on Windows, Terminal on Mac/Linux)
     in the folder where you unzipped this.
  3. Install dependencies:
       pip install -r requirements.txt
  4. Run it:
       python3 digitize_v2.py your_logo.jpg output_name --width-mm 100
  5. Files land as output_name.dst / .pes / .jef / .exp in that same folder.
  No server, no account, no deployment needed -- it's a local script.

OPTION 2 — Google Colab (if you don't want to install anything)
  1. Go to https://colab.research.google.com -> New Notebook
  2. Upload digitize_v2.py and your logo image (folder icon on the left sidebar)
  3. In a cell, run:
       !pip install -r requirements.txt   # or paste the 4 lines from that file
       !python digitize_v2.py your_logo.jpg output_name --width-mm 100
  4. Download the generated .dst/.pes/.jef files from the file browser
  Free, runs in your browser, nothing to install -- good if this is a
  one-off or you're on a machine you can't install software on.

OPTION 3 — A small cloud VM / server (only if you want this running
  unattended for a team, e.g. behind a simple upload form)
  Any basic Linux VM (DigitalOcean, AWS EC2 t3.micro, etc.) works:
       sudo apt install python3-pip
       pip3 install -r requirements.txt
       python3 digitize_v2.py logo.jpg out --width-mm 100
  This is overkill for personal/one-off use -- only worth it if you're
  wrapping this in a web form for other people to upload logos to.

Full option list:
  python3 digitize_v2.py --help

Preview/tweak before sewing: open the .dst in Inkscape + the free Ink/Stitch
extension (Extensions > Ink/Stitch > Visualise and Export > Simulator).
