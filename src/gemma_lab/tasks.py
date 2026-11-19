import json

AGENT_FIELDS = ("instance_id", "repo", "base_commit", "problem_statement", "hints_text")

def read_tasks(path, repo=None):
    seen = set()
    with path.open() as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            task = json.loads(line)
            for key in ("instance_id", "repo", "base_commit", "problem_statement"):
                if not isinstance(task.get(key), str) or not task[key].strip():
                    raise ValueError(f"Task line {number}: missing or empty {key}")
            if task["instance_id"] in seen:
                raise ValueError(f"Duplicate task: {task['instance_id']}")
            seen.add(task["instance_id"])
            if repo is None or task["repo"] == repo:
                yield task

def agent_input(task):
    # Never hand reference patches or evaluator-only metadata to the agent.
    return {key: task[key] for key in AGENT_FIELDS if key in task}
