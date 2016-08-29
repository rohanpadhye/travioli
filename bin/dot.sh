#!/bin/bash

if [ "$#" -lt 1 ]; then
  echo "USAGE: $0 ID " >&2
  exit 1
fi

ID="$1"
dot -Tpng -o "ag_$ID.png" "ag_$ID.dot"
