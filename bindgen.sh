#!/usr/bin/env bash
set -e

wasm-bindgen ../rollgui2/target/wasm32-unknown-unknown/release/rollgui2.wasm --out-dir static/ --out-name engine.wasm --target web --no-typescript
sed -i "s/import \* as __wbg_star1 from 'env';//" static/engine.js
sed -i "s/let wasm;/let wasm; export const set_wasm = (w) => wasm = w;/" static/engine.js
sed -i "s/imports\['env'\] = __wbg_star1;/return imports.wbg\;/" static/engine.js
