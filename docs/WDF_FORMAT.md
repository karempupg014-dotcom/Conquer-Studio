# WDF archive reader

The reader implements the documented Conquer Online WDF layout:

- 12-byte little-endian header: ASCII magic `PFDW`, uint32 entry count, uint32 absolute index offset.
- Index table entries are 16 bytes: uint32 hashed file ID, uint32 absolute payload offset, uint32 payload size, uint32 reserved field.
- Payloads are addressed by absolute offsets.

This is based on the community format walkthrough: https://cooldown.dev/topic/860-teach-learn-tutorial-guide-the-wdf-file-format/

## Commands

Inspect the index without extracting:

    python tools/wdf_tool.py inspect garments.wdf

Extract payloads using safe hash-based names:

    python tools/wdf_tool.py extract garments.wdf extracted/garments

## Important limitations

WDF stores hashed IDs, not original filenames. The tool therefore writes names such as `1234ABCD.bin`; it does not invent original paths or extensions. A verified hash-to-path dictionary can be added separately.

The reader validates archive bounds, index bounds, payload ranges, and index overlap. It enforces limits on entry count and per-entry size. It never executes extracted content. Extraction refuses to overwrite existing output files.

This milestone is read/extract only. Rebuilding WDF archives and modifying game assets are not implemented yet.
