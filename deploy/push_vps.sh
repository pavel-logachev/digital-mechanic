#!/usr/bin/env bash
# Выкладка текущего коммита на стенд (VPS с алиасом ssh pavel-production-vps). .env и данные на сервере не трогаются.
set -euo pipefail
cd "$(dirname "$0")/.."
HOST=${HOST:-pavel-production-vps}
DIR=${DIR:-/home/deploy/iikuznitsa/digital-mechanic}
TMP=$(mktemp -d)
git archive --format=tar.gz -o "$TMP/dm.tgz" HEAD
scp -q "$TMP/dm.tgz" "$HOST:$DIR/../dm.tgz"
rm -rf "$TMP"
ssh -o BatchMode=yes "$HOST" "cd $DIR && tar -xzf ../dm.tgz && rm ../dm.tgz && \
  docker compose -p mechanic -f docker-compose.yml -f deploy/compose.vps.yml up -d --build 2>&1 | tail -3 && \
  sleep 20 && docker ps --format '{{.Names}} {{.Status}}' | grep mechanic"
curl -fsS -m 20 https://mechanic.logachev.net/api/health && echo
