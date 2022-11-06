<VirtualHost *:80>
    ServerName rolling.local

    # Tracim
    ProxyPass /assets http://127.0.0.1:8080/assets
    ProxyPassReverse /assets http://127.0.0.1:8080/assets
    ProxyPass /app http://127.0.0.1:8080/app
    ProxyPassReverse /app http://127.0.0.1:8080/app
    ProxyPass /api http://127.0.0.1:8080/api
    ProxyPassReverse /api http://127.0.0.1:8080/api
    ProxyPass /ui http://127.0.0.1:8080/ui
    ProxyPassReverse /ui http://127.0.0.1:8080/ui

    # Rolling
    ProxyPass / http://127.0.0.1:5000/
    ProxyPassReverse / http://127.0.0.1:5000/
    # Require a2enmod proxy_wstunnel
    RewriteEngine on
    RewriteCond %{HTTP:Upgrade} websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule ^/?(.*) "ws://127.0.0.1:5000/$1" [P,L]

    LogLevel warn
    CustomLog /var/log/apache2/rolling.local-access.log combined
    ErrorLog /var/log/apache2/rolling.local-error.log
</VirtualHost>
