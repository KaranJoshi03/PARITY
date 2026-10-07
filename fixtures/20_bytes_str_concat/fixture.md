# Fixture: 20_bytes_str_concat (Bytes + Str Concatenation)

## Description
Py2: b'hello' + ' world' works (both are str). Py3: TypeError because bytes + str is not allowed.

## Exposing Input
`concat_test(b"hello", " world")`

## Verified Runner Output
- **Py2 Original Output**: `hello world` (Exit: 0)
- **Correct Py3 Output**: `hello world` (Exit: 0)
- **Subtly Wrong Py3 Output**: `TypeError` (Exit: 0)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
