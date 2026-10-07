"""Migration backends module for PARITY — CONTRACTS.md § MigrationResult.

Implements three distinct migration backends:
  1. 2to3 baseline (`TwoToThreeBackend`)
  2. Local model via Ollama HTTP API (`OllamaBackend`)
  3. Generic OpenAI-compatible HTTP client (`OpenAICompatibleBackend`)

Features:
  - Logs every MigrationResult to disk (`eval/results/migrations/<timestamp>_<module>_<backend>.json`).
  - Defensive code parsing from LLM output (detects markdown fences or bare code, verifies AST parseability).
  - Explicit parse_ok=False with failure reason on invalid code; never guesses.
  - Strict prompt instructions to preserve behavior without refactoring.
  - Fixed temperature (0.0) and seed where supported.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from parity.contracts import MigrationResult

MIGRATION_RESULTS_DIR = Path("d:/KARAN/parity/eval/results/migrations")
MIGRATION_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
PROMPTS_DIR = Path("d:/KARAN/parity/src/parity/migrate/prompts")


def _load_prompt_template(version: str = "v1") -> str:
    """Load a versioned prompt template file."""
    p = PROMPTS_DIR / f"{version}.prompt"
    if not p.exists():
        # Fallback to default
        return (
            "Translate the following Python 2 code to Python 3.\n"
            "Preserve behavior exactly without refactoring.\n"
            "Python 2 Code:\n```python\n{source_code}\n```\n"
        )
    return p.read_text(encoding="utf-8")


def parse_migrated_code(raw_llm_output: str) -> Tuple[Optional[str], bool, Optional[str]]:
    """Defensively extract Python code from model output.
    
    Returns (parsed_code, parse_ok, parse_error).
    Never guesses; validates syntax via ast.parse.
    """
    if not raw_llm_output or not raw_llm_output.strip():
        return None, False, "Model output was empty or whitespace only"

    text = raw_llm_output.strip()

    # Try extracting from markdown code block ```python ... ```
    m = re.search(r'```(?:python|py)?\s*\n(.*?)```', text, re.DOTALL | re.IGNORECASE)
    if m:
        extracted = m.group(1).strip()
    else:
        # Check if text is wrapped in triple backticks without newline
        m2 = re.search(r'```(.*?)```', text, re.DOTALL)
        if m2:
            extracted = m2.group(1).strip()
        else:
            # If no code block, treat entire text as potential code
            extracted = text

    # Validate syntax defensively via AST
    try:
        ast.parse(extracted)
        return extracted, True, None
    except SyntaxError as e:
        return extracted, False, f"SyntaxError during AST parse on line {e.lineno}: {e.msg}"
    except Exception as e:
        return extracted, False, f"Unexpected error parsing code: {str(e)}"


def _save_migration_result(result: MigrationResult, module_name: str, backend_name: str) -> Path:
    """Log MigrationResult object to disk in eval/results/migrations/."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    out_file = MIGRATION_RESULTS_DIR / f"{ts}_{module_name}_{backend_name}.json"
    out_file.write_text(result.to_json(indent=2), encoding="utf-8")
    return out_file


# ---------------------------------------------------------------------------
# Backend 1: 2to3 Baseline
# ---------------------------------------------------------------------------

class TwoToThreeBackend:
    """Deterministic AST-based migration baseline using standard library lib2to3 / 2to3 tool."""

    def __init__(self, fixes: Optional[list[str]] = None):
        self.name = "2to3"
        self.model_name = "lib2to3"
        self.fixes = fixes

    def migrate(self, source_code: str, module_name: str = "module") -> MigrationResult:
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()
        parameters = {"fixes": self.fixes or "all", "deterministic": True}
        prompt = "lib2to3 AST fixers"

        # Try using lib2to3 in Python
        raw_output = ""
        parsed_code = None
        parse_ok = False
        parse_error = None

        try:
            # Python 3.11+ can run 2to3 as a tool or via lib2to3 refactor
            try:
                from lib2to3.refactor import RefactoringTool, get_fixers_from_package
                fixers = get_fixers_from_package('lib2to3.fixes')
                tool = RefactoringTool(fixers)
                tree = tool.refactor_string(source_code + "\n", name=module_name)
                transformed = str(tree)
                raw_output = transformed
                parsed_code = transformed
                parse_ok = True
            except ImportError:
                # If lib2to3 not directly importable, run 2to3 CLI or manual fallback
                import tempfile
                with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tf:
                    tf.write(source_code)
                    tf_name = tf.name
                
                try:
                    res = subprocess.run(
                        [sys.executable, "-m", "lib2to3", "-w", "-n", "--no-diffs", tf_name],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    with open(tf_name, "r", encoding="utf-8") as rf:
                        transformed = rf.read()
                    raw_output = transformed
                    parsed_code = transformed
                    parse_ok = True
                finally:
                    if os.path.exists(tf_name):
                        os.remove(tf_name)
        except Exception as e:
            raw_output = f"Error running 2to3: {str(e)}"
            parse_ok = False
            parse_error = str(e)

        if parse_ok and parsed_code:
            # Verify AST
            try:
                ast.parse(parsed_code)
            except SyntaxError as e:
                parse_ok = False
                parse_error = f"SyntaxError in 2to3 output: {str(e)}"

        duration_ms = (time.time() - start_time) * 1000.0

        res_obj = MigrationResult(
            module=module_name,
            backend=self.name,
            model_name=self.model_name,
            parameters=parameters,
            prompt=prompt,
            raw_output=raw_output,
            parsed_code=parsed_code or "",
            parse_ok=parse_ok,
            parse_error=parse_error,
            timestamp=timestamp,
            duration_ms=duration_ms,
        )
        _save_migration_result(res_obj, module_name, self.name)
        return res_obj


# ---------------------------------------------------------------------------
# Backend 2: Ollama Local Model
# ---------------------------------------------------------------------------

class OllamaBackend:
    """Local LLM backend calling Ollama API (http://localhost:11434/api/generate)."""

    def __init__(
        self,
        model_name: str = "codellama",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.0,
        seed: int = 42,
        prompt_version: str = "v1",
    ):
        self.name = "ollama"
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.seed = seed
        self.prompt_version = prompt_version

    def is_available(self) -> bool:
        """Check if Ollama server is responding."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def migrate(self, source_code: str, module_name: str = "module") -> MigrationResult:
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()
        template = _load_prompt_template(self.prompt_version)
        prompt = template.format(source_code=source_code)

        parameters = {
            "temperature": self.temperature,
            "seed": self.seed,
            "prompt_version": self.prompt_version,
            "base_url": self.base_url,
        }

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "seed": self.seed,
            }
        }

        raw_output = ""
        parsed_code = None
        parse_ok = False
        parse_error = None

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30.0) as response:
                resp_json = json.loads(response.read().decode("utf-8"))
                raw_output = resp_json.get("response", "")
            
            parsed_code, parse_ok, parse_error = parse_migrated_code(raw_output)
        except urllib.error.URLError as e:
            raw_output = f"URLError connecting to Ollama at {self.base_url}: {str(e)}"
            parse_ok = False
            parse_error = f"Ollama connection failure: {str(e)}"
        except Exception as e:
            raw_output = f"Ollama execution error: {str(e)}"
            parse_ok = False
            parse_error = f"Execution error: {str(e)}"

        duration_ms = (time.time() - start_time) * 1000.0

        res_obj = MigrationResult(
            module=module_name,
            backend=self.name,
            model_name=self.model_name,
            parameters=parameters,
            prompt=prompt,
            raw_output=raw_output,
            parsed_code=parsed_code or "",
            parse_ok=parse_ok,
            parse_error=parse_error,
            timestamp=timestamp,
            duration_ms=duration_ms,
        )
        _save_migration_result(res_obj, module_name, self.name)
        return res_obj


# ---------------------------------------------------------------------------
# Backend 3: Generic OpenAI-Compatible HTTP Client
# ---------------------------------------------------------------------------

class OpenAICompatibleBackend:
    """Generic OpenAI-compatible chat completion client (supports OpenAI, Groq, DeepSeek, LocalAI, vLLM)."""

    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        base_url: Optional[str] = None,
        api_key_env: str = "OPENAI_API_KEY",
        temperature: float = 0.0,
        seed: Optional[int] = 42,
        prompt_version: str = "v1",
    ):
        self.name = "openai_compatible"
        self.model_name = model_name
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key_env = api_key_env
        self.temperature = temperature
        self.seed = seed
        self.prompt_version = prompt_version

    def is_available(self) -> bool:
        """Check if API key is present in environment."""
        key = os.environ.get(self.api_key_env)
        return bool(key and key.strip())

    def migrate(self, source_code: str, module_name: str = "module") -> MigrationResult:
        start_time = time.time()
        timestamp = datetime.now(timezone.utc).isoformat()
        template = _load_prompt_template(self.prompt_version)
        user_prompt = template.format(source_code=source_code)

        parameters = {
            "temperature": self.temperature,
            "seed": self.seed,
            "prompt_version": self.prompt_version,
            "base_url": self.base_url,
            "api_key_env": self.api_key_env,
        }

        api_key = os.environ.get(self.api_key_env, "")
        raw_output = ""
        parsed_code = None
        parse_ok = False
        parse_error = None

        if not api_key:
            raw_output = f"API key environment variable '{self.api_key_env}' is not set."
            parse_ok = False
            parse_error = f"Missing API key environment variable {self.api_key_env}"
        else:
            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a strict Python migration compiler. "
                            "Output ONLY valid Python 3 code in a markdown block. "
                            "Do NOT improve or refactor code."
                        ),
                    },
                    {"role": "role", "content": user_prompt},
                ],
                "temperature": self.temperature,
            }
            if self.seed is not None:
                payload["seed"] = self.seed

            try:
                req_data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.base_url}/chat/completions",
                    data=req_data,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=30.0) as response:
                    resp_json = json.loads(response.read().decode("utf-8"))
                    choices = resp_json.get("choices", [])
                    if choices:
                        raw_output = choices[0].get("message", {}).get("content", "")
                    else:
                        raw_output = json.dumps(resp_json)
                
                parsed_code, parse_ok, parse_error = parse_migrated_code(raw_output)
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                raw_output = f"HTTPError {e.code}: {err_body}"
                parse_ok = False
                parse_error = f"HTTP {e.code} API error: {err_body[:200]}"
            except Exception as e:
                raw_output = f"Request error: {str(e)}"
                parse_ok = False
                parse_error = str(e)

        duration_ms = (time.time() - start_time) * 1000.0

        res_obj = MigrationResult(
            module=module_name,
            backend=self.name,
            model_name=self.model_name,
            parameters=parameters,
            prompt=user_prompt,
            raw_output=raw_output,
            parsed_code=parsed_code or "",
            parse_ok=parse_ok,
            parse_error=parse_error,
            timestamp=timestamp,
            duration_ms=duration_ms,
        )
        _save_migration_result(res_obj, module_name, self.name)
        return res_obj
