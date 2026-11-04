FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY index.html favicon.ico favicon.svg robots.txt sitemap.xml llms.txt schema_org_snippet.html /usr/share/nginx/html/
COPY assets/ /usr/share/nginx/html/assets/
COPY docs/ /usr/share/nginx/html/docs/
COPY health/ /usr/share/nginx/html/health/
COPY packs/ /usr/share/nginx/html/packs/
COPY sample-packs/ /usr/share/nginx/html/sample-packs/
COPY .well-known/ /usr/share/nginx/html/.well-known/
COPY generated-packs/ /app/generated-packs/

COPY nginx-docker.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh \
    && mkdir -p /app/generated-packs

ENV PYTHONPATH=/app

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1/health || exit 1

CMD ["/docker-entrypoint.sh"]
