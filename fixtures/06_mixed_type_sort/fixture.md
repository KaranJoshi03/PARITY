# Fixture: 06_mixed_type_sort (Mixed-Type Sorting)

## Description
Py2 permits sorting lists containing mixed types ([1, 'a']). Py3 raises TypeError.

## Exposing Input
`sort_mixed([1, "a", 2])`

## Verified Runner Output
- **Py2 Original Output**: `[1, 2, 'a']` (Exit: 0)
- **Correct Py3 Output**: `[1, 2, 'a']` (Exit: 0)
- **Subtly Wrong Py3 Output**: `ERROR: TypeError` (Exit: 1)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
