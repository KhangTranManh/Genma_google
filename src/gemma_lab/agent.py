"""Bounded local tool loop. Official ADK compilation remains a separate adapter."""
import json
import time
from .tools import TOOLS, validate

class AgentLoop:
    def __init__(self, client, sandbox, settings, run):
        self.client, self.sandbox = client, sandbox
        self.settings, self.run = settings, run
        self.calls = 0
        self.turn = 0
        self.review_requested = False
        self.known_files = []
        self.last_failure = None
        self.verification_passed = False
        self.deadline = time.monotonic() + settings["time_limit_seconds"]
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0}

    def event(self, kind, **data):
        record = {"time": time.time(), "event": kind, **data}
        with (self.run / "trajectory.jsonl").open("a") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        if kind in ("tool_call", "tool_result", "turn", "finished", "compacted"):
            summary = json.dumps(record, ensure_ascii=False)
            print(summary[:1000], flush=True)

    def status(self):
        return {"remaining_seconds": round(max(0, self.deadline - time.monotonic()), 1),
                "remaining_tool_calls": self.settings["max_tool_calls"] - self.calls,
                "remaining_turns": self.settings["max_turns"] - self.turn}

    def solve(self, issue, system):
        initial = [{"role": "system", "content": system},
                   {"role": "user", "content": issue}]
        if sum(len(m["content"]) for m in initial) > self.settings["history_char_limit"] // 2:
            raise ValueError("Task/system prompt exceeds local context allowance")
        groups = []
        for turn in range(1, self.settings["max_turns"] + 1):
            if time.monotonic() >= self.deadline:
                return self.finish("time_limit")
            if self.calls >= self.settings["max_tool_calls"]:
                return self.finish("tool_limit")
            self.turn = turn
            memory = {"known_files": self.known_files[-12:], "last_observed_failure": self.last_failure,
                      "review_requested": self.review_requested, "verification_passed": self.verification_passed,
                      "next_step": "Inspect git diff once, then submit_patch; do not repeat unchanged checks."
                          if self.review_requested and self.verification_passed else "Continue fixing and testing.",
                      "budget": self.status()}
            prefix = initial + [{"role": "user", "content": "Runtime memory (failures may be stale; rerun tests after fixing): " + json.dumps(memory)}]
            messages = prefix + [message for group in groups for message in group]
            while len(json.dumps(messages)) > self.settings["history_char_limit"] and len(groups) > 1:
                groups.pop(0)  # Remove complete assistant + tool-result groups, never orphan tool messages.
                messages = prefix + [message for group in groups for message in group]
                self.event("compacted", retained_groups=len(groups))
            try:
                response = self.client.complete(messages, TOOLS, timeout=max(1, self.deadline - time.monotonic()))
            except TimeoutError as error:
                if time.monotonic() < self.deadline:
                    raise
                self.event("request_timeout", turn=self.turn, error=str(error))
                return self.finish("time_limit")
            self.event("response", response=response)
            for key in self.usage:
                self.usage[key] += response.get("usage", {}).get(key, 0)
            if response["choices"][0]["finish_reason"] == "length":
                self.event("truncated", turn=self.turn)
                groups.append([{"role": "user", "content": "Your previous response exceeded its token limit and was discarded. Use one concise tool call, without a long explanation. Split large edits into smaller changes."}])
                continue
            message = response["choices"][0]["message"]
            calls = message.get("tool_calls") or []
            assistant = {"role": "assistant", "content": message.get("content")}
            if message.get("reasoning"):
                assistant["reasoning"] = message["reasoning"]
            if calls:
                assistant["tool_calls"] = calls
            group = [assistant]
            groups.append(group)
            self.event("turn", turn=self.turn, tool_calls=len(calls), usage=self.usage)
            if not calls:
                group.append({"role": "user", "content": "Use the available tools to complete the fix. Call submit_patch when finished."})
                continue
            submitted = False
            for call in calls:
                name = call["function"]["name"]
                arguments = None
                self.event("tool_call", turn=self.turn, name=name, raw_arguments=call["function"]["arguments"])
                if submitted or self.calls >= self.settings["max_tool_calls"] or time.monotonic() >= self.deadline:
                    result = {"error": "Execution budget exhausted or patch already submitted"}
                else:
                    self.calls += 1
                    try:
                        arguments = json.loads(call["function"]["arguments"])
                        validate(name, arguments)
                        if name == "get_status":
                            result = self.status()
                        elif name == "submit_patch":
                            patch = self.sandbox.patch()
                            result = self.submission_gate(patch)
                            if result.get("submitted"):
                                (self.run / "patch.diff").write_text(patch)
                                submitted = True
                        else:
                            result = self.sandbox.call(name, arguments, timeout=max(1, self.deadline - time.monotonic()))
                    except (ValueError, KeyError) as error:
                        result = {"error": str(error)}
                self.remember_result(name, arguments, result)
                self.event("tool_result", name=name, result=result)
                group.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})
            if submitted:
                return self.finish("submitted")
        return self.finish("turn_limit")

    def remember_result(self, name, arguments, result):
        arguments = arguments if isinstance(arguments, dict) else {}
        if name in ("read_file", "write_file", "edit_file"):
            filename = arguments.get("filepath")
            if filename and filename not in self.known_files:
                self.known_files.append(filename)
            if name in ("write_file", "edit_file") and not result.get("error"):
                self.verification_passed = False
        command = arguments.get("command") if name == "run_command" else None
        failed = result.get("error") or ("exit_code" in result and result["exit_code"] != 0) or result.get("timed_out")
        if failed:
            self.last_failure = {"tool": name, "command": command, "result": json.dumps(result)[:1400]}
        elif command and result.get("exit_code") == 0 and self.last_failure and self.last_failure.get("command") == command:
            self.last_failure = None
        if command and command == self.settings.get("verification_command"):
            self.verification_passed = result.get("exit_code") == 0 and not result.get("timed_out")

    def submission_gate(self, patch):
        if not patch.strip():
            return {"error": "The patch is empty; implement the issue before submitting."}
        if self.settings.get("review_before_submit", False) and not self.review_requested:
            self.review_requested = True
            (self.run / "candidate.diff").write_text(patch)
            return {"review_required": True, "instruction":
                "Inspect git diff and verify EVERY requirement in the issue, especially edge cases. "
                "Add regression tests covering the reported failures, run them, fix any gaps, then call submit_patch again. "
                "No patch has been submitted yet."}
        if self.settings.get("require_regression_tests", False):
            changed = [line.split(" b/", 1)[-1] for line in patch.splitlines() if line.startswith("diff --git ")]
            tests = [name for name in changed if name.startswith("tests/") or "/tests/" in name
                     or name.rsplit("/", 1)[-1].startswith("test_") or name.endswith("_test.py")]
            if not tests:
                return {"error": "Add regression tests for the issue before submitting. Original tests must not be weakened."}
        verify = self.settings.get("verification_command")
        if verify:
            result = self.sandbox.run_command(verify, timeout=max(1, self.deadline - time.monotonic()))
            self.event("verification", command=verify, result=result)
            (self.run / "public-test-result.json").write_text(json.dumps(result, indent=2) + "\n")
            if result.get("exit_code") != 0 or result.get("timed_out"):
                return {"error": "Public verification failed; fix the code and run tests again.", "verification": result}
        return {"submitted": True, "patch_bytes": len(patch.encode())}

    def finish(self, reason):
        result = {"reason": reason, "turns": self.turn, "tool_calls": self.calls, "usage": self.usage}
        self.event("finished", **result)
        return result
