<IfModule mod_ssl.c>
<VirtualHost *:443>
    ServerName creatif.bux.fr

    ProxyPass / http://127.0.0.1:7432/
    RewriteEngine on
    RewriteCond %{HTTP:Upgrade} websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule ^/?(.*) "ws://127.0.0.1:7432/$1" [P,L]

    LogLevel warn
    CustomLog /var/log/apache2/creatif.bux.fr-access.log combined
    ErrorLog /var/log/apache2/creatif.bux.fr-error.log

SSLCertificateFile /etc/letsencrypt/live/creatif.bux.fr/fullchain.pem
SSLCertificateKeyFile /etc/letsencrypt/live/creatif.bux.fr/privkey.pem
Include /etc/letsencrypt/options-ssl-apache.conf
</VirtualHost>
</IfModule>
