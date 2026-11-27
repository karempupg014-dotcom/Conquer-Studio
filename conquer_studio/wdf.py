"""Conservative reader/extractor for Conquer Online PFDW WDF archives.

The parser treats all archive values as untrusted and validates every range before
reading or writing. It does not infer original asset names from hash IDs.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import struct

MAGIC = b"PFDW"
HEADER = struct.Struct("<4sII")
ENTRY = struct.Struct("<IIII")
MAX_ENTRIES = 2_000_000
MAX_ENTRY_SIZE = 512 * 1024 * 1024

class WDFFormatError(ValueError):
    """Raised when a WDF archive is malformed or unsupported."""

@dataclass(frozen=True)
class WDFEntry:
    file_id: int
    offset: int
    size: int
    reserved: int

@dataclass(frozen=True)
class WDFArchive:
    path: Path
    file_size: int
    index_offset: int
    entries: tuple[WDFEntry, ...]

    @classmethod
    def open(cls, path: Path) -> "WDFArchive":
        path = Path(path)
        file_size = path.stat().st_size
        if file_size < HEADER.size:
            raise WDFFormatError("File is smaller than the WDF header")
        with path.open("rb") as stream:
            raw = stream.read(HEADER.size)
            magic, count, index_offset = HEADER.unpack(raw)
            if magic != MAGIC:
                raise WDFFormatError(f"Invalid WDF signature: {magic!r}")
            if count > MAX_ENTRIES:
                raise WDFFormatError(f"Entry count exceeds safety limit: {count}")
            index_size = count * ENTRY.size
            if index_offset < HEADER.size or index_offset > file_size or index_size > file_size - index_offset:
                raise WDFFormatError("Index table points outside the archive")
            stream.seek(index_offset)
            entries = []
            for i in range(count):
                file_id, offset, size, reserved = ENTRY.unpack(stream.read(ENTRY.size))
                if size > MAX_ENTRY_SIZE:
                    raise WDFFormatError(f"Entry {i} exceeds the per-file size safety limit")
                if offset < HEADER.size or offset > file_size or size > file_size - offset:
                    raise WDFFormatError(f"Entry {i} payload range is outside the archive")
                # Payloads must not overlap the index table.
                if size and offset < index_offset + index_size and offset + size > index_offset:
                    raise WDFFormatError(f"Entry {i} overlaps the index table")
                entries.append(WDFEntry(file_id, offset, size, reserved))
        return cls(path, file_size, index_offset, tuple(entries))

    def read_entry(self, entry: WDFEntry) -> bytes:
        if entry not in self.entries:
            raise ValueError("Entry does not belong to this archive")
        with self.path.open("rb") as stream:
            stream.seek(entry.offset)
            data = stream.read(entry.size)
        if len(data) != entry.size:
            raise WDFFormatError("Unexpected end of archive while reading payload")
        return data

    def manifest(self) -> dict:
        return {
            "format": "PFDW",
            "archive": self.path.name,
            "file_size": self.file_size,
            "index_offset": self.index_offset,
            "entry_count": len(self.entries),
            "entries": [
                {"id": f"{e.file_id:08X}", "id_decimal": e.file_id,
                 "offset": e.offset, "size": e.size, "reserved": e.reserved}
                for e in self.entries
            ],
            "note": "WDF stores hashed IDs, not original filenames. Names/extensions require a verified hash dictionary."
        }

    def extract(self, destination: Path) -> dict:
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        records = []
        names = [f"{entry.file_id:08X}.bin" for entry in self.entries]
        if len(set(names)) != len(names):
            raise WDFFormatError("Archive contains duplicate IDs; refusing ambiguous extraction")
        manifest_path = destination / "wdf-manifest.json"
        if manifest_path.exists():
            raise FileExistsError(f"Refusing to overwrite existing manifest: {manifest_path}")
        for name in names:
            if (destination / name).exists():
                raise FileExistsError(f"Refusing to overwrite existing file: {destination / name}")
        for entry, name in zip(self.entries, names):
            # Hash-only names; never interpret archive IDs as paths.
            target = destination / name
            data = self.read_entry(entry)
            target.write_bytes(data)
            records.append({"id": f"{entry.file_id:08X}", "file": name, "size": entry.size})
        manifest = {"archive": self.path.name, "entry_count": len(records), "files": records,
                    "note": "Extracted names are hash IDs; extensions are intentionally not guessed."}
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return manifest
