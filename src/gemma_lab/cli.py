import argparse
import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from .config import load
from .tasks import read_tasks
from .serving import endpoint, health, serve, serve_command
from .runs import execute, expand, prepare, variables
from .submission import package

def main(argv=None):
    parser = argparse.ArgumentParser(prog="gemma-lab")
    parser.add_argument("--config", default="configs/project.toml")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("doctor")
    sub.add_parser("archive-results")
    for name in ("serve", "health", "tasks", "prepare", "run", "package", "demo", "solve", "improve-prompt"):
        command = sub.add_parser(name)
        command.add_argument("--model")
        if name in ("tasks", "prepare", "run", "solve"):
            command.add_argument("--repo")
        if name in ("prepare", "run", "solve"):
            command.add_argument("--task", required=True)
        if name in ("demo", "solve"):
            command.add_argument("--prompt", type=Path)
        if name == "improve-prompt":
            command.add_argument("--from-run", required=True, type=Path)
            command.add_argument("--evaluate-demo", action="store_true")
        if name == "solve":
            command.add_argument("--checkout", required=True, type=Path)
        if name == "serve":
            command.add_argument("--dry-run", action="store_true")
        if name == "package":
            command.add_argument("--allow-unvalidated", action="store_true")
    args = parser.parse_args(argv)
    try:
        project = load(args.config)
        if args.action == "archive-results":
            from .experiments import archive_results
            records = archive_results(project, legacy=True)
            print(f"Archived {len(records)} finished runs to experiments/results")
            return 0
        if args.action == "doctor":
            print(json.dumps({"python": sys.version.split()[0], "executables": {
                name: (str(project.root / ".venv/bin/vllm")
                       if name == "vllm" and (project.root / ".venv/bin/vllm").is_file()
                       else shutil.which(name))
                for name in ("vllm", "docker", "git", "nvidia-smi")},
                "tasks_available": project.path("tasks").is_file(),
                "agent_available": (project.path("submission") / "agent.yaml").is_file(),
                "endpoint": endpoint(project)}, indent=2))
            if shutil.which("nvidia-smi"):
                subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv"], check=True)
            return 0
        key, model = project.select("model", args.model)
        if args.action == "serve":
            if args.dry_run:
                print("CUDA_VISIBLE_DEVICES=" + project.raw["serving"]["devices"] + " " + shlex.join(serve_command(project, model)))
                return 0
            return serve(project, model)
        if args.action == "health":
            print(json.dumps(health(project, model), indent=2))
            return 0
        if args.action == "package":
            validator = expand(project.raw["harness"]["validator_command"], variables(project, model))
            print(package(project, validator, args.allow_unvalidated))
            return 0
        if args.action == "improve-prompt":
            from .prompts import propose
            prompt = propose(project, args.from_run, key, model)
            if args.evaluate_demo:
                from .local import demo
                _, status = demo(project, key, model, prompt=prompt)
                return 0 if status == "local_pass" else 1
            return 0
        if args.action == "demo":
            from .local import demo
            _, status = demo(project, key, model, prompt=args.prompt)
            return 0 if status == "local_pass" else 1
        _, repo = project.select("repo", args.repo)
        tasks = list(read_tasks(project.path("tasks"), repo["slug"]))
        if args.action == "tasks":
            for task in tasks:
                print(task["instance_id"], task["repo"], task["base_commit"])
            return 0
        matches = [task for task in tasks if task["instance_id"] == args.task]
        if not matches:
            raise ValueError(f"Task {args.task} not found in {repo['slug']}")
        if args.action == "solve":
            from .local import solve
            _, status = solve(project, matches[0], args.checkout.resolve(), key, model, prompt=args.prompt)
            return 0 if status == "submitted" else 1
        if args.action == "run":
            if not project.raw["harness"]["command"]:
                raise ValueError("Configure harness.command from the official HARNESS_README.md before running")
            if not (project.path("submission") / "agent.yaml").is_file():
                raise ValueError("Import the official submission/agent.yaml before running")
            health(project, model)
        run = prepare(project, matches[0], key, model)
        print(run, flush=True)
        if args.action == "run":
            command = expand(project.raw["harness"]["command"], variables(project, model, run, args.task))
            return execute(project, command, run)
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError, subprocess.TimeoutExpired, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
