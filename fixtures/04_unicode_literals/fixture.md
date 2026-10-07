# Fixture: 04_unicode_literals (Unicode vs Str Type Check)

## Description
Py2 code checks isinstance(s, (str, unicode)). In Py3 'unicode' is not defined, raising NameError in unmigrated code.

## Exposing Input
`check_is_text("hello")`

## Verified Runner Output
- **Py2 Original Output**: `True` (Exit: 0)
- **Correct Py3 Output**: `True` (Exit: 0)
- **Subtly Wrong Py3 Output**: `ERROR: NameError` (Exit: 1)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
