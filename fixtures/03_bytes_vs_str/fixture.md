# Fixture: 03_bytes_vs_str (Bytes vs Str Indexing)

## Description
Py2 b"hello"[0] returns byte str "h". Py3 b"hello"[0] returns int 104.

## Exposing Input
`first_byte(b"hello")`

## Verified Runner Output
- **Py2 Original Output**: `h` (Exit: 0)
- **Correct Py3 Output**: `h` (Exit: 0)
- **Subtly Wrong Py3 Output**: `104` (Exit: 0)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
