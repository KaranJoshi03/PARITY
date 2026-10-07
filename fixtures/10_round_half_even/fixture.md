# Fixture: 10_round_half_even (Round Half Away From Zero vs Half Even)

## Description
Py2 round(2.5) rounds to 3.0 (half away from zero). Py3 round(2.5) rounds to 2 (banker's round to even).

## Exposing Input
`round_val(2.5)`

## Verified Runner Output
- **Py2 Original Output**: `3.0` (Exit: 0)
- **Correct Py3 Output**: `3.0` (Exit: 0)
- **Subtly Wrong Py3 Output**: `2.0` (Exit: 0)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
