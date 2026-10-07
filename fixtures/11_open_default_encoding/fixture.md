# Fixture: 11_open_default_encoding (Open Mode Text vs Binary)

## Description
Py2 open default mode reads raw byte str ('rb'). Py3 default open reads text ('r') with default encoding.

## Exposing Input
`read_mode()`

## Verified Runner Output
- **Py2 Original Output**: `rb` (Exit: 0)
- **Correct Py3 Output**: `rb` (Exit: 0)
- **Subtly Wrong Py3 Output**: `r` (Exit: 0)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
