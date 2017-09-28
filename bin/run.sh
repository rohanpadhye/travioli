#!/bin/bash

TRAVIOLI_DIR="$(dirname $0)/.."

# Set python runtime
if [ -z "$PYTHON" ]; then
  if which pypy > /dev/null; then
    export PYTHON="pypy"
  else
    export PYTHON="python"
  fi
fi

# Set JS runtime
if [ -z "$NODEJS" ]; then
  export NODEJS="node"
fi

# Set directories for travioli to exlude
if [ -z "$TRAVIOLI_EXCLUDE_PATTERN" ]; then
  export TRAVIOLI_EXCLUDE_PATTERN="node_modules/|perf/|test/"
fi

"$NODEJS" $@ &&
"$TRAVIOLI_DIR/bin/collect_trace.sh" "$TRAVIOLI_DIR/node_modules/jalangi2" $@ &&
"$PYTHON" "$TRAVIOLI_DIR/src/py/readtrace.py" && 
tail -3 ".travioli/traversals.out"

