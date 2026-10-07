# Fixture: 12_exception_message_text (Exception .message Attribute)

## Description
Py2 exceptions had a .message attribute containing the error text. Py3 removed .message; accessing it returns empty string or raises AttributeError.

## Exposing Input
`get_exc_msg()`

## Verified Runner Output
- **Py2 Original Output**: `True` (Exit: 0)
- **Correct Py3 Output**: `True` (Exit: 0)
- **Subtly Wrong Py3 Output**: `False` (Exit: 0)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
