# Fixtures Meta-Test Failure Report

## Summary
- **Total Fixtures Evaluated**: 20
- **Passing All Assertions**: 20
- **Failing Assertions**: 0

## Assertions Checked
1. **original_py2 runs under py2**: exit code 0, runs successfully.
2. **correct_py3 matches original on exposing input**: identical stdout and exit code.
3. **subtly_wrong_py3 differs on exposing input**: different stdout or exit code.

---

## Fixtures Failing Their Own Claim

None. All fixtures passed all three assertions.

---

## Full Verification Matrix (All 20 Fixtures)

| Fixture | Status | C1 (Py2 Runs) | C2 (Correct Matches) | C3 (Wrong Differs) | Real Py2 Output | Real Correct Py3 Output | Real Wrong Py3 Output |
| :--- | :---: | :---: | :---: | :---: | :--- | :--- | :--- |
| `01_integer_division` | **PASS** | True | True | True | `3` | `3` | `3.5` |
| `02_long_int` | **PASS** | True | True | True | `True` | `True` | `ERROR:NameError` |
| `03_bytes_vs_str` | **PASS** | True | True | True | `h` | `h` | `104` |
| `04_unicode_literals` | **PASS** | True | True | True | `True` | `True` | `ERROR:NameError` |
| `05_dict_set_order` | **PASS** | True | True | True | `a` | `a` | `z` |
| `06_mixed_type_sort` | **PASS** | True | True | True | `[1, 2, 'a']` | `[1, 2, 'a']` | `ERROR:TypeError` |
| `07_map_filter_zip_iter` | **PASS** | True | True | True | `3` | `3` | `ERROR:TypeError` |
| `08_range_vs_xrange` | **PASS** | True | True | True | `[0, 1, 2, 3, 4]` | `[0, 1, 2, 3, 4]` | `ERROR:NameError` |
| `09_string_formatting` | **PASS** | True | True | True | `Value is 12` | `Value is 12` | `b'Value is 12'` |
| `10_round_half_even` | **PASS** | True | True | True | `3.0` | `3.0` | `2.0` |
| `11_open_default_encoding` | **PASS** | True | True | True | `rb` | `rb` | `r` |
| `12_exception_message_text` | **PASS** | True | True | True | `True` | `True` | `False` |
| `13_sorted_cmp` | **PASS** | True | True | True | `[1, 2, 3]` | `[1, 2, 3]` | `ERROR:TypeError` |
| `14_dict_keys_view` | **PASS** | True | True | True | `a` | `a` | `ERROR:TypeError` |
| `15_print_formatting` | **PASS** | True | True | True | `hello 42` | `hello 42` | `ERROR:SyntaxError` |
| `16_reduce_import` | **PASS** | True | True | True | `10` | `10` | `ERROR:NameError` |
| `17_integer_overflow` | **PASS** | True | True | True | `True` | `True` | `ERROR:NameError` |
| `18_str_bytes_hashing` | **PASS** | True | True | True | `True` | `True` | `False` |
| `19_input_raw_input` | **PASS** | True | True | True | `raw_input_used` | `raw_input_used` | `ERROR:NameError` |
| `20_bytes_str_concat` | **PASS** | True | True | True | `hello world` | `hello world` | `TypeError` |
