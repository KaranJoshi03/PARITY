# Fixture: 18_str_bytes_hashing (Bytes/Str Identity Check)

## Description
Py2 isinstance(b"hello", str) returns True (bytes IS str). Py3 returns False (bytes is NOT str).

## Exposing Input
`check_identity(b"hello")`

## Verified Runner Output
- **Py2 Original Output**: `True` (Exit: 0)
- **Correct Py3 Output**: `True` (Exit: 0)
- **Subtly Wrong Py3 Output**: `False` (Exit: 0)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
