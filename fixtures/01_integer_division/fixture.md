# Fixture: 01_integer_division (Integer vs True Division)

## Description
Py2 7/2 performs integer division returning 3. Py3 7/2 returns float 3.5. Subtly wrong Py3 code uses 7/2 instead of 7//2.

## Exposing Input
`calculate(7, 2)`

## Verified Runner Output
- **Py2 Original Output**: `3` (Exit: 0)
- **Correct Py3 Output**: `3` (Exit: 0)
- **Subtly Wrong Py3 Output**: `3.5` (Exit: 0)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
