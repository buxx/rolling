#!/usr/bin/env bash
set -e

rm -f static/mq_js_bundle.js
curl https://raw.githubusercontent.com/not-fl3/miniquad/v0.3.0-alpha.43/native/sapp-wasm/js/gl.js >> static/mq_js_bundle.js
curl https://raw.githubusercontent.com/not-fl3/quad-snd/f1b04bb32c56073388d25a14bd762d810046ec39/js/audio.js >> static/mq_js_bundle.js
curl https://raw.githubusercontent.com/not-fl3/sapp-jsutils/a871b9eac1390dfdc1098f4be0d7dc673a1480ad/js/sapp_jsutils.js >> static/mq_js_bundle.js
curl https://raw.githubusercontent.com/buxx/quad-net/d8e582c5001f977ec42e5f8dd21c1c0bbc9463e7/js/quad-net.js >> static/mq_js_bundle.js
