# Fixture: 09_string_formatting (Bytes vs String Formatting)

## Description
Py2 string formatting b'val: %d' % 12 works with bytes. Py3 bytes % requires strict bytes or text formatting.

## Exposing Input
`format_val(12)`

## Verified Runner Output
- **Py2 Original Output**: `Value is 12` (Exit: 0)
- **Correct Py3 Output**: `Value is 12` (Exit: 0)
- **Subtly Wrong Py3 Output**: `b'Value is 12'` (Exit: 0)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
