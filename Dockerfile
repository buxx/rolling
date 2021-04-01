FROM debian:10

RUN \
    apt-get update \
    && apt-get upgrade -qy \
    && apt-get install -qy \
        git \
        locales \
        python3 \
        curl \
        build-essential \
        libjpeg-dev \
        python3-dev \
        python3-pip \
        postgresql-server-dev-11

RUN mkdir /rolling
COPY requirements.txt /rolling/requirements.txt

RUN pip3 install --upgrade pip setuptools
RUN cd /rolling && pip3 install -r requirements.txt

COPY rolling /rolling/rolling
COPY guilang /rolling/guilang
COPY setup.py /rolling/setup.py
COPY server.ini.tpl /game/server.ini

RUN cd /rolling && python3 setup.py install

VOLUME ["/game", "/zones", "/world", "/db"]
EXPOSE 5000
CMD ["/usr/local/bin/rolling-server","--host", "0.0.0.0", "--port", "5000", "--server-db-path", "/db/server.db", "/world/map.txt", "/zones", "/game", "/game/server.ini"]
