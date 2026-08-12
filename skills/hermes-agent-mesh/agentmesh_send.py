#!/usr/bin/env python3
"""agentmesh_send.py — produtor ZeroMQ do orquestrador.

Conecta no FRONTEND (ROUTER) do acer_dispatcher e envia uma tarefa.
O dispatcher roteia para o worker ativo (opencode|hermes) conforme ~/.acer_state
e devolve {"task_id","status","out"}.

Protocolo (frontend 5555):
  envio : JSON {"prompt": "...", "repo": "..."}
  resposta: JSON {"task_id": "tN", "status": "...", "out": "..."}
  status: ok | quota_exceeded | paused | timeout | error

Uso:
  python3 agentmesh_send.py "faça X no repo Y" [repo]
  python3 agentmesh_send.py --target tcp://192.168.0.150:5555 "prompt"
"""
import sys, json, argparse, os
import zmq
import curve

DEFAULT_TARGET = os.environ.get("AGENTMESH_TARGET", "tcp://127.0.0.1:5555")
TIMEOUT_MS = int(os.environ.get("AGENTMESH_TIMEOUT_MS", "1200000"))  # 20 min


def send(target, prompt, repo, timeout_ms):
    ctx = zmq.Context()
    sock = ctx.socket(zmq.DEALER)
    sock.setsockopt(zmq.LINGER, 0)
    curve.apply_client(sock)
    sock.connect(target)
    task = {"prompt": prompt, "repo": repo}
    sock.send_json(task)
    poller = zmq.Poller()
    poller.register(sock, zmq.POLLIN)
    if poller.poll(timeout_ms):
        parts = sock.recv_multipart()
        # ROUTER pode prefixar identity; pega o ultimo frame (payload)
        payload = parts[-1]
        try:
            return json.loads(payload.decode())
        except Exception:
            return {"status": "raw", "out": payload.decode(errors="replace")}
    return {"status": "timeout", "out": f"sem resposta de {target} em {timeout_ms}ms"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ap.add_argument("repo", nargs="?", default=None)
    ap.add_argument("--target", default=DEFAULT_TARGET)
    ap.add_argument("--timeout-ms", type=int, default=TIMEOUT_MS)
    a = ap.parse_args()
    res = send(a.target, a.prompt, a.repo, a.timeout_ms)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
