# Fixture: 08_range_vs_xrange (Range vs Xrange Iteration)

## Description
Py2 used xrange() for lazy iteration. Py3 removed xrange() in favor of range(), so unmigrated code raises NameError.

## Exposing Input
`get_numbers(5)`

## Verified Runner Output
- **Py2 Original Output**: `[0, 1, 2, 3, 4]` (Exit: 0)
- **Correct Py3 Output**: `[0, 1, 2, 3, 4]` (Exit: 0)
- **Subtly Wrong Py3 Output**: `ERROR: NameError` (Exit: 1)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
