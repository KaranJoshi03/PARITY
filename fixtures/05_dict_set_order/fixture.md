# Fixture: 05_dict_set_order (Dict Iteration Ordering)

## Description
Py2 dict keys iteration order depends on hash table layout. Py3 maintains insertion order.

## Exposing Input
`get_first_key({"z": 1, "a": 2})`

## Verified Runner Output
- **Py2 Original Output**: `a` (Exit: 0)
- **Correct Py3 Output**: `a` (Exit: 0)
- **Subtly Wrong Py3 Output**: `z` (Exit: 0)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
