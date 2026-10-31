FROM nginx:alpine

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy static website files and manifests
COPY index.html favicon.ico favicon.svg robots.txt sitemap.xml llms.txt /usr/share/nginx/html/
COPY assets/ /usr/share/nginx/html/assets/
COPY .well-known /usr/share/nginx/html/.well-known/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
