# PHY4 residual-byte analysis

Date: 2026-11-26

This note records a follow-up byte inspection of the three candidate record streams. It is deliberately conservative: bytes after the candidate vertex records are not yet a complete index/submesh decode.

## Exact candidate boundaries

| Sample | File size | Candidate record start | Count | Stride | End |
|---|---:|---:|---:|---:|---:|
| Monster 1.c3 | 168431 | 46 | 3172 | 40 | 126926 |
| Mount 8090000.C3 | 65808 | 5316 | 1102 | 40 | 49396 |
| Garment 001183485.C3 | 52866 | 2404 | 929 | 40 | 39564 |

## Post-record sequences

### Monster
At byte 126926, the next eight bytes decode as little-endian uint32 values (4488, 0). The following 4488 uint16 values are all less than 3172; observed maximum is 1015 and 1016 distinct values occur. The sequence ends at byte 135910, leaving 32521 bytes before EOF.

### Garment
At byte 39564, the next eight bytes decode as (1265, 0). The following 1265 uint16 values are all less than 929; observed maximum is 335 and 336 distinct values occur. This sequence ends at byte 42102, leaving 10764 bytes before EOF. Since 1265 is not divisible by three, it must not be treated as one complete triangle-list index buffer without further framing evidence.

The bytes immediately after that first sequence continue as dense binary data. They are not safely classifiable as a second index buffer from the available evidence.

### Mount
The bytes immediately after the 1102 candidate records do not begin with the same (count, zero, uint16 indices) pattern. They instead begin with values that look like another packed record stream. The mount residual therefore requires a separate layout hypothesis.

## Structural markers observed in the samples
- Monster: root PHY4 at offset 16; a 2SID/PHY4 marker at 153982; 16 further PHY4 markers at 153986..162520; MOTI markers at 163087 and then every 96 bytes through 168335.
- Mount: repeated 2SID/PHY4 markers around offsets 867, 1603, 2339, 3075, 3811, 4547, 5282, and 60076; PHY4 markers immediately after those prefixes; MOTI markers begin around 60784.
- Garment: repeated 2SID/PHY4 markers around offsets 1292, 1831, and 2370; MOTI markers begin around 47362.

The small tagged blocks and their length fields still need their own validated framing parser. Marker positions alone do not establish the meaning of the blocks.

## Next technical gate
1. Determine whether the first uint16 sequence is one submesh, one strip, or one part of a multi-buffer structure.
2. Identify how the remaining residual bytes are partitioned, especially in the garment and mount examples.
3. Correlate submesh/material identifiers with the small tagged PHY4 blocks and texture references.
4. Confirm topology and winding by rendering a known sample only after a decoder has a defensible mesh interpretation.

No OBJ/glTF export or production viewer should be enabled based on this evidence alone.
