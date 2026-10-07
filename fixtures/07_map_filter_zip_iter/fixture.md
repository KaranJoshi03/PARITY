# Fixture: 07_map_filter_zip_iter (Map Returning Iterator vs List)

## Description
Py2 map() returns a list (len(m) succeeds). Py3 map() returns an iterator (len(m) raises TypeError).

## Exposing Input
`process_list([1, 2, 3])`

## Verified Runner Output
- **Py2 Original Output**: `3` (Exit: 0)
- **Correct Py3 Output**: `3` (Exit: 0)
- **Subtly Wrong Py3 Output**: `ERROR: TypeError` (Exit: 1)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
