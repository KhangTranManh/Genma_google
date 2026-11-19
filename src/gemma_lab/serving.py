import os
import subprocess
import urllib.request
import json

def endpoint(project):
    serving = project.raw["serving"]
    return f"http://{serving['host']}:{serving['port']}/v1"

def serve_command(project, model):
    settings = project.raw["serving"]
    if settings["backend"] != "vllm":
        raise ValueError("Only vLLM serving is implemented")
    executable = project.root / ".venv/bin/vllm"
    command = [str(executable) if executable.is_file() else "vllm", "serve", str((project.root / model["path"]).resolve()),
               "--served-model-name", model["alias"],
               "--host", settings["host"], "--port", str(settings["port"]),
               "--tensor-parallel-size", str(settings["tensor_parallel_size"]),
               "--max-model-len", str(settings["max_model_len"]),
               "--gpu-memory-utilization", str(settings["gpu_memory_utilization"]),
               "--dtype", settings["dtype"]]
    return command + settings.get("extra_args", [])

def serve(project, model):
    path = project.root / model["path"]
    if not (path / "config.json").is_file():
        raise ValueError(f"Model checkpoint missing config.json: {path}")
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=project.raw["serving"]["devices"])
    return subprocess.call(serve_command(project, model), env=env, cwd=project.root)

def health(project, model):
    with urllib.request.urlopen(endpoint(project) + "/models", timeout=10) as response:
        data = json.load(response)
    names = [item["id"] for item in data.get("data", [])]
    if model["alias"] not in names:
        raise ValueError(f"Expected {model['alias']}, endpoint serves: {names}")
    return data
