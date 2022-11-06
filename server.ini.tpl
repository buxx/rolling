[default]
base_url = http://rolling.local
allow_origin = http://rolling.local
rp_url = http://rolling.local/ui/
disable_auth_token = __CHANGE_THIS_SECURITY_TOKEN__
sender_email = xxxxx@xxxxx.xxx
smtp_server = xxxxxxxxxx
smtp_port = 587
smtp_user = xxxxxxxxx
smtp_password = xxxxxxxxx
db_user = rolling
db_name = rolling
db_password = rolling
db_address = 127.0.0.1:5432
avatars_folder_path = ./avatars
loading_folder_path = ./loadings
anonymous_media_file_name = anonymous.png
admin_login = admin
# CHANGE THIS PASSWORD !
admin_password = admin
name = Rolling

# Path must be relative to this config file or absolute
game=./game
worldmap=./worldmap.txt
zones=./zones

[tracim]
api_address=https://127.0.0.1:8080/api/
api_key=xxxxxxxxxxxxxxxxxxxxxxxx
admin_email=admin@admin.admin
# tracim_common_spaces=42:reader,442:contributor
tracim_common_spaces=
