#!/usr/bin/env bash
# agentmesh_mcp_launcher.sh — launcher do servidor MCP da malha.
# Permite registrar no Hermes via `command` unico (sem `args` lista, que o
# `hermes config set` nao aceita). Hereda AGENTMESH_TARGET do env do mcp_servers.
exec "$(dirname "$0")/venv/bin/python" "$(dirname "$0")/agentmesh_mcp.py" "$@"
