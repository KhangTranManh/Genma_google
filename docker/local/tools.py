"""Tool implementation executed inside the container, never on the host."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

ROOT = Path("/workspace")

def path(value):
    result = (ROOT / value).resolve()
    if not result.is_relative_to(ROOT):
        raise ValueError("Path must remain within /workspace")
    return result

def command(text, timeout, limit):
    # Use a file rather than unbounded PIPE buffers for noisy subprocesses.
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(["/bin/bash", "-c", text], cwd=ROOT,
                                   stdout=output, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        expired = False
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            expired = True
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        output.seek(0)
        text = output.read(limit + 1).decode(errors="replace")
    return {"exit_code": process.returncode, "timed_out": expired,
            "output": text[:limit], "truncated": len(text) > limit}

def dispatch(name, args, timeout, limit):
    if name == "run_command":
        return command(args["command"], timeout, limit)
    if name == "read_file":
        lines = path(args["filepath"]).read_text().splitlines()
        start = args.get("start_line") or 1
        end = args.get("end_line") or len(lines)
        if start < 1 or end < start:
            raise ValueError("Use 1-indexed inclusive line ranges")
        text = "\n".join(f"{i}: {line}" for i, line in enumerate(lines[start-1:end], start))
        return {"content": text[:limit], "truncated": len(text) > limit}
    if name == "write_file":
        target = path(args["filepath"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(args["content"])
        return {"written": args["filepath"]}
    if name == "edit_file":
        target = path(args["filepath"])
        old = args["old_string"]
        if not old:
            raise ValueError("old_string must not be empty")
        if old == args["new_string"]:
            raise ValueError("new_string equals old_string; no changes made. Read the file and correct the edit.")
        text = target.read_text()
        count = text.count(old)
        if count == 0:
            raise ValueError("old_string was not found. Read the current file and retry with exact text.")
        if count > 1 and not args.get("allow_multiple", False):
            raise ValueError(f"Expected one match, got {count}; use allow_multiple for all matches")
        target.write_text(text.replace(old, args["new_string"], -1 if args.get("allow_multiple", False) else 1))
        return {"replacements": count if args.get("allow_multiple", False) else 1}
    raise ValueError(f"Unsupported tool: {name}")

if __name__ == "__main__":
    try:
        payload = json.load(sys.stdin)
        result = dispatch(payload["name"], payload["arguments"], payload["timeout"], payload["output_limit"])
    except Exception as error:
        result = {"error": str(error)}
    print(json.dumps(result))
