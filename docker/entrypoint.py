#!/usr/bin/env python
"""Container entrypoint: reads code from stdin, executes it, outputs JSON result.

Schema:
{
  "stdout": str,
  "stderr": str,
  "exit_code": int,
  "exception_type": str or None,
  "exception_message": str or None,
  "duration_ms": float,
  "timed_out": bool
}
"""

import sys
import os
import json
import time
import traceback


def main():
    start_time = time.time()
    code = sys.stdin.read()

    # Capture stdout and stderr
    import io
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = stdout_buf = io.StringIO() if sys.version_info[0] >= 3 else io.BytesIO()
    sys.stdout_write = sys.stdout.write
    sys.stderr = stderr_buf = io.StringIO() if sys.version_info[0] >= 3 else io.BytesIO()

    exit_code = 0
    exc_type_str = None
    exc_msg_str = None
    timed_out = False

    try:
        global_ns = {"__name__": "__main__", "__file__": "<sandbox>"}
        exec(code, global_ns)
    except SystemExit as e:
        exit_code = e.code if isinstance(e.code, int) else (1 if e.code else 0)
    except Exception as e:
        exit_code = 1
        exc_type_str = type(e).__name__
        exc_msg_str = str(e)
        traceback.print_exc(file=stderr_buf)

    duration_ms = (time.time() - start_time) * 1000.0

    sys.stdout = old_stdout
    sys.stderr = old_stderr

    result = {
        "stdout": stdout_buf.getvalue(),
        "stderr": stderr_buf.getvalue(),
        "exit_code": exit_code,
        "exception_type": exc_type_str,
        "exception_message": exc_msg_str,
        "duration_ms": round(duration_ms, 3),
        "timed_out": timed_out,
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
