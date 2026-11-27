# Asset catalog foundation

The first application-engine milestone is a read-only asset catalog. It indexes known game-asset extensions without executing binaries or modifying source files. It intentionally excludes arbitrary text/configuration files, executables, DLLs, scripts, symlinks, and common build/cache directories.

## Run

    python tools/build_asset_catalog.py PATH/TO/GAME/PATCH --output reports/asset-catalog.json

Add --hashes to calculate SHA-256 for every indexed asset. This is slower on large patch folders.

## Current recognition

- C3: validates the MAXFILE C3 00001 signature and counts known structural tags. It does not claim to decode geometry, skeletons, or animation.
- DDS: reads the standard 128-byte header and validates basic header dimensions.
- WDF and DMap: labels them as candidates only; their binary layouts are not yet decoded.
- Common image extensions: included in the catalog as unknown image assets pending a dedicated decoder/viewer.

The catalog is metadata only. It does not write back to game assets. Editing and export must be implemented as separate, format-specific modules with backups and round-trip tests.

## Safety guarantees

- No game executable or DLL is loaded or run.
- No source asset is modified.
- Symlinks are not followed.
- .txt, .exe, .dll, .bat, and other unlisted files are not indexed.
- Catalog output is written atomically through a temporary file.
