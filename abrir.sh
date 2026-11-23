#!/usr/bin/env bash
# Arranca el despiece en esta máquina y abre el navegador.
set -euo pipefail
APP="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
URL="http://127.0.0.1:8765/"
DIR="$HOME/.local/share/muebles-melamina"
LOG="$DIR/servidor.log"
PID="$DIR/servidor.pid"
FIRMA="$DIR/servidor.sha"
mkdir -p "$DIR"

fingerprint() {
  (cd "$APP" && sha256sum abrir.sh servidor.py pagina.py despiece.py pdf_zoclo.py vista.js estilo.css icono.png 2>/dev/null | sha256sum | cut -d" " -f1)
}

pid_servidor() {
  if [ -s "$PID" ]; then
    cat "$PID"
  fi
}

pid_es_servidor() {
  local pid="$1"
  [ "$pid" -gt 0 ] 2>/dev/null || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  tr "\0" " " <"/proc/$pid/cmdline" 2>/dev/null | grep -F "$APP/servidor.py" >/dev/null
}

detener_servidor() {
  local pid
  pid="$(pid_servidor)"
  if [ -n "$pid" ] && pid_es_servidor "$pid"; then
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 20); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.05
    done
  fi

  for pid in $(ss -ltnp "sport = :8765" 2>/dev/null | sed -n 's/.*pid=\([0-9][0-9]*\).*/\1/p' | sort -u); do
    if pid_es_servidor "$pid"; then
      kill "$pid" 2>/dev/null || true
      for _ in $(seq 1 20); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.05
      done
    fi
  done
  rm -f "$PID"
}

FIRMA_ACTUAL="$(fingerprint)"
FIRMA_PREVIA=""
[ -s "$FIRMA" ] && FIRMA_PREVIA="$(cat "$FIRMA")"
PID_ACTUAL="$(pid_servidor)"

if [ -n "$PID_ACTUAL" ] && pid_es_servidor "$PID_ACTUAL" && curl -fsS -o /dev/null --max-time 1 "$URL" 2>/dev/null && [ "$FIRMA_ACTUAL" = "$FIRMA_PREVIA" ]; then
  :
else
  detener_servidor
  : >"$LOG"
  setsid python3 "$APP/servidor.py" >>"$LOG" 2>&1 < /dev/null &
  PID_NUEVO="$!"
  echo "$PID_NUEVO" >"$PID"
  ok=0
  for _ in $(seq 1 40); do
    if curl -fsS -o /dev/null --max-time 1 "$URL" 2>/dev/null; then
      ok=1
      break
    fi
    if ! kill -0 "$PID_NUEVO" 2>/dev/null; then
      break
    fi
    sleep 0.15
  done
  if [ "$ok" -ne 1 ]; then
    rm -f "$PID"
    notify-send "Muebles de melamina" "No arrancó. El detalle está en $LOG" || true
    exit 1
  fi
  echo "$FIRMA_ACTUAL" >"$FIRMA"
fi

xdg-open "$URL" >/dev/null 2>&1 || true
