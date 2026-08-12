#!/usr/bin/env bash
# install.sh — implanta o monitoramento LOCAL do OpenCode neste host.
#
# Idempotente: roda quantas vezes quiser, não quebra o que já existe.
# Usa $HOME, então funciona independente do usuário/home do host.
#
# Uso:  bash install.sh
# (execute no Acer, no orquestrador, ou em qualquer host Hermes que rode opencode)

set -u

SRC="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$HOME/.hermes/skills/software-development/opencode-free-limit-monitor"
SCRIPT_DIR="$HOME/.hermes/scripts"
SCRIPT_DST="$SCRIPT_DIR/opencode_run.sh"

mkdir -p "$SKILL_DIR" "$SCRIPT_DIR"

# 1) Skill
cp "$SRC/SKILL.md" "$SKILL_DIR/SKILL.md"

# 2) Wrapper
cp "$SRC/opencode_run.sh" "$SCRIPT_DST"
chmod +x "$SCRIPT_DST"

# 3) Sanidade: opencode presente?
OC_BIN="${OPENCODE_BIN:-$HOME/.opencode/bin/opencode}"
if [ -x "$OC_BIN" ]; then
  echo "OK: opencode encontrado em $OC_BIN"
else
  echo "AVISO: opencode nao encontrado em $OC_BIN (defina OPENCODE_BIN se estiver noutro lugar)"
fi

echo "Implantado:"
echo "  skill : $SKILL_DIR/SKILL.md"
echo "  script: $SCRIPT_DST (executavel)"
echo
echo "Teste rapido (nao dispara fase real):"
echo "  bash $SCRIPT_DST --help"
