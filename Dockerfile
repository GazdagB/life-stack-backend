FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system lifeos \
    && useradd --system --gid lifeos --home-dir /app lifeos

COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt

COPY . .
RUN chmod +x /app/docker-entrypoint.sh \
    && chown -R lifeos:lifeos /app

USER lifeos
EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
