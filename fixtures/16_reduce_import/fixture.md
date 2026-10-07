# Fixture: 16_reduce_import (Reduce Builtin vs Functools)

## Description
Py2 reduce() is a built-in function. Py3 moved reduce() to functools, so un-imported reduce() raises NameError.

## Exposing Input
`sum_all([1, 2, 3, 4])`

## Verified Runner Output
- **Py2 Original Output**: `10` (Exit: 0)
- **Correct Py3 Output**: `10` (Exit: 0)
- **Subtly Wrong Py3 Output**: `ERROR: NameError` (Exit: 1)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
