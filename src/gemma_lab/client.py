import json
import urllib.error
import urllib.request

class VllmClient:
    def __init__(self, base_url, model, max_tokens=1024, thinking=False):
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.thinking = thinking

    def complete(self, messages, tools, timeout, response_format=None):
        body = {"model": self.model, "messages": messages, "temperature": 0, "max_tokens": self.max_tokens,
                "chat_template_kwargs": {"enable_thinking": self.thinking}}
        if tools:
            body.update(tools=tools, tool_choice="auto")
        if response_format:
            body["response_format"] = response_format
        request = urllib.request.Request(self.base_url + "/chat/completions",
            data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                result = json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"vLLM HTTP {error.code}: {error.read(2000).decode(errors='replace')}") from error
        if "error" in result:
            raise RuntimeError(result["error"])
        return result
