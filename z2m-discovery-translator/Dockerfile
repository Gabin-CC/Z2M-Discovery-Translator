FROM ghcr.io/home-assistant/base:latest

RUN apk add --no-cache \
    python3 \
    py3-paho-mqtt

COPY run.py /run.py
COPY translations /translations

# s6-overlay ne propage pas les variables Docker (dont SUPERVISOR_TOKEN) sans with-contenv.
CMD ["/usr/bin/with-contenv", "python3", "/run.py"]
