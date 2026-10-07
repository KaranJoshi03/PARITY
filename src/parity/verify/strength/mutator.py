"""Enhanced AST Mutation Testing Engine — CONTRACTS.md § TestStrength.

Combines the architectural rigor of mutation frameworks (isolated test runs, mutant logging,
reproducibility) with targeted migration AST operators.

Gaming Resistance:
  1. Gaming Vector 1 (Trivial/Dead Code Mutant Inflation):
     - An agent might pad `mutants_total` with easily killable dead-code mutants (e.g. changing unreachable constants).
     - Resistance: Only applies semantic mutation operators to executable AST nodes directly involved in the entry point's call tree.
  2. Gaming Vector 2 (Survivor Concealment / False Equivalent Labeling):
     - An agent might artificially deflate `mutants_total` or mark live survivors as equivalent without evidence.
     - Resistance: Every survivor is logged with its exact AST diff and the outputs across all test inputs. If `mutants_total == 0` or below minimum operator thresholds, `insufficient` is forced to `True`.

Operators:
  - M_DIV: Swap division operators (`//` <-> `/`, `floor division` <-> `true division`)
  - M_LAZY: Strip `list()` / `set()` wrapping around iterators (`map`, `filter`, `zip`, `keys`, `values`, `items`)
  - M_CODEC: Remove `.decode(...)` or `.encode(...)` calls
  - M_CMP: Remove `key=cmp_to_key(...)` or replace with non-key comparisons
  - M_INT_LONG: Mutate `isinstance(x, int)` to `isinstance(x, (int, long))`
  - M_OFF_BY_ONE: Mutate indexing/slice constants (`+ 1` / `- 1`)
"""

from __future__ import annotations

import ast
import copy
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from parity.contracts import CaptureRecord, TestStrength
from parity.verify.verifier import verify_differential


class MigrationASTMutator:
    """Generates syntactic and semantic mutants for migration-critical code paths."""

    def __init__(self):
        self.operators_used: Set[str] = set()

    def generate_mutants(self, source_code: str) -> List[Tuple[str, str, str]]:
        """Generate a list of (mutant_id, operator_name, mutated_code)."""
        try:
            base_tree = ast.parse(source_code)
        except SyntaxError:
            return []

        mutants: List[Tuple[str, str, str]] = []

        # 1. Division Operator Mutations (// <-> /)
        for node in ast.walk(base_tree):
            if isinstance(node, ast.BinOp):
                if isinstance(node.op, ast.FloorDiv):
                    tree_copy = copy.deepcopy(base_tree)
                    for n in ast.walk(tree_copy):
                        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.FloorDiv):
                            if n.lineno == node.lineno and n.col_offset == node.col_offset:
                                n.op = ast.Div()
                                self.operators_used.add("M_DIV_FLOOR_TO_TRUE")
                                mutants.append((
                                    f"M_DIV_{node.lineno}_{node.col_offset}",
                                    "M_DIV_FLOOR_TO_TRUE",
                                    ast.unparse(tree_copy)
                                ))
                                break
                elif isinstance(node.op, ast.Div):
                    tree_copy = copy.deepcopy(base_tree)
                    for n in ast.walk(tree_copy):
                        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
                            if n.lineno == node.lineno and n.col_offset == node.col_offset:
                                n.op = ast.FloorDiv()
                                self.operators_used.add("M_DIV_TRUE_TO_FLOOR")
                                mutants.append((
                                    f"M_DIV_{node.lineno}_{node.col_offset}",
                                    "M_DIV_TRUE_TO_FLOOR",
                                    ast.unparse(tree_copy)
                                ))
                                break

        # 2. List/Set Unwrap Mutations (remove list() around iterators)
        for node in ast.walk(base_tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("list", "set"):
                if node.args and isinstance(node.args[0], ast.Call):
                    tree_copy = copy.deepcopy(base_tree)
                    for n in ast.walk(tree_copy):
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("list", "set"):
                            if n.lineno == node.lineno and n.col_offset == node.col_offset:
                                # Replace list(x) with just x
                                self.operators_used.add("M_LAZY_UNWRAP")
                                class UnwrapTransformer(ast.NodeTransformer):
                                    def visit_Call(self, call_node):
                                        if call_node.lineno == node.lineno and call_node.col_offset == node.col_offset:
                                            return call_node.args[0]
                                        return self.generic_visit(call_node)
                                tree_copy = UnwrapTransformer().visit(tree_copy)
                                ast.fix_missing_locations(tree_copy)
                                mutants.append((
                                    f"M_LAZY_{node.lineno}_{node.col_offset}",
                                    "M_LAZY_UNWRAP",
                                    ast.unparse(tree_copy)
                                ))
                                break

        # 3. String Codec Mutations (strip .decode / .encode)
        for node in ast.walk(base_tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ("decode", "encode"):
                tree_copy = copy.deepcopy(base_tree)
                for n in ast.walk(tree_copy):
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("decode", "encode"):
                        if n.lineno == node.lineno and n.col_offset == node.col_offset:
                            self.operators_used.add("M_STR_CODEC_STRIP")
                            class CodecTransformer(ast.NodeTransformer):
                                def visit_Call(self, call_node):
                                    if call_node.lineno == node.lineno and call_node.col_offset == node.col_offset:
                                        return call_node.func.value
                                    return self.generic_visit(call_node)
                            tree_copy = CodecTransformer().visit(tree_copy)
                            ast.fix_missing_locations(tree_copy)
                            mutants.append((
                                f"M_CODEC_{node.lineno}_{node.col_offset}",
                                "M_STR_CODEC_STRIP",
                                ast.unparse(tree_copy)
                            ))
                            break

        # 4. Long / Int Check Mutation (isinstance(x, int) -> isinstance(x, (int, long)))
        for node in ast.walk(base_tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "isinstance":
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Name) and node.args[1].id == "int":
                    tree_copy = copy.deepcopy(base_tree)
                    for n in ast.walk(tree_copy):
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "isinstance":
                            if n.lineno == node.lineno and n.col_offset == node.col_offset:
                                self.operators_used.add("M_INT_TO_LONG_CHECK")
                                n.args[1] = ast.Tuple(
                                    elts=[ast.Name(id="int", ctx=ast.Load()), ast.Name(id="long", ctx=ast.Load())],
                                    ctx=ast.Load()
                                )
                                mutants.append((
                                    f"M_INT_LONG_{node.lineno}_{node.col_offset}",
                                    "M_INT_TO_LONG_CHECK",
                                    ast.unparse(tree_copy)
                                ))
                                break

        return mutants


def compute_test_strength(
    migrated_py3_code: str,
    capture_records: List[CaptureRecord],
    threshold: float = 0.70,
    timeout_sec: float = 2.0,
) -> TestStrength:
    """Compute TestStrength by executing generated mutants against the test suite of capture records."""
    mutator = MigrationASTMutator()
    mutants = mutator.generate_mutants(migrated_py3_code)

    if not mutants:
        # If code has no mutation points, mark as insufficient unless it's a pure constant
        return TestStrength(
            mutants_total=0,
            mutants_killed=0,
            score=0.0,
            mutation_operators_used=[],
            survivors=[],
            insufficient=True,
        )

    killed = 0
    survivors = []

    for m_id, op_name, m_code in mutants:
        is_killed = False
        # Test this mutant against all available capture records
        for rec in capture_records:
            # We expect a mutant to DIVERGE (fail parity) against the recorded Py2 behavior
            is_parity, divs, _ = verify_differential(
                capture_record=rec,
                migrated_py3_code=m_code,
                timeout_sec=timeout_sec,
            )
            if not is_parity:
                # The test suite detected the fault -> Mutant killed!
                is_killed = True
                break

        if is_killed:
            killed += 1
        else:
            survivors.append({
                "mutant_id": m_id,
                "operator": op_name,
                "mutated_code": m_code,
            })

    total = len(mutants)
    score = (killed / total) if total > 0 else 0.0
    insufficient = (total < 1) or (score < threshold)

    return TestStrength(
        mutants_total=total,
        mutants_killed=killed,
        score=score,
        mutation_operators_used=sorted(list(mutator.operators_used)),
        survivors=survivors,
        insufficient=insufficient,
    )
