# Conquer Studio

A work-in-progress toolkit for inspecting and eventually editing Conquer Online assets.

## Current status

- Read-only C3 structural research and experimental PHY4 field audits.
- Read-only asset catalog foundation for C3, DDS, WDF/DMap candidates, and common image assets.
- No production C3 mesh decoder or game-compatible asset writer is claimed yet.

See docs/ASSET_CATALOG.md and docs/C3_PHY4_RESEARCH.md.

## Build an asset catalog

    python tools/build_asset_catalog.py PATH/TO/GAME/PATCH --output reports/asset-catalog.json

Run tests:

    python -m unittest discover -s tests -v

The project does not execute game binaries or DLLs and does not modify source assets during cataloging.
