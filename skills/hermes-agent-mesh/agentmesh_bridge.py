#!/usr/bin/env python3
"""agentmesh_bridge.py — daemon de ponte ZeroMQ do orquestrador.

Mantem a comunicacao com o host remoto (Acer) viva: conecta no FRONTEND
(tcp://192.168.0.150:5555) como DEALER, faz healthcheck periodico e reconecta
sozinho se a rede cair. Registra status em ~/.agentmesh_health.

Nao executa tarefas por si — o Hermes orquestrador usa o MCP server
(agentmesh_mcp.py) para disparar. Este daemon so garante que o enlace
"entre servidores" sobrevive a quedas e inicializa com o host (systemd).

Uso: python3 agentmesh_bridge.py
Env:  AGENTMESH_TARGET (default tcp://192.168.0.150:5555)
      AGENTMESH_HEALTH (default ~/.agentmesh_health)
"""
import os, time, json, datetime
import zmq
import curve

TARGET = os.environ.get("AGENTMESH_TARGET", "tcp://192.168.0.150:5555")
HEALTH = os.environ.get("AGENTMESH_HEALTH", os.path.expanduser("~/.agentmesh_health"))
HEALTH_INTERVAL = int(os.environ.get("AGENTMESH_HEALTH_INTERVAL", "30"))


def write_health(state, detail=""):
    line = f"{datetime.datetime.now().isoformat()} | {state} | {detail}\n"
    try:
        with open(HEALTH, "w") as f:
            f.write(line)
    except Exception:
        pass


def main():
    ctx = zmq.Context()
    sock = ctx.socket(zmq.DEALER)
    sock.setsockopt(zmq.LINGER, 0)
    curve.apply_client(sock)
    connected = False
    while True:
        try:
            if not connected:
                sock.connect(TARGET)
                connected = True
                write_health("CONNECTED", TARGET)
                print(f"[bridge] conectado a {TARGET}", flush=True)
            # healthcheck: envia ping, espera pong curto
            sock.send_json({"prompt": "__mesh_ping__", "repo": None})
            poller = zmq.Poller(); poller.register(sock, zmq.POLLIN)
            if poller.poll(5000):
                sock.recv_multipart()  # descarta resposta
                write_health("OK", TARGET)
            else:
                write_health("STALE", "sem resposta em 5s")
        except Exception as e:
            connected = False
            try: sock.disconnect(TARGET)
            except Exception: pass
            write_health("DOWN", str(e)[:120])
            print(f"[bridge] queda: {e} — reconectando em 5s", flush=True)
            time.sleep(5)
            continue
        time.sleep(HEALTH_INTERVAL)


if __name__ == "__main__":
    main()
