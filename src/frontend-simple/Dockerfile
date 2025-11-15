FROM node:20-alpine

RUN set -ex; \
    apk update && \
    apk add --no-cache bash && \
    npm install -g http-server && \
    mkdir -p /app
EXPOSE 8080

# Switch to app
WORKDIR /app

ADD --chown=app:app . /app

ENTRYPOINT ["/bin/bash"]