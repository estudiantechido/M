#!/usr/bin/env bash
# Arranca el despiece en esta máquina y abre el navegador.
set -euo pipefail
APP="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
URL="http://127.0.0.1:8765/"
DIR="$HOME/.local/share/muebles-melamina"
LOG="$DIR/servidor.log"
mkdir -p "$DIR"

if ! curl -fsS -o /dev/null --max-time 1 "$URL" 2>/dev/null; then
  setsid python3 "$APP/servidor.py" >>"$LOG" 2>&1 < /dev/null &
  ok=0
  for _ in $(seq 1 40); do
    if curl -fsS -o /dev/null --max-time 1 "$URL" 2>/dev/null; then
      ok=1
      break
    fi
    sleep 0.15
  done
  if [ "$ok" -ne 1 ]; then
    notify-send "Muebles de melamina" "No arrancó. El detalle está en $LOG" || true
    exit 1
  fi
fi

xdg-open "$URL" >/dev/null 2>&1 || true
