FROM python:3.11-slim

# Create non-root sandbox user
RUN groupadd -g 1000 sandbox && \
    useradd -u 1000 -g sandbox -m -s /bin/bash sandbox

# Set deterministic environment defaults
ENV PYTHONHASHSEED=0 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    TZ=UTC

WORKDIR /home/sandbox
USER 1000:1000

COPY --chown=1000:1000 docker/entrypoint.py /entrypoint.py

ENTRYPOINT ["python3", "/entrypoint.py"]
