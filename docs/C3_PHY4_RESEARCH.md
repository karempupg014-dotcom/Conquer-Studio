# C3 PHY4 research notes (experimental)

## Scope and safety

These notes describe read-only inspection of selected C3 assets from the
provided Conquer Online client archive. They are not a complete C3 format
specification. No game executable, DLL, script, or suspicious asset is run.

## Verified observations in the sampled client

The sampled files begin with the 16-byte signature `MAXFILE C3 00001`.
The root geometry section is tagged `PHY4`. For the sampled root
`v_body` sections, the bytes after the name contain three 32-bit values.
The second value behaves as a candidate vertex count, and a 40-byte
record stride fits inside the declared section length.

| Sample | Candidate record count | Candidate record start | XYZ finite | Candidate UV finite |
|---|---:|---:|---|---|
| monster/100/1.c3 | 3172 | 46 | yes | yes |
| Mount/809/8090000.C3 | 1102 | 5316 | yes | yes |
| mesh/x/garment/001183485.C3 | 929 | 2404 | yes | yes |

Across these three samples, the first 12 bytes of each candidate record
decode as three finite little-endian float values (XYZ). The next 8 bytes
also decode as finite values in ranges consistent with texture coordinates.
This is strong evidence for a common candidate record layout, but the
remaining 20 bytes have not been semantically identified.

## Candidate index data

For the monster and garment samples, the bytes immediately following the
candidate vertex records begin with a plausible 32-bit count, a zero
32-bit value, and 16-bit values that all fall below the candidate vertex
count. The monster count is 4488 (divisible by 3); the garment count is
1265 (not divisible by 3). Therefore this must not yet be called a confirmed
triangle index list. The horse sample has a different-looking continuation
after its candidate records, so the same heuristic does not identify an
index buffer there.

No OBJ/mesh export is enabled by this probe. Doing so before the index
topology, record fields, submesh layout, and transforms are confirmed could
produce convincing but incorrect geometry.

## Version compatibility warning

A public C3 WebGL viewer describes a different PHY parser and a 76-byte
vertex record for its bundled client-5065 assets. That is useful as a
reference, but it must not be copied blindly into this sampled client:
our observed root `PHY4` sections and candidate 40-byte records do not
match that published layout. See:
https://github.com/javinladish/C3-WebGL-Loader

## Next validation tasks

1. Decode the remaining fields in the 40-byte record using byte-level
   comparisons across body, mount, and garment samples.
2. Locate all index/submesh blocks, including the horse continuation.
3. Confirm triangle-list versus strip/fan topology and winding.
4. Validate exported geometry in an independent 3D viewer before enabling
   editing or saving.
5. Decode skeleton/attachment and MOTI animation chunks separately.

The accompanying `tools/c3_phy4_candidate_probe.py` prints these candidate
measurements without asserting a full decode.
