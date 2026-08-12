---
name: hermes-agent-mesh
description: Multi-host Hermes orchestration over ZeroMQ. Orchestrator host dispatches tasks to remote Hermes/OpenCode workers via a ROUTER/DEALER broker; results, status, and quota events flow back. Includes a LOCAL per-host OpenCode free-limit monitor. Publish-ready.
version: 1.0.0
author: Hector Dufau
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [multi-agent, orchestration, zeromq, mesh, remote, networking]
    related_skills: [opencode-free-limit-monitor]
---

# Hermes Agent Mesh (ZeroMQ)

Orchestrate several Hermes hosts over a ZeroMQ broker — no SSH, no public
ingress. One **orchestrator** host receives your requests (CLI or its own
Telegram) and dispatches work to **remote** hosts that run OpenCode/Hermes.
Results, status, and quota-limit events flow back over the same socket.

Each host also runs its **own** OpenCode free-limit monitor locally (see
`opencode-free-limit-monitor`) — monitoring is per-host and never crosses the
mesh.

## Topology

```
[you] -> Hermes(orchestrator) --mcp_agentmesh_send_task--> agentmesh_mcp.py
                                                     |
                                            ZMQ DEALER  tcp://<remote>:5555
                                                     |
                                              acer_dispatcher (ROUTER)
                                              /          |          \
                                    5555 prod.      5556 workers   5557 control
                                    (ROUTER)        (ROUTER)        (ROUTER)
                                                   /        \
                                          worker_opencode   worker_hermes
                                          (DEALER id=       (DEALER id=
                                           "opencode")       "hermes")
```

- Orchestrator: `hermes-gateway.service` (spawns MCP) + `agentmesh-orchestrator.service` (bridge daemon).
- Remote (Acer reference): `acer-dispatcher.service` + `acer-worker-opencode.service` + `acer-worker-hermes.service` + `hermes-gateway.service`.
- Add a 3rd host: copy the remote side (dispatcher+workers) and point a new
  orchestrator DEALER at its `:5555`. Broker is flat — every host is independent.

## Protocol (dispatcher FRONTEND, ROUTER on :5555)

Producer -> dispatcher: multipart JSON `{"prompt": "...", "repo": "..."}`.
Dispatcher adds `task_id`, routes to the active worker by `~/.acer_state["mode"]`
(`opencode` | `hermes`), and replies:

Dispatcher -> producer: multipart JSON `{"task_id": "tN", "status": "...", "out": "..."}`
where `status` ∈ `ok | quota_exceeded | paused | timeout | error`.

`quota_exceeded` is emitted when the OpenCode worker hits its daily API limit;
the dispatcher records it in `~/.acer_events` and waits for a user decision on
the CONTROL socket (`continue_hermes` | `pause` | `resume_opencode`) — it never
auto-switches state.

## Install — orchestrator host

```bash
# deps
python3 -m venv ~/.hermes/agentmesh-dist/venv
~/.hermes/agentmesh-dist/venv/bin/pip install mcp==1.9.4 pyzmq==27.1.0
# files live in ~/.hermes/agentmesh-dist/: agentmesh_send.py, agentmesh_mcp.py,
#        agentmesh_bridge.py, install.sh
# register MCP (Hermes spawns it on startup):
hermes config set mcp_servers.agentmesh.command "$HOME/.hermes/agentmesh-dist/agentmesh_mcp_launcher.sh"
hermes config set mcp_servers.agentmesh.env.AGENTMESH_TARGET "tcp://<remote-ip>:5555"
# boot service (bridge daemon)
mkdir -p ~/.config/systemd/user
# (copy agentmesh-orchestrator.service, then:)
systemctl --user daemon-reload
systemctl --user enable --now agentmesh-orchestrator.service
systemctl --user restart hermes-gateway.service   # pick up MCP
```

## Install — remote host (worker)

Copy `acer_dispatch/` (dispatcher + 2 workers) and the three systemd units.
The dispatcher must listen on all network interfaces so other hosts can reach
it — see `references/broker.md` for the exact bind lines and the CURVE setup.

`systemctl --user enable --now acer-dispatcher acer-worker-opencode acer-worker-hermes`.

## Use

From the orchestrator Hermes (or any tool caller): `mcp_agentmesh_send_task(prompt="inicie as VMs", repo=None)`.
Or standalone: `AGENTMESH_TARGET=tcp://<remote>:5555 ~/.hermes/agentmesh-dist/venv/bin/python agentmesh_send.py "prompt"`.

## Security (CURVE applied)

This mesh uses **CURVE** (ZMQ elliptic-curve) so the broker can listen on all
interfaces without exposing plaintext on the LAN. Channel is encrypted; only
peers holding the curve keys can speak. Layout:
- Server (dispatcher, Acer): `curve.apply_server(sock)` on frontend/backend/control.
- Clients (workers + orchestrator): `curve.apply_client(sock)` before `connect`.
- Keys live in `curve_keys.py` (server + client pairs). Generate per deployment
  and keep that file out of version control:
  `python3 -c "import zmq; sp,ss=zmq.curve_keypair(); cp,cs=zmq.curve_keypair(); print(sp.decode(),ss.decode(),cp.decode(),cs.decode())"`
  drop the 4 values into `curve_keys.py` on every host (server needs server_*
  + client_*; clients need client_* + server_public).
- `curve.py` is the keyless helper (safe to publish).

Optional hardening (not applied here): authenticate specific hosts with
`zmq.auth` so the dispatcher only accepts known client public keys. Do this
before adding a 3rd untrusted host.

## Pitfalls

- DEALER producer works against a ROUTER frontend; the last multipart frame is the JSON payload.
- If the dispatcher restarts, in-memory `pending` is lost (state file survives); workers reconnect automatically.
- mcp SDK must be **1.x** (`@app.list_tools()` decorator API). 2.x changed the API.
- Configure MCP servers via `hermes config set mcp_servers...` rather than editing files by hand.
- The OpenCode limit monitor is **local per host**; the orchestrator does NOT watch the remote opencode — each host watches its own.

## Files in this skill

- `agentmesh_send.py` — one-shot DEALER producer (CLI).
- `agentmesh_mcp.py` — MCP server exposing `send_task` (Hermes-native tool).
- `agentmesh_mcp_launcher.sh` — launcher so Hermes can register it via `command` only (config set can't write `args` lists).
- `agentmesh_bridge.py` — persistent bridge daemon (healthcheck + reconnect), boot service.
- `curve.py` — keyless CURVE helper (`apply_server` / `apply_client`).
- `agentmesh-orchestrator.service` — systemd user unit for the bridge.
- `opencode-local-monitor/` — the per-host OpenCode limit monitor (skill + wrapper + installer).
- `curve_keys.py` — NOT included (holds secrets). Generate per deployment, see Security.
