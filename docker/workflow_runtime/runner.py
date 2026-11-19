"""Trusted wire adapter, executed with candidate imports only inside Docker."""
import json
from pathlib import Path
import sys

wire = sys.stdout
sys.stdout = sys.stderr  # Candidate prints cannot masquerade as ordinary RPC messages.
initial = json.loads(sys.stdin.readline())

def rpc(operation, **data):
    wire.write(json.dumps({'operation': operation, **data}) + '\n')
    wire.flush()
    response = json.loads(sys.stdin.readline())
    if not response.get('ok'):
        raise RuntimeError(response.get('error', 'RPC rejected'))
    return response.get('result')

class Client:
    def complete(self, messages, tools, timeout):
        return rpc('complete', messages=messages)

class Sandbox:
    def call(self, name, arguments, timeout=None):
        return rpc('tool', name=name, arguments=arguments)
    def run_command(self, command, timeout=None):
        return self.call('run_command', {'command': command})
    def patch(self):
        return rpc('snapshot')

sys.path.insert(0, '/workspace/src')
try:
    from gemma_lab.agent import AgentLoop
    run = Path('/tmp/runtime-run')
    run.mkdir(exist_ok=True)
    agent = AgentLoop(Client(), Sandbox(), initial['settings'], run)
    result = agent.solve(initial['issue'], initial['system'])
    rpc('finish', outcome=result)
except BaseException as error:
    rpc('finish', outcome={'reason': 'runtime_error', 'error': str(error)})
