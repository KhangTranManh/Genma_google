"""Agent-facing names/signatures follow the basic competition tool subset."""

def function(name, description, properties, required=()):
    return {"type": "function", "function": {"name": name, "description": description,
        "parameters": {"type": "object", "properties": properties,
                       "required": list(required), "additionalProperties": False}}}

STRING = {"type": "string"}
TOOLS = [
    function("run_command", "Execute a bash command in /workspace. Network is disabled.",
             {"command": STRING}, ["command"]),
    function("read_file", "Read a repository file; optional line bounds are 1-indexed and inclusive.",
             {"filepath": STRING, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}}, ["filepath"]),
    function("edit_file", "Replace an exact string in an existing file. Matching must be unique unless allow_multiple is true.",
             {"filepath": STRING, "old_string": STRING, "new_string": STRING,
              "allow_multiple": {"type": "boolean"}}, ["filepath", "old_string", "new_string"]),
    function("write_file", "Create or overwrite a repository file.",
             {"filepath": STRING, "content": STRING}, ["filepath", "content"]),
    function("get_status", "Inspect remaining time, turns and tool-call budget.", {}),
    function("submit_patch", "Capture the current git diff and finish the task. Run focused tests and inspect the diff first.", {}),
]

ALLOWED = {tool["function"]["name"]: tool["function"]["parameters"] for tool in TOOLS}

def validate(name, arguments):
    if name not in ALLOWED or not isinstance(arguments, dict):
        raise ValueError("Unknown tool or invalid arguments")
    schema = ALLOWED[name]
    if set(arguments) - set(schema["properties"]):
        raise ValueError("Unexpected tool arguments")
    if set(schema["required"]) - set(arguments):
        raise ValueError("Missing required arguments")
    for key, value in arguments.items():
        expected = schema["properties"][key]["type"]
        if ((expected == "string" and not isinstance(value, str)) or
            (expected == "integer" and type(value) is not int) or
            (expected == "boolean" and type(value) is not bool)):
            raise ValueError(f"Wrong type for {key}")
