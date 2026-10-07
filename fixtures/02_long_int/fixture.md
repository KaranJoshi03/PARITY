# Fixture: 02_long_int (Long vs Int Unified Type)

## Description
Py2 code checked isinstance(x, (int, long)) which succeeds. In Py3 'long' is removed, raising NameError unless handled.

## Exposing Input
`check_large_int(2**65)`

## Verified Runner Output
- **Py2 Original Output**: `True` (Exit: 0)
- **Correct Py3 Output**: `True` (Exit: 0)
- **Subtly Wrong Py3 Output**: `ERROR: NameError` (Exit: 1)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
