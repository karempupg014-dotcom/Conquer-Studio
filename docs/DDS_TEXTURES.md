# DDS texture decoding

The project can decode the top mip level of common block-compressed DDS textures:

- BC1 / DXT1, including the one-bit transparent mode.
- BC2 / DXT3, including explicit 4-bit alpha.
- BC3 / DXT5, including interpolated alpha.

The decoder writes standard RGBA PNG files and does not modify the source DDS.

## Convert one texture

    python tools/dds_to_png.py path/to/texture.dds output/texture.png

Existing output files are protected. To intentionally replace one:

    python tools/dds_to_png.py path/to/texture.dds output/texture.png --force

Only the top mip level is exported. BC4, BC5, uncompressed DDS, cubemaps, texture arrays, and other DXGI formats are not yet decoded to PNG. Header inspection may recognize more formats than the image decoder supports.

## Export textures directly from a WDF archive

    python tools/wdf_textures_to_png.py garments.wdf output/garments-textures

The exporter scans the archive, writes supported textures as `HASHID.png`, and creates `texture-export-manifest.json` with exported, unsupported, and non-DDS entry counts. It refuses to overwrite existing output files. Original filenames are not recovered because WDF stores hashed IDs.

## Current limitations

- No graphical texture browser has been implemented yet.
- No WDF batch extraction-to-PNG workflow is implemented yet.
- BC2/BC3 decoding currently targets the common DXT3/DXT5 block layout; premultiplied-alpha DXT2/DXT4 handling has not been separately validated.
- Mip-chain completeness is not fully validated; the parser checks that the base level fits.
