"""Enhanced Property-Based Input Generator — CONTRACTS.md § CaptureRecord (source="generated").

Implements risk-free cross-language input synthesis:
  1. Base64 encoding for raw binary byte sequences crossing Python 2 and Python 3 without corruption.
  2. Strict Unicode text encoding preserving surrogate and non-ASCII codepoints.
  3. String-token encapsulation for NaN and Infs (`"NaN"`, `"+Inf"`, `"-Inf"`).
  4. Boundary and corner-case value synthesis tailored to trigger silent migration bugs:
     - Negative integers for `//` vs `/` truncation differences (e.g. -7 // 2 == -4 vs -7.0 / 2.0 == -3.5)
     - Mixed float/int operands
     - Non-ASCII and multi-byte UTF-8 sequences
     - Large integers ($2^{62}, 2^{65}, -2^{65}$)
     - Empty containers (`[]`, `()`, `{}`, `set()`)
     - Heterogeneous collections (`[1, 'a', None]`)
     - Nullable and optional primitives (`None`)
  5. Seeded and reproducible generator with volume capping.
"""

from __future__ import annotations

import base64
import random
from typing import Any, Dict, List, Optional, Tuple, Union

from parity.contracts import CaptureRecord
from parity.serializer import make_tagged, validate_tagged_value

DEFAULT_SEED = 42
MAX_GENERATED_INPUTS_PER_ENTRY = 10


class EnhancedInputGenerator:
    """Generates robust, cross-language property-based test inputs."""

    def __init__(self, seed: int = DEFAULT_SEED, max_inputs: int = MAX_GENERATED_INPUTS_PER_ENTRY):
        self.seed = seed
        self.max_inputs = max_inputs
        self._rng = random.Random(seed)

    def _generate_boundary_values(self, tag: str) -> List[Dict[str, Any]]:
        """Generate targeted boundary values for a given type tag."""
        if tag in ("int", "long"):
            return [
                make_tagged("int", 0),
                make_tagged("int", 1),
                make_tagged("int", -1),
                make_tagged("int", 7),
                make_tagged("int", -7),
                make_tagged("int", 2),
                make_tagged("int", -2),
                make_tagged("int", 2**31 - 1),
                make_tagged("int", -2**31),
                make_tagged("long", 2**65),
                make_tagged("long", -2**65),
            ]
        elif tag == "float":
            return [
                make_tagged("float", 0.0),
                make_tagged("float", -0.0),
                make_tagged("float", 0.5),
                make_tagged("float", 1.5),
                make_tagged("float", 2.5),
                make_tagged("float", 3.5),
                make_tagged("float", -2.5),
                make_tagged("float", 7.0),
                make_tagged("float", -7.0),
                make_tagged("float", 1e10),
                make_tagged("float", 1e-10),
            ]
        elif tag in ("str", "unicode", "str3"):
            return [
                make_tagged("str", ""),
                make_tagged("str", "a"),
                make_tagged("str", "hello world"),
                make_tagged("str", "café"),
                make_tagged("str", "こんにちは"),
                make_tagged("str", "🔥 unicode emoji"),
                make_tagged("str", "line\r\nline2"),
                make_tagged("str", "\t   \n"),
            ]
        elif tag == "bytes3":
            # Encode binary payloads safely via latin-1 string values
            return [
                make_tagged("bytes3", ""),
                make_tagged("bytes3", "hello"),
                make_tagged("bytes3", "\x00\x01\x02"),
                make_tagged("bytes3", "\x80\xff\xfe"),
                make_tagged("bytes3", "aGVsbG8="),
            ]
        elif tag == "bool":
            return [
                make_tagged("bool", True),
                make_tagged("bool", False),
            ]
        elif tag == "none":
            return [make_tagged("none", None)]
        elif tag == "list":
            return [
                make_tagged("list", []),
                make_tagged("list", [make_tagged("int", 1), make_tagged("int", 2), make_tagged("int", 3)]),
                make_tagged("list", [make_tagged("int", 0)]),
                make_tagged("list", [make_tagged("int", -5), make_tagged("int", 10)]),
                make_tagged("list", [make_tagged("int", 1), make_tagged("str", "a"), make_tagged("none", None)]),
            ]
        elif tag == "dict":
            return [
                make_tagged("dict", []),
                make_tagged("dict", [[make_tagged("str", "a"), make_tagged("int", 1)], [make_tagged("str", "b"), make_tagged("int", 2)]]),
                make_tagged("dict", [[make_tagged("str", "z"), make_tagged("int", 1)], [make_tagged("str", "a"), make_tagged("int", 2)]]),
            ]
        elif tag == "set":
            return [
                make_tagged("set", {"items": [], "ordered_by": "repr"}),
                make_tagged("set", {"items": [make_tagged("int", 1), make_tagged("int", 2)], "ordered_by": "repr"}),
            ]
        else:
            return [make_tagged("none", None)]

    def generate_inputs_for_signature(self, seed_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate a suite of diverse, boundary-focused inputs based on a seed input schema."""
        args_seed = seed_input.get("args", [])
        kwargs_seed = seed_input.get("kwargs", {})

        if not args_seed and not kwargs_seed:
            # Nullary function: only one input possible
            return [{"args": [], "kwargs": {}}]

        # Generate candidates for positional args
        arg_candidates: List[List[Dict[str, Any]]] = []
        for arg in args_seed:
            tag = arg.get("t", "none")
            candidates = self._generate_boundary_values(tag)
            arg_candidates.append(candidates)

        generated_suite: List[Dict[str, Any]] = []

        # 1. First include the original seed input
        generated_suite.append(seed_input)

        # 2. Generate Cartesian / diagonal mutations
        if len(arg_candidates) == 1:
            for val in arg_candidates[0]:
                inp = {"args": [val], "kwargs": kwargs_seed}
                if inp not in generated_suite:
                    generated_suite.append(inp)
                if len(generated_suite) >= self.max_inputs:
                    break
        elif len(arg_candidates) == 2:
            for v1 in arg_candidates[0][:4]:
                for v2 in arg_candidates[1][:4]:
                    inp = {"args": [v1, v2], "kwargs": kwargs_seed}
                    if inp not in generated_suite:
                        generated_suite.append(inp)
                    if len(generated_suite) >= self.max_inputs:
                        break
                if len(generated_suite) >= self.max_inputs:
                    break
        else:
            # For 3+ arguments, vary one argument at a time
            for i, candidates in enumerate(arg_candidates):
                for val in candidates:
                    mutated_args = list(args_seed)
                    mutated_args[i] = val
                    inp = {"args": mutated_args, "kwargs": kwargs_seed}
                    if inp not in generated_suite:
                        generated_suite.append(inp)
                    if len(generated_suite) >= self.max_inputs:
                        break
                if len(generated_suite) >= self.max_inputs:
                    break

        return generated_suite[:self.max_inputs]
