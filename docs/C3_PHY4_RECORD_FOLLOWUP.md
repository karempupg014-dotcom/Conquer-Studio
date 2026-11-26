# C3 PHY4 Candidate Record Follow-up

Date: 2026-11-26

## Scope and safety
Read-only byte analysis of the three extracted sample files. No game executable or DLL was run. This is a research note, not a production decoder.

## Candidate 40-byte records
Using the previously observed candidate starts and counts:

| Sample | Candidate start | Records | Record bytes | Candidate record end |
|---|---:|---:|---:|---:|
| monster/100/1.c3 | 46 | 3172 | 40 | 126926 |
| Mount/809/8090000.C3 | 5316 | 1102 | 40 | 49396 |
| garment/001183485.C3 | 2404 | 929 | 40 | 39564 |

Across all records in all three samples:
- Bytes +0..+11 decode as three finite little-endian floats with plausible spatial ranges.
- Bytes +12..+19 decode as two finite little-endian floats in [0,1], consistent with candidate UV coordinates.
- Bytes +24..+31 contain two small integer values (candidate bone indices/IDs).
- Bytes +32..+39 decode as two floats in [0,1].
- The two floats at +32 and +36 sum to 1 within floating-point tolerance for every record in all three samples (3172/3172, 1102/1102, 929/929). This is strong evidence for two influence weights per vertex, but their association with the integer fields at +24/+28 is not yet proven.
- The 32-bit value at +20 is constant within each sample but differs by sample: 0xffffffff for the monster, 0 for mount and garment. Its meaning is unknown.

### First record examples
- Monster: `1b 9e 04 41 ec 51 a0 c0 65 09 37 c3 49 2e 2f 3f 3b 01 4d bf ff ff ff ff 18 00 00 00 01 00 00 00 00 00 80 3f 00 00 00 00`
- Mount: `5d f3 31 41 e0 88 e6 41 26 5c b6 c2 a1 85 3b 3f c3 70 55 3f 00 00 00 00 02 00 00 00 01 00 00 00 00 00 00 3f 00 00 00 3f`
- Garment: `4b c5 ce c1 ad 43 95 c0 f9 5c 07 c3 4b 11 c5 3d ee 06 90 3e 00 00 00 00 10 00 00 00 00 00 00 00 00 00 80 3f 00 00 00 00`

## Candidate index data: partially confirmed, topology unresolved
Immediately after the candidate vertex records, monster and garment samples contain:
- uint32 candidate count
- uint32 zero/reserved value
- a sequence of uint16 values, each less than the candidate vertex count.

Monster:
- candidate count 4488; 4488 is divisible by 3.
- all 4488 values are within [0,1015] for 3172 candidate vertices.
- grouping sequentially into triples yields no degenerate triples in this sample.
- This is consistent with a triangle-list index buffer, but does not alone prove primitive type, winding, or submesh boundaries.

Garment:
- candidate count 1265; this is not divisible by 3.
- all 1265 values are within [0,335] for 929 candidate vertices.
- The odd count means this cannot be accepted as one complete triangle-list buffer. It may involve strips, multiple submeshes, a different count interpretation, or additional framing. Do not export as triangles.

Mount:
- bytes immediately after the candidate records do not match the same simple count + reserved + uint16 index pattern. The mount residual requires a separate parser.

## Next required validation
1. Identify all submesh/material boundaries and explain the remaining bytes after each candidate index sequence.
2. Confirm whether garment indices are strips, multiple buffers, or something else; inspect restart markers and section framing.
3. Confirm index winding and render a test mesh in an independent viewer before enabling OBJ/glTF export.
4. Correlate the two candidate integer fields with actual skeleton/bone tables and the two weights.
5. Decode the constant +20 field and mount's distinct residual layout.
6. Only after those tests should a production PHY4 decoder and 3D viewer be implemented.

## Explicit non-claims
This note does not establish a complete C3 format specification, confirmed bone semantics, confirmed topology for every model, or a working Conquer Studio 3D viewer.
