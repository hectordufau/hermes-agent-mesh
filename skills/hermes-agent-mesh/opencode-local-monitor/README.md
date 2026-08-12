# OpenCode Free-Limit Monitor — implantação LOCAL por host

Monitoramento de limite diário da API do OpenCode. **Local e independente por
host**: não usa rede, ZMQ, nem coordenação central. Cada host Hermes que roda
opcode instala a sua própria cópia.

## O que é
- `opencode_run.sh` — wrapper que roda `opencode` e, ao detectar mensagem de
  limite de API no stdout, mata o processo e sai com código **42**.
- `opencode-free-limit-monitor/SKILL.md` — skill que instrui o Hermes a sempre
  lançar o opencode via wrapper e a reagir a 42 (pausar, aguardar "retomar").

## Implantar num host (orquestrador, Acer, ou qualquer outro)
```bash
bash install.sh
```
Idempotente. Usa `$HOME`, então funciona em qualquer usuário/home.

## Usar
```bash
bash ~/.hermes/scripts/opencode_run.sh run '<prompt>' --agent build --title '...'
```
Saída:
- `0`  → opencode terminou normalmente (verifique evidências antes de prosseguir)
- `42` → limite diário atingido → PARE, não dispare próxima fase, aguarde "retomar"

## Em malha multi-host (orquestrador + Acer + N)
Implantar em **todos** os hosts. O orquestrador NÃO monitora o opencode do Acer
remotamente — cada host vigia o seu. A orquestração (ZMQ, etc.) cuida do
roteamento de tarefas; este monitor cuida só do limite local do opencode.

## Desinstalar
```bash
rm -f ~/.hermes/scripts/opencode_run.sh
rm -rf ~/.hermes/skills/software-development/opencode-free-limit-monitor
```
