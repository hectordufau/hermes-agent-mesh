#!/usr/bin/env python3
"""curve.py — helpers CURVE para a malha ZeroMQ.

Modo: servidor (dispatcher) exige curve_server=True + server keys.
Clientes (workers, orquestrador) usam client keys + server_public.
Canal cifrado; apenas quem tem as chaves fala. Para autenticar hosts
especificos, estenda com zmq.auth (certificados por host).
"""
import os
import sys
import zmq

_sysdir = os.path.dirname(os.path.abspath(__file__))
if _sysdir not in sys.path:
    sys.path.insert(0, _sysdir)
import curve_keys as _k  # noqa: E402


def apply_server(sock):
    """Torna o socket um servidor CURVE (apos socket() e antes de bind)."""
    sock.curve_server = True
    sock.setsockopt_string(zmq.CURVE_SECRETKEY, _k.SERVER_SECRET)
    sock.setsockopt_string(zmq.CURVE_PUBLICKEY, _k.SERVER_PUBLIC)


def apply_client(sock):
    """Torna o socket um cliente CURVE (apos socket() e antes de connect)."""
    sock.setsockopt_string(zmq.CURVE_SECRETKEY, _k.CLIENT_SECRET)
    sock.setsockopt_string(zmq.CURVE_PUBLICKEY, _k.CLIENT_PUBLIC)
    sock.setsockopt_string(zmq.CURVE_SERVERKEY, _k.SERVER_PUBLIC)
