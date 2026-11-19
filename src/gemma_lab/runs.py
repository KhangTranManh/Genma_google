from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import uuid
from .tasks import agent_input
from .serving import endpoint
from .experiments import identity, workflow_fingerprint, workflow_files
import tarfile

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")

def prepare(project, task, model_key, model):
    run = project.path("runs") / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    run.mkdir(parents=True)
    experiment = identity(project)
    fingerprint, sources = workflow_fingerprint(project.root)
    with tarfile.open(run / "workflow-source.tar.gz", "w:gz") as archive:
        for path in workflow_files(project.root):
            archive.add(path, arcname=str(path.relative_to(project.root)))
    write_json(run / "workflow-files.json", sources)
    write_json(run / "agent_input.json", agent_input(task))
    # Full task (including reference patches) is deliberately not persisted in the run.
    write_json(run / "manifest.json", {
        "experiment": experiment, "workflow_sha256": fingerprint,
        "status": "prepared", "instance_id": task["instance_id"],
        "repo": task["repo"], "base_commit": task["base_commit"],
        "model_key": model_key, "model": model["alias"],
        "base_url": endpoint(project), "config": project.raw,
    })
    return run

def variables(project, model, run=None, instance_id=""):
    return {"submission": str(project.path("submission")), "model": model["alias"],
            "base_url": endpoint(project), "tasks": str(project.path("tasks")),
            "run_dir": str(run) if run else "", "instance_id": instance_id,
            "agent_input": str(run / "agent_input.json") if run else ""}

def expand(command, values):
    if not isinstance(command, list) or not all(isinstance(arg, str) for arg in command):
        raise ValueError("Harness command must be a TOML array of argument strings")
    return [arg.format_map(values) for arg in command]

def execute(project, command, run):
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.update(status="running", command=command)
    write_json(manifest_path, manifest)
    try:
        with (run / "harness.log").open("w") as output:
            result = subprocess.run(command, cwd=project.root, stdout=output, stderr=subprocess.STDOUT)
        manifest.update(status="harness_finished" if result.returncode == 0 else "failed", returncode=result.returncode)
        return result.returncode
    except BaseException as error:
        manifest.update(status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed", error=str(error))
        raise
    finally:
        write_json(manifest_path, manifest)
