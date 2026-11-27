# PHY4 candidate skinning-field audit

Date: 2026-11-27

## Why this follow-up exists

The earlier 40-byte candidate-record note described offsets +24/+28 as small integer fields and +32/+36 as two floats whose sum is 1. This follow-up separates those fields explicitly so that future analysis does not accidentally interpret the integer words as floating-point numbers.

## Working field map (not a confirmed specification)

| Byte offsets | Current interpretation | Confidence |
|---|---|---|
| +0..+11 | 3 little-endian float32 values, candidate XYZ | Strong structural observation |
| +12..+19 | 2 little-endian float32 values, candidate UV | Plausible; texture mapping not yet visually validated |
| +20..+23 | uint32, constant within each of the three samples but different across samples | Value observed; meaning unknown |
| +24..+27 | uint32 candidate ID A | Integer field observed; bone meaning unconfirmed |
| +28..+31 | uint32 candidate ID B | Integer field observed; bone meaning unconfirmed |
| +32..+35 | float32 candidate weight A | Strong clue from range and paired sum |
| +36..+39 | float32 candidate weight B | Strong clue from range and paired sum |

Across the three previously inspected samples, the two values at +32 and +36 sum to approximately 1 for every record. This is consistent with a two-influence skinning record, but it does not prove that +24/+28 index a bone table. The values might instead be local palette indices, remapped joint IDs, or another pair of attributes.

## New diagnostic tool

Run the read-only audit on an extracted sample:

```bash
python tools/c3_phy4_skinning_audit.py path/to/sample.c3 --start 46 --count 3172
```

Use the matching start/count for the sample being checked:
- Monster sample: start 46, count 3172
- Mount sample: start 5316, count 1102
- Garment sample: start 2404, count 929

The tool reports:
- separate XYZ and UV ranges
- unknown uint32 at +20
- distinct candidate integer IDs at +24 and +28
- weight ranges and how many pairs sum to 1 within 1e-5
- candidate post-record uint16 block and remaining bytes
- tagged marker offsets for later correlation

## Added statistical diagnostics

The audit JSON now includes `field_diagnostics`: distinct candidate ID values and ordered pairs, records where both IDs match, finite weight-pair counts, weights individually within 0..1, and pairs summing to one within 1e-5. The `assessment` label is deliberately limited to `consistent_with_two_normalized_influences` when every finite pair passes both range and sum checks; otherwise it reports `inconclusive_candidate_fields`. This is not proof of bone indices or skinning semantics.

A focused unit test covers a normalized sample and an out-of-range pair whose sum is still one. Run it with:

```bash
python -m unittest tests.test_c3_skinning_audit -v
```

## Next validation gates

1. Compare candidate IDs against bone/joint names and counts in the corresponding skeleton/animation chunks.
2. Determine whether IDs are global skeleton indices or per-mesh palette indices.
3. Check whether weights are normalized for every supported model family, not only these three samples.
4. Verify UVs against actual DDS textures in a renderer.
5. Decode submesh/material partitions and the residual data before interpreting index buffers.
6. Validate triangle topology and winding in an independent renderer before any mesh export.

## Safety and non-claims

The tool reads bytes only. It does not run client executables or DLLs. It does not decode a skeleton, prove bone semantics, build a mesh, or export OBJ/glTF. The C3 format remains only partially understood.
