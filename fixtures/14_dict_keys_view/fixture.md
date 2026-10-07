# Fixture: 14_dict_keys_view (Dict Keys Indexing / View)

## Description
Py2 d.keys() returns a list (indexing keys[0] works). Py3 d.keys() returns dict_keys view (indexing raises TypeError).

## Exposing Input
`pop_key({"a": 1, "b": 2})`

## Verified Runner Output
- **Py2 Original Output**: `a` (Exit: 0)
- **Correct Py3 Output**: `a` (Exit: 0)
- **Subtly Wrong Py3 Output**: `ERROR: TypeError` (Exit: 1)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
