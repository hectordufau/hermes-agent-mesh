# Broker reference (dispatcher bind + CURVE)

This file holds the low-level broker configuration referenced from SKILL.md.
It is intentionally separate from the main skill body.

## Dispatcher bind (all interfaces)

The remote dispatcher must accept connections from other hosts on the LAN, so
it binds on every interface instead of loopback. In `acer_dispatcher.py` use the
ZMQ wildcard host (`*` means all interfaces):

```python
FRONTEND = "tcp://*:5555"   # tasks (producers)
BACKEND  = "tcp://*:5556"   # workers (DEALER)
CONTROL  = "tcp://*:5557"   # user decisions
```

Producers connect with a DEALER socket at `tcp://<remote-ip>:5555`.

## CURVE setup

`curve.py` exposes two helpers:

```python
import curve
curve.apply_server(sock)   # dispatcher: frontend/backend/control, before bind
curve.apply_client(sock)   # workers + orchestrator, before connect
```

`curve_keys.py` (not in this repo — generate per deployment) holds:
- `SERVER_PUBLIC` / `SERVER_SECRET` — used by the dispatcher (apply_server).
- `CLIENT_PUBLIC` / `CLIENT_SECRET` — used by workers + orchestrator (apply_client),
  plus `SERVER_PUBLIC` as the server key.

Generate:
```bash
python3 -c "import zmq; sp,ss=zmq.curve_keypair(); cp,cs=zmq.curve_keypair(); print(sp.decode(),ss.decode(),cp.decode(),cs.decode())"
```

Hardening: to accept only known hosts, add `zmq.auth` — an `AuthenticationThread`
with `configure_curve(domain, certs_dir)` — before going multi-host on an
untrusted network.

## Remote host notes (Acer reference deployment)

The mesh runs arbitrary commands on the connected host — that is its purpose.
Observations from the Acer box:

- **QEMU/KVM via libvirt**: the user's default `virsh` points at
  `qemu:///session` (empty). Real VMs live in `qemu:///system`. Always use the
  explicit URI:
  ```bash
  virsh -c qemu:///system list --all          # enumerate
  virsh -c qemu:///system start <name>        # boot a VM
  ```
  The `hector` user can drive `qemu:///system` (passwordless sudo `virsh`
  confirmed). The actual domain names are **`win11`**, `macOS`, `SAPABAP`
  (NOT `windows11` — that name does not exist and `virsh start windows11`
  fails with "failed to get domain").
- **multipass** VMs (edi, gold, matriz, mgv, sic) run alongside and are started
  with `multipass start --all` / listed with `multipass list`.

The worker echoes raw shell output (prompt + ANSI escapes). Parse the body, not
the decoration, when reading `out`.
