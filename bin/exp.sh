#!/bin/bash

set -e

cd test

# d3-hierarchy
git clone https://github.com/d3/d3-hierarchy
pushd d3-hierarchy
git checkout 68c37131e536754a6f000e4530b1099611591f91 -b travioli_exp
npm install
cp node_modules/tape/bin/tape node_modules/tape/bin/tape.js
../../bin/run.sh node_modules/tape/bin/tape.js test/*/*test.js
popd

# d3-collection
git clone https://github.com/d3/d3-collection
pushd d3-collection
git checkout 44be4dcb5b425e0df8b28916c6d53d1f1090102a -b travioli_exp
npm install
cp node_modules/tape/bin/tape node_modules/tape/bin/tape.js
../../bin/run.sh node_modules/tape/bin/tape.js test/*test.js
popd

# express
git clone https://github.com/expressjs/express
pushd express
git checkout 3c54220a3495a7a2cdf580c3289ee37e835c0190 -b travioli_exp
npm install
cp node_modules/mocha/bin/_mocha node_modules/mocha/bin/_mocha.js
../../bin/run.sh node_modules/mocha/bin/_mocha.js --require test/support/env.js --reporter spec --bail test/*.js -t 60000
popd

# mathjs
git clone https://github.com/josdejong/mathjs 
pushd mathjs
git checkout cd9214727db6e811144e6a09f20c833119eb1a60 -b travioli_exp
npm install
cp node_modules/mocha/bin/_mocha node_modules/mocha/bin/_mocha.js
../../bin/run.sh node_modules/mocha/bin/_mocha.js test/type/matrix/*.test.js -t 60000
popd
