#!/usr/bin/env bash

sudo su -c "psql -lqt | cut -d \| -f 1 | grep -qw rolling" postgres

if [ "$?" -eq "0" ]; then
    read -p "Postgresql database \"rolling\" will be deleted, continue ? (y/n) " -n 1 -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]
    then
        [[ "$0" = "$BASH_SOURCE" ]] && exit 1 || return 1
    fi

    echo ""
    sudo su -c "psql -c \"DROP DATABASE rolling\"" postgres
fi

sudo su -c "psql -c \"CREATE DATABASE rolling\"" postgres

sudo su -c "psql postgres -tAc \"SELECT 1 FROM pg_roles WHERE rolname='rolling'\" | grep -q 1" postgres
if [ "$?" -eq "0" ]; then
    sudo su -c "psql -c \"ALTER USER rolling WITH PASSWORD 'rolling'\"" postgres
else
    sudo su -c "psql -c \"CREATE USER rolling WITH PASSWORD 'rolling'\"" postgres
fi

sudo su -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE rolling TO rolling\"" postgres

# stamp database head with alembic
alembic stamp head

echo "WARNING : nee to sync resource docs with command 'rolling-server-manage sync-zone-resources'"