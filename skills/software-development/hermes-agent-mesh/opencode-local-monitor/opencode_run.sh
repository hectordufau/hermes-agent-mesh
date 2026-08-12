#!/usr/bin/env bash
# opencode_run.sh — roda `opencode` com monitoramento de limite de API.
#
# Problema que resolve: o opencode atinge o limite diário da API e estagna
# (ou imprime "Free usage exceeded" e fica aguardando). Sem monitoramento, o
# agente Hermes não percebe e deixa a fase rodando/ociosa.
#
# Solução: este wrapper captura o stdout do opencode e roda um watcher em
# paralelo que detecta a mensagem de limite. Ao detectar, MATA o opencode e
# sai com código 42, de modo que o Hermes recebe a notificação de término e
# interpreta 42 como "limite atingido -> pausar e aguardar 'retomar'".
#
# Uso:  bash opencode_run.sh run '<prompt>' --agent build --title '...'
#       (todos os args são repassados ao opencode)
#
# USO LOCAL: este script roda no PRÓPRIO host onde o opencode é executado.
# Não depende de rede, ZMQ, nem de nenhum outro Hermes. Cada host vigia o
# seu próprio opencode de forma independente.

set -u

OPENCODE_BIN="${OPENCODE_BIN:-$HOME/.opencode/bin/opencode}"
OUT="$(mktemp /tmp/opencode_out.XXXXXX.log)"
LIMIT_FLAG="$(mktemp /tmp/opencode_limit.XXXXXX.flag)"

# Padrões que indicam limite de API / rate limit. Defensivo: falso positivo
# apenas causa uma pausa antecipada (o usuário retoma), o que é aceitável.
PAT='usage exceeded|free usage|rate[ -]limit|[^0-9]429|too many requests|quota|limit reached|daily limit|upgrade to continue|retry in|try again later|exceeded your|usage limit'

# Inicia o opencode capturando tudo (stdout+stderr) para o arquivo de log.
"$OPENCODE_BIN" "$@" >"$OUT" 2>&1 &
OC=$!

# Watcher: monitora o log em tempo real, strip de ANSI, e sai na 1ª ocorrência.
(
  tail -F -n0 "$OUT" 2>/dev/null \
    | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' \
    | grep -m1 -iE "$PAT" >/dev/null 2>&1
  touch "$LIMIT_FLAG"
  kill -TERM "$OC" 2>/dev/null
) &
WATCH=$!

# Espera o opencode terminar (normalmente ou morto pelo watcher).
wait "$OC"; RC=$?
kill -TERM "$WATCH" 2>/dev/null

if [ -f "$LIMIT_FLAG" ]; then
  echo "OPENCODE_LIMIT_REACHED: opencode atingiu o limite diário de API e foi interrompido automaticamente." >&2
  echo "AÇÃO: o Hermes deve PAUSAR e aguardar 'retomar' (próximo dia ou ordem do usuário). Não disparar próxima fase." >&2
  echo "--- últimas linhas do opencode ---" >&2
  tail -15 "$OUT" >&2
  rm -f "$OUT" "$LIMIT_FLAG"
  exit 42
fi

rm -f "$OUT" "$LIMIT_FLAG"
exit $RC
