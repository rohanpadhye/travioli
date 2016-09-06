#!/bin/bash

if [ "$#" -ge 1 ]; then
  PATTERN="ag_$1.dot"
else
  PATTERN="ag_*.dot"
fi

for ag in $(ls $PATTERN); do
	echo -n "Rendering access graph: ${ag%%.*}..."
	dot -Tpng -o "${ag%%.*}.png" "${ag%%.*}.dot"
	dot -Tpdf -o "${ag%%.*}.pdf" "${ag%%.*}.dot"
	echo " Done!"
done
