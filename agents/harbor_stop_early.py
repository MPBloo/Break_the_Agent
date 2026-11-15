"""Harbor agent for the judges' stop-early baseline.

It plays exactly like the reference, through the MCP tools, then stops after two of the five hotspots.
The three untreated hotspots score -0.5 each, so stopping early earns almost nothing.

    PYTHONPATH=. harbor run -p harbor/tasks/canadair-firefighting-seed-1 -a agents.harbor_stop_early:StopEarlyAgent

Harbor gives a custom agent no access to the task folder, so this agent ships its own copy of the
reference and of the MCP client into the agent's container, then runs them there.
"""
import os
import shutil
import tempfile
from pathlib import Path

from harbor.agents.base import BaseAgent
from harbor.agents.capabilities import AgentCapabilities
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

ROOT = Path(__file__).resolve().parent.parent

PLAY = '''import sys
from reference import Reference
from mcp_client import McpClient

client = McpClient(url=sys.argv[1])
Reference(client).run(max_targets=2)
client.close()
print("Stopped after two hotspots.")
'''


class StopEarlyAgent(BaseAgent):
    capabilities = AgentCapabilities(mcp_servers=True)   # it plays through the task's MCP server

    @staticmethod
    def name() -> str:
        return "stop-early"

    def version(self) -> str:
        return "1.0.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        return

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(ROOT / "agents" / "reference.py", os.path.join(tmp, "reference.py"))
            shutil.copy(ROOT / "bomber" / "mcp_client.py", os.path.join(tmp, "mcp_client.py"))
            Path(tmp, "stop_early.py").write_text(PLAY)
            await environment.upload_dir(source_dir=tmp, target_dir="/tmp/stop_early")
        result = await environment.exec(
            command='pip install --break-system-packages --quiet "mcp>=1.12" 2>/dev/null || pip install --quiet "mcp>=1.12"; '
                    "cd /tmp/stop_early && python3 stop_early.py http://mcp-server:8000/mcp",
            env={"DEBIAN_FRONTEND": "noninteractive"},
        )
        (self.logs_dir / "stop_early.txt").write_text((result.stdout or "") + (result.stderr or ""))
