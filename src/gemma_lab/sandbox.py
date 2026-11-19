"""Docker boundary shared by the local agent and clean patch evaluator."""
import io
import json
import re
from pathlib import Path
import subprocess
import tarfile
import uuid

class DockerSandbox:
    def __init__(self, image, timeout=20, output_limit=6000):
        self.image = image
        self.timeout = timeout
        self.output_limit = output_limit
        self.name = "gemma-lab-" + uuid.uuid4().hex[:12]

    def __enter__(self):
        subprocess.run(["docker", "run", "--detach", "--name", self.name,
                        "--network", "none", "--cap-drop", "ALL",
                        "--security-opt", "no-new-privileges", "--pids-limit", "128",
                        "--memory", "2g", "--cpus", "2", "--read-only",
                        "--env", "PYTHONDONTWRITEBYTECODE=1",
                        "--tmpfs", "/workspace:rw,exec,size=512m,mode=1777,uid=1000,gid=1000",
                        "--tmpfs", "/tmp:rw,exec,size=256m,mode=1777",
                        self.image], check=True, capture_output=True, text=True, timeout=60)
        return self

    def __exit__(self, *exc):
        subprocess.run(["docker", "rm", "--force", self.name], capture_output=True, timeout=30)

    def _exec(self, args, data=None, timeout=None):
        return subprocess.run(["docker", "exec", "-i", "--workdir", "/workspace", self.name, *args],
                              input=data, capture_output=True, timeout=timeout or self.timeout + 10)

    def copy_file(self, source, target):
        # Trusted evaluator files are only copied into a fresh evaluation container.
        source = Path(source)
        content = source.read_bytes()
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w") as tar:
            info = tarfile.TarInfo(source.name)
            info.size = len(content)
            info.mode = 0o444
            tar.addfile(info, io.BytesIO(content))
        copied = self._exec(["tar", "--extract", "--file=-", "--no-same-owner", "--directory=" + target], archive.getvalue(), timeout=30)
        if copied.returncode:
            raise RuntimeError(copied.stderr.decode(errors="replace"))

    def checkout(self, repository, commit):
        # Export tracked files at the exact commit, with no .git or host credentials.
        if not re.fullmatch(r"[0-9a-fA-F]{40}", commit):
            raise ValueError("base_commit must be a full 40-character Git commit SHA")
        snapshot = subprocess.run(["git", "-C", str(repository), "archive", "--format=tar", commit],
                                  capture_output=True, check=True, timeout=30).stdout
        with tarfile.open(fileobj=io.BytesIO(snapshot)) as tar:
            for item in tar:
                if item.issym() or item.islnk() or item.isdev():
                    raise ValueError("Local runner currently requires a repository without links or device files")
        extracted = self._exec(["tar", "--extract", "--file=-", "--no-same-owner", "--directory=/workspace"], snapshot, timeout=30)
        if extracted.returncode:
            raise RuntimeError(extracted.stderr.decode(errors="replace"))
        result = self.run_command("git init -q && git config user.email local@example.invalid && "
                                  "git config user.name GemmaLab && git add -A && git commit -qm baseline")
        if result["exit_code"]:
            raise RuntimeError(result["output"])

    def call(self, name, arguments, timeout=None):
        payload = json.dumps({"name": name, "arguments": arguments,
                              "timeout": min(self.timeout, timeout) if timeout is not None else self.timeout,
                              "output_limit": self.output_limit}).encode()
        result = self._exec(["python", "/opt/gemma/tools.py"], payload)
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors="replace"))
        return json.loads(result.stdout)

    def run_command(self, command, timeout=None):
        return self.call("run_command", {"command": command}, timeout)

    def patch(self):
        # Never truncate a submitted patch as we truncate ordinary tool output.
        result = self._exec(["bash", "-c", "git add -N . && git diff --binary HEAD"])
        if result.returncode:
            raise RuntimeError(result.stderr.decode(errors="replace"))
        if len(result.stdout) > 4 * 1024 * 1024:
            raise ValueError("Local patch limit exceeded (4 MiB)")
        return result.stdout.decode()

    def apply_patch(self, patch):
        result = self._exec(["git", "apply", "--whitespace=nowarn", "-"], patch.encode())
        if result.returncode:
            raise ValueError(result.stderr.decode(errors="replace"))
