# C3 PHY4 research notes (experimental)

## Scope and safety

These notes describe read-only inspection of selected C3 assets from the
provided Conquer Online client archive. They are not a complete C3 format
specification. No game executable, DLL, script, or suspicious asset is run.

## Verified observations in the sampled client

The sampled files begin with the 16-byte signature `MAXFILE C3 00001`.
The three examples below are the `v_body` PHY4 sections, not necessarily
the first PHY4 section in each file. The section header is followed by three
32-bit values; the second value behaves as a candidate vertex count. A
40-byte record stride fits exactly within the declared section boundary.

| Sample | PHY4 tag offset | Candidate record count | Candidate record start | XYZ finite | Candidate UV finite |
|---|---:|---:|---:|---|---|
| monster/100/1.c3 | 16 (root) | 3172 | 46 | yes | yes |
| Mount/809/8090000.C3 | 5286 (nested) | 1102 | 5316 | yes | yes |
| mesh/x/garment/001183485.C3 | 2374 (nested) | 929 | 2404 | yes | yes |

Across these three samples, the first 12 bytes of each candidate record
decode as three finite little-endian float values (XYZ). The next 8 bytes
also decode as finite values in ranges consistent with texture coordinates.
This is strong evidence for a common candidate record layout, but the
remaining 20 bytes have not been semantically identified.

A broader scan of all PHY4 sections found the same 40-byte candidate fit
in 17 sections of the monster sample, 9 sections of the horse sample, and
4 sections of the garment sample. This includes body and attachment parts
such as `v_head`, `v_l_arm`, `v_mount`, `v_l_weapon`, and `v_body`.
This is broader structural consistency, not proof that every field has
the same meaning in every section.

## Candidate index data

Several small attachment sections contain a plausible 32-bit count,
a zero 32-bit value, and 16-bit values that all fall below the candidate
vertex count. Many of those counts are divisible by 3. For the monster
body, the candidate count is 4488 (divisible by 3); for the garment body,
it is 1265 (not divisible by 3). The horse body continuation does not
match the same simple heuristic. These observations are not enough to
declare a confirmed triangle index list or topology; strips, submeshes,
and additional data blocks may be involved.

The probe now labels a recognized index-count block as `triangle_list_candidate` only when all values are in range and the count is divisible by three. This remains a count-based hint, not a topology decode: it does not establish winding, submesh boundaries, strip/fan use, or whether the values are consumed as one triangle list.

No OBJ/mesh export is enabled by this probe. Doing so before the index
topology, record fields, submesh layout, and transforms are confirmed could
produce convincing but incorrect geometry.

## Version compatibility warning

A public C3 WebGL viewer describes a different PHY parser and a 76-byte
vertex record for its bundled client-5065 assets. That is useful as a
reference, but it must not be copied blindly into this sampled client:
our observed `PHY4` sections and candidate 40-byte records do not match
that published layout. See:
https://github.com/javinladish/C3-WebGL-Loader

## Next validation tasks

1. Decode the remaining fields in the 40-byte record using byte-level
   comparisons across body, mount, and garment samples.
2. Locate all index/submesh blocks, including the horse body continuation.
3. Confirm triangle-list versus strip/fan topology and winding.
4. Validate exported geometry in an independent 3D viewer before enabling
   editing or saving.
5. Decode skeleton/attachment and MOTI animation chunks separately.

The accompanying `tools/c3_phy4_candidate_probe.py` scans root and nested
PHY4 sections and reports these candidate measurements without asserting
a full decode. The extraction workflow also runs it and uploads a separate
experimental report artifact.
