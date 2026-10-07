# Fixture: 17_integer_overflow (Integer Overflow Auto-Long Promotion)

## Description
Py2 promotes large integers to long and checks isinstance(x, (int, long)). Py3 references to 'long' raise NameError.

## Exposing Input
`check_overflow(2**62)`

## Verified Runner Output
- **Py2 Original Output**: `True` (Exit: 0)
- **Correct Py3 Output**: `True` (Exit: 0)
- **Subtly Wrong Py3 Output**: `ERROR: NameError` (Exit: 1)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
