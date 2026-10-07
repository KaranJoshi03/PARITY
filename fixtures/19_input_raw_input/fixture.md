# Fixture: 19_input_raw_input (Raw Input vs Input Function)

## Description
Py2 raw_input() reads string. Py3 removed raw_input(), raising NameError.

## Exposing Input
`get_input()`

## Verified Runner Output
- **Py2 Original Output**: `raw_input_used` (Exit: 0)
- **Correct Py3 Output**: `raw_input_used` (Exit: 0)
- **Subtly Wrong Py3 Output**: `ERROR: NameError` (Exit: 1)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
