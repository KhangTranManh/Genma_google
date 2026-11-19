import json
from pathlib import Path
import shutil
import subprocess
import time
from .agent import AgentLoop
from .client import VllmClient
from .runs import prepare, write_json
from .sandbox import DockerSandbox
from .serving import endpoint, health
from .experiments import validate_selection, workflow_fingerprint, digest_file


def evaluate(settings, repository, commit, patch, evaluator):
    with DockerSandbox(settings["image"], settings["command_timeout_seconds"], settings["tool_output_chars"]) as clean:
        clean.checkout(repository, commit)
        if patch:
            clean.apply_patch(patch)
        clean.copy_file(evaluator, "/tmp")
        return clean.run_command("PYTHONPATH=/workspace python /tmp/" + Path(evaluator).name)


def solve(project, task, repository, model_key, model, evaluator=None, prompt=None):
    validate_selection(project, model_key, prompt)
    health(project, model)
    settings = dict(project.raw["workflow"])
    if prompt is not None:
        settings["system_prompt"] = str(Path(prompt).resolve())
    profile = next((repo for repo in project.raw["repos"].values() if repo["slug"] == task["repo"]), {})
    settings["verification_command"] = task.get("test_command") or profile.get("test_command")
    if not settings["verification_command"]:
        raise ValueError("Configure test_command for the selected repository before running the local agent")
    run = prepare(project, task, model_key, model)
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.update(status="running", backend="local_docker", competition_score=False, workflow=settings)
    write_json(manifest_path, manifest)
    print("Run directory:", run, flush=True)
    started = time.monotonic()
    try:
        if evaluator:
            baseline = evaluate(settings, repository, task["base_commit"], "", evaluator)
            write_json(run / "baseline-evaluation.json", baseline)
            manifest["baseline_passed"] = baseline["exit_code"] == 0 and not baseline["timed_out"]
        with DockerSandbox(settings["image"], settings["command_timeout_seconds"], settings["tool_output_chars"]) as sandbox:
            sandbox.checkout(repository, task["base_commit"])
            client = VllmClient(endpoint(project), model["alias"], settings["max_output_tokens"], settings["thinking"])
            policy = settings.get("agent_policy", "baseline")
            if policy == "baseline":
                agent = AgentLoop(client, sandbox, settings, run)
            elif policy == "progress":
                from .progress_agent import ProgressAgent
                agent = ProgressAgent(client, sandbox, settings, run)
            else:
                raise ValueError("Unknown workflow.agent_policy")
            system = (project.root / settings["system_prompt"]).read_text()
            (run / "system_prompt.md").write_text(system)
            manifest["prompt_sha256"] = digest_file(run / "system_prompt.md")
            write_json(manifest_path, manifest)
            issue = f"Repository: {task['repo']}\nVerification command: {settings['verification_command']}\nIssue:\n{task['problem_statement']}"
            outcome = agent.solve(issue, system)
            manifest["solve_elapsed_seconds"] = round(time.monotonic() - started, 3)
            if outcome["reason"] not in ("submitted", "harness_submitted"):
                partial = sandbox.patch()
                if partial.strip():
                    (run / "recovered.diff").write_text(partial)
        manifest["agent"] = outcome
        if outcome["reason"] not in ("submitted", "harness_submitted"):
            manifest["status"] = "incomplete"
            if evaluator and (run / "recovered.diff").exists():
                try:
                    recovered = evaluate(settings, repository, task["base_commit"], (run / "recovered.diff").read_text(), evaluator)
                    manifest["recovered_passed"] = recovered["exit_code"] == 0 and not recovered["timed_out"]
                except Exception as error:
                    recovered = {"error": str(error), "diagnostic_only": True}
                    manifest["recovered_passed"] = False
                write_json(run / "recovered-evaluation.json", recovered)
        else:
            patch = (run / "patch.diff").read_text()
            manifest.update(status="submitted", patch_bytes=len(patch.encode()))
            if evaluator:
                result = evaluate(settings, repository, task["base_commit"], patch, evaluator)
                write_json(run / "evaluation.json", result)
                passed = result["exit_code"] == 0 and not result["timed_out"] and bool(patch.strip())
                manifest.update(status="local_pass" if passed else "local_fail", evaluation_passed=passed)
        return run, manifest["status"]
    except BaseException as error:
        manifest.update(status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed", error=str(error))
        raise
    finally:
        manifest["code_changed_during_run"] = workflow_fingerprint(project.root)[0] != manifest["workflow_sha256"]
        manifest["elapsed_seconds"] = round(time.monotonic() - started, 3)
        write_json(manifest_path, manifest)
        print("Run status:", manifest["status"], flush=True)


def demo(project, model_key, model, prompt=None):
    import tempfile
    project.path("runs").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="demo-source-", dir=project.path("runs")) as directory:
        source = Path(directory)
        shutil.copytree(project.root / "examples/urlkit_repo", source, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__"))
        for command in (["git", "init", "-q"], ["git", "add", "-A"],
                        ["git", "-c", "user.name=GemmaLab", "-c", "user.email=local@example.invalid", "commit", "-qm", "baseline"]):
            subprocess.run(command, cwd=source, check=True, capture_output=True)
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
        task = {"instance_id": "demo-urlkit-query", "repo": "local/urlkit", "base_commit": commit,
                "problem_statement": (project.root / "examples/urlkit_issue.md").read_text(),
                "test_command": "python -m unittest discover -s tests -v"}
        return solve(project, task, source, model_key, model, project.root / "examples/evaluation/test_urlkit.py", prompt=prompt)
