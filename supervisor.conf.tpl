[program:rolling_creatif]
numprocs = 1
numprocs_start = 1
process_name = rolling_creatif_%(process_num)s

command=/home/rolling/servers/creatif/venv3.10/bin/rolling-server --host 0.0.0.0 --port 7432 --sentry "https://x@x.ingest.sentry.io/x" server.ini --serve-static-files=./static
directory=/home/rolling/servers/creatif
user=rolling
autostart=true
autorestart=true
stderr_logfile=/home/rolling/servers/creatif/server.logs
stdout_logfile=/home/rolling/servers/creatif/server.logs
redirect_stderr=true