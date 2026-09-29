#!/bin/sh
set -eu
for value in "$LOGIN_NGINX_RATE_PER_SECOND" "$LOGIN_NGINX_BURST"; do
    case "$value" in
        ''|*[!0-9]*) echo "INVALID_LOGIN_NGINX_LIMIT" >&2; exit 1 ;;
    esac
    if [ "$value" -lt 1 ] || [ "$value" -gt 1000 ]; then
        echo "INVALID_LOGIN_NGINX_LIMIT" >&2
        exit 1
    fi
done
envsubst '${LOGIN_NGINX_RATE_PER_SECOND} ${LOGIN_NGINX_BURST}' \
    < /etc/nginx/nginx.conf.template > /tmp/nginx.conf
exec nginx -c /tmp/nginx.conf -g 'daemon off;'
