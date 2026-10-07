# Fixture: 15_print_formatting (Print Statement vs Print Function)

## Description
Py2 uses print statement 'print a, b'. Py3 requires print() function; print statement is a SyntaxError.

## Exposing Input
`print_data("hello", 42)`

## Verified Runner Output
- **Py2 Original Output**: `hello 42` (Exit: 0)
- **Correct Py3 Output**: `hello 42` (Exit: 0)
- **Subtly Wrong Py3 Output**: `ERROR: SyntaxError` (Exit: 1)

## Behavioral Divergence Reproduced
- **Reproduced**: yes
