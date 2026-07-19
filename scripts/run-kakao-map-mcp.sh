#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${KAKAO_API_KEY:-}" ]]; then
  echo "KAKAO_API_KEY is required for kakao-map MCP." >&2
  exit 1
fi

repo_url="https://github.com/cgoinglove/mcp-server-kakao-map.git"
cache_root="${XDG_CACHE_HOME:-$HOME/.cache}/neo"
server_dir="$cache_root/mcp-server-kakao-map"

mkdir -p "$cache_root"

if [[ ! -d "$server_dir/.git" ]]; then
  git clone --depth 1 "$repo_url" "$server_dir" >&2
else
  git -C "$server_dir" fetch --depth 1 origin main >&2
  git -C "$server_dir" reset --hard origin/main >&2
fi

cd "$server_dir"

if [[ ! -d node_modules ]]; then
  npm install --ignore-scripts >&2
fi

npm run build >&2
exec node dist/index.js
