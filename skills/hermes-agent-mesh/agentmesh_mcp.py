#!/usr/bin/env python3
"""agentmesh_mcp.py — servidor MCP que expoe a malha de agentes como tool nativa.

Registrado no Hermes orquestrador via mcp_servers:
  mcp_servers:
    agentmesh:
      command: "/home/hector/.hermes/agentmesh-dist/venv/bin/python"
      args: ["/home/hector/.hermes/agentmesh-dist/agentmesh_mcp.py"]
      env:
        AGENTMESH_TARGET: "tcp://127.0.0.1:5555"   # via tunnel, ou tcp://192.168.0.150:5555

Tool: send_task(prompt, repo?) -> JSON do resultado do host remoto (Acer).
"""
import os, json
from mcp.server import Server
import mcp.types as types
import zmq
import curve

DEFAULT_TARGET = os.environ.get("AGENTMESH_TARGET", "tcp://127.0.0.1:5555")
TIMEOUT_MS = int(os.environ.get("AGENTMESH_TIMEOUT_MS", "1200000"))

app = Server("hermes-agent-mesh")


def _send(target, prompt, repo, timeout_ms):
    ctx = zmq.Context()
    sock = ctx.socket(zmq.DEALER)
    sock.setsockopt(zmq.LINGER, 0)
    curve.apply_client(sock)
    sock.connect(target)
    sock.send_json({"prompt": prompt, "repo": repo})
    poller = zmq.Poller()
    poller.register(sock, zmq.POLLIN)
    if poller.poll(timeout_ms):
        parts = sock.recv_multipart()
        payload = parts[-1]
        try:
            return json.loads(payload.decode())
        except Exception:
            return {"status": "raw", "out": payload.decode(errors="replace")}
    return {"status": "timeout", "out": f"sem resposta de {target} em {timeout_ms}ms"}


@app.list_tools()
async def list_tools():
    return [types.Tool(
        name="send_task",
        description="Envia uma tarefa para o host remoto da malha (Acer) via ZeroMQ. "
                    "O dispatcher remoto roteia para opencode ou hermes conforme estado local "
                    "e devolve status+resultado. Use para orquestrar execucao em outro host.",
        inputSchema={
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Instrucao/tarefa para o agente remoto."},
                "repo": {"type": "string", "description": "Repo/diretorio de trabalho no host remoto (opcional)."},
            },
            "required": ["prompt"],
        },
    )]


@app.call_tool()
async def call_tool(name, arguments):
    if name != "send_task":
        return [types.TextContent(type="text", text=json.dumps({"status": "error", "out": f"tool desconhecida: {name}"}))]
    target = os.environ.get("AGENTMESH_TARGET", DEFAULT_TARGET)
    res = _send(target, arguments.get("prompt", ""), arguments.get("repo"), TIMEOUT_MS)
    return [types.TextContent(type="text", text=json.dumps(res, ensure_ascii=False, indent=2))]


if __name__ == "__main__":
    import anyio
    from mcp.server.stdio import stdio_server
    async def _run():
        async with stdio_server() as (r, w):
            await app.run(r, w, app.create_initialization_options())
    anyio.run(_run)
