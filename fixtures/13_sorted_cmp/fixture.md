# Fixture: 13_sorted_cmp (Sorted with Cmp Parameter)

## Description
Py2 sorted() accepts cmp argument. Py3 removed cmp parameter, raising TypeError.

## Exposing Input
`sort_with_cmp([3, 1, 2])`

## Verified Runner Output
- **Py2 Original Output**: `[1, 2, 3]` (Exit: 0)
- **Correct Py3 Output**: `[1, 2, 3]` (Exit: 0)
- **Subtly Wrong Py3 Output**: `ERROR: TypeError` (Exit: 1)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
