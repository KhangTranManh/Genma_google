from pathlib import Path
import subprocess
import zipfile

BLOCKED = {".git", "__pycache__", ".env", ".venv"}

def submission_files(root):
    root = Path(root).resolve()
    if not (root / "agent.yaml").is_file():
        raise ValueError("submission/agent.yaml is missing. Import the official sample first.")
    files = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_symlink():
            raise ValueError(f"Submission symlinks are forbidden: {relative}")
        if any(part in BLOCKED or part.startswith(".env.") for part in relative.parts):
            raise ValueError(f"Unexpected private/runtime file in submission: {relative}")
        if path.is_file():
            files.append((path, relative))
    return files

def package(project, validator, allow_unvalidated=False):
    source = project.path("submission")
    files = submission_files(source)
    if not validator and not allow_unvalidated:
        raise ValueError("Configure harness.validator_command, or use --allow-unvalidated for a development archive.")
    if validator:
        subprocess.run(validator, cwd=project.root, check=True)
    target = project.path("dist") / ("submission.zip" if validator else "submission.unvalidated.zip")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for path, relative in files:
                archive.write(path, relative.as_posix())
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target
