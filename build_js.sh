#!/usr/bin/env bash
set -e

rm -f static/mq_js_bundle.js
# curl https://raw.githubusercontent.com/not-fl3/miniquad/afcfbabd4fcfdccf5b220334cbc102d854cded62/js/gl.js >> static/mq_js_bundle.js
# curl https://raw.githubusercontent.com/not-fl3/quad-snd/f1b04bb32c56073388d25a14bd762d810046ec39/js/audio.js >> static/mq_js_bundle.js
# curl https://raw.githubusercontent.com/not-fl3/sapp-jsutils/3dffa01d4cebac58eba37a15755ef20d21ca9d25/js/sapp_jsutils.js >> static/mq_js_bundle.js
# curl https://raw.githubusercontent.com/buxx/quad-net/d8e582c5001f977ec42e5f8dd21c1c0bbc9463e7/js/quad-net.js >> static/mq_js_bundle.js
curl https://raw.githubusercontent.com/not-fl3/egui-miniquad/82b6ac065b102c6a9181d4ad73594323e054dee2/docs/quad-url.js >> static/more.js
curl https://raw.githubusercontent.com/optozorax/quad-storage/3760b953aec17d65cc4ca8edfa39c38e7337ec3a/js/quad-storage.js >> static/more.js

# sed -i 's/js_objects = {}/var js_objects = {}/' static/mq_js_bundle.js
# sed -i 's/unique_js_id = 0/var unique_js_id = 0/' static/mq_js_bundle.js
# sed -i 's/params_set_mem = function/var params_set_mem = function/' static/mq_js_bundle.js
# sed -i 's/params_register_js_plugin = function/var params_register_js_plugin = function/' static/mq_js_bundle.js