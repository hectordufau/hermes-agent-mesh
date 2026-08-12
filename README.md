# hermes-agent-mesh

Multi-host **Hermes Agent** orchestration over **ZeroMQ** — no SSH, no public
ingress. One *orchestrator* host receives your requests (CLI or its own Telegram)
and dispatches work to *remote* hosts that run OpenCode/Hermes. Results, status,
and quota-limit events flow back over the same socket, encrypted with **CURVE**.

Each host also runs its **own** OpenCode free-limit monitor locally — monitoring
is per-host and never crosses the mesh.

## What it does

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

- Orchestrator dispatches a task; the remote dispatcher routes it to the active
  worker (`opencode` | `hermes`) by local `~/.acer_state["mode"]`.
- Replies are JSON `{"task_id", "status", "out"}` where `status` ∈
  `ok | quota_exceeded | paused | timeout | error`.
- `quota_exceeded` fires when the OpenCode worker hits its daily API limit; the
  dispatcher records it in `~/.acer_events` and waits for a user decision on the
  CONTROL socket (`continue_hermes` | `pause` | `resume_opencode`).

## Install

### Orchestrator host

```bash
python3 -m venv ~/.hermes/agentmesh-dist/venv
~/.hermes/agentmesh-dist/venv/bin/pip install "mcp>=1.0,<1.10" pyzmq
# copy the skill files (agentmesh_send.py, agentmesh_mcp.py, agentmesh_bridge.py,
#        curve.py, agentmesh_mcp_launcher.sh) into ~/.hermes/agentmesh-dist/
# generate curve keys (see Security) into ~/.hermes/agentmesh-dist/curve_keys.py
# register MCP (Hermes spawns it on startup):
hermes config set mcp_servers.agentmesh.command "$HOME/.hermes/agentmesh-dist/agentmesh_mcp_launcher.sh"
hermes config set mcp_servers.agentmesh.env.AGENTMESH_TARGET "tcp://<remote-ip>:5555"
# boot service (bridge daemon)
mkdir -p ~/.config/systemd/user
# copy agentmesh-orchestrator.service, then:
systemctl --user daemon-reload
systemctl --user enable --now agentmesh-orchestrator.service
systemctl --user restart hermes-gateway.service   # pick up MCP
```

### Remote host (worker)

Copy `acer_dispatcher.py` + `worker_hermes.py` + `worker_opencode.py` (from the
reference deployment) and the three systemd units. Bind the dispatcher to
`0.0.0.0` so other hosts can reach it, and apply CURVE (`curve.apply_server` on
frontend/backend/control; `curve.apply_client` on the workers). Then:

```bash
systemctl --user enable --now acer-dispatcher acer-worker-opencode acer-worker-hermes
```

## Use

From the orchestrator Hermes (or any tool caller):
`mcp_agentmesh_send_task(prompt="inicie as VMs", repo=None)`.

Or standalone:
`AGENTMESH_TARGET=tcp://<remote>:5555 ~/.hermes/agentmesh-dist/venv/bin/python agentmesh_send.py "prompt"`.

## Security (CURVE)

This mesh uses **CURVE** (ZMQ elliptic-curve) so the broker can bind `0.0.0.0`
without exposing plaintext on the LAN. Channel is encrypted; only peers holding
the curve keys can speak.

Generate per deployment (do **not** commit the result):

```bash
python3 -c "import zmq; sp,ss=zmq.curve_keypair(); cp,cs=zmq.curve_keypair(); print(sp.decode(),ss.decode(),cp.decode(),cs.decode())"
```

Drop the 4 values into `curve_keys.py` on every host:
- server needs `server_*` + `client_*`
- clients need `client_*` + `server_public`

`curve.py` is the keyless helper (safe to publish).

Optional hardening: authenticate specific hosts with `zmq.auth`
(`AuthenticationThread` + `configure_curve(domain, certs_dir)`) so the dispatcher
only accepts known client public keys — do this before adding a 3rd untrusted host.

## Add a 3rd host

Copy the remote side (dispatcher + workers) and point a new orchestrator DEALER
at its `:5555`. The broker is flat — every host is independent. Generate a new
client key pair per host and register it with the dispatcher's CURVE authenticator.

## Layout of this repo

```
skills/software-development/hermes-agent-mesh/
  SKILL.md                       # skill body (load with skill_view)
  agentmesh_send.py              # one-shot DEALER producer (CLI)
  agentmesh_mcp.py               # MCP server exposing send_task (Hermes-native tool)
  agentmesh_mcp_launcher.sh      # launcher so Hermes registers via `command` only
  agentmesh_bridge.py            # persistent bridge daemon (healthcheck + reconnect)
  curve.py                       # keyless CURVE helper
  agentmesh-orchestrator.service # systemd user unit for the bridge
  opencode-local-monitor/        # per-host OpenCode limit monitor (skill + wrapper + installer)
```

`curve_keys.py` is intentionally **not** included — it holds secrets.

## License

MIT
