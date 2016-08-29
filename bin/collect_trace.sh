#!/bin/bash

TRAVIOLI_DIR="$(dirname $0)/.."
JALANGI_DIR="$1"

# Set JS runtime
node="node"

if [ $# -lt 2 ]; then
  echo "Usage: $0 JALANGI_DIR JS_FILE [ARGS]" >&2
  exit 1
fi

mkdir -p "travioli"
node "$JALANGI_DIR/src/js/commands/jalangi.js" --inlineIID --inlineSource --analysis "$JALANGI_DIR/src/js/sample_analyses/ChainedAnalyses.js" --analysis "$JALANGI_DIR/src/js/runtime/SMemory.js" --analysis "$TRAVIOLI_DIR/src/js/LogData.js" "${@:2}"
