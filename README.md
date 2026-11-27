# Conquer Studio

A work-in-progress toolkit for inspecting and eventually editing Conquer Online assets.

## Current status

- Read-only C3 structural research and experimental PHY4 field audits.
- Read-only asset catalog foundation for C3, DDS, WDF/DMap candidates, and common image assets.
- DDS top-mip decoding and PNG export for BC1/DXT1, BC2/DXT3, and BC3/DXT5 (`tools/dds_to_png.py`) and batch WDF texture export (`tools/wdf_textures_to_png.py`).
- No production C3 mesh decoder or game-compatible asset writer is claimed yet.

See docs/ASSET_CATALOG.md, docs/C3_PHY4_RESEARCH.md, and docs/DDS_TEXTURES.md.

## Launch the desktop texture browser (Windows 10/11, 64-bit)

Install the optional GUI dependency and the project:

    py -m pip install -e ".[gui]"
    py tools/run_studio.py

The first desktop milestone can open WDF archives and DDS files, preview supported BC1/BC2/BC3 textures, export the selected texture, and batch-export supported textures from a WDF. It is a texture browser foundation, not yet the complete C3 model/map editor.

## Build an asset catalog

    python tools/build_asset_catalog.py PATH/TO/GAME/PATCH --output reports/asset-catalog.json

Run tests:

    python -m unittest discover -s tests -v

The project does not execute game binaries or DLLs and does not modify source assets during cataloging.
