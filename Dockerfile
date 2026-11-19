ARG TARGETARCH
FROM ghcr.io/linuxserver/baseimage-selkies@sha256:0af93768720ccb685322aff1fecf0598ecce8a56405bed44839e43e8a5ffdba0 AS desktop-amd64
FROM ghcr.io/linuxserver/baseimage-selkies@sha256:cb0d9b32d7e46dd08be7a72e84ab0f0a1b041ddf21de1f42e624359e640a86be AS desktop-arm64
FROM desktop-${TARGETARCH}

ENV TITLE="Dev Workspace Desktop" \
    PIXELFLUX_WAYLAND=true \
    START_DOCKER=false \
    HARDEN_DESKTOP=true \
    DISABLE_SUDO=true \
    NO_GAMEPAD=true \
    NO_WEBCAM=true \
    SELKIES_PRINTING_ENABLED=false \
    SELKIES_COMMAND_ENABLED=false \
    SELKIES_FILE_TRANSFERS=none \
    SELKIES_ENABLE_CLIPBOARD=true \
    SELKIES_ALLOWED_ORIGINS="" \
    SELKIES_ENABLE_DUAL_MODE=false

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      gnome-keyring libsecret-1-0 python3-gi dbus-daemon libasound2t64 libxss1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -f /etc/ssl/private/ssl-cert-snakeoil.key /etc/ssl/certs/ssl-cert-snakeoil.pem

COPY assets/install-editor.py assets/editor-releases.json /usr/local/lib/dev-workspace-desktop/
COPY assets/workspace-connection.py assets/open-workspace.py /usr/local/lib/dev-workspace-desktop/
COPY assets/keyring.py /usr/local/lib/dev-workspace-desktop/
COPY assets/patch-selkies-keyboard.py /usr/local/lib/dev-workspace-desktop/
COPY assets/connect-workspace.txt /usr/local/share/dev-workspace-desktop/connect-workspace.txt
COPY assets/start-desktop /usr/local/bin/start-desktop
COPY assets/code /usr/local/bin/code
COPY assets/autostart /defaults/autostart
COPY assets/autostart /defaults/autostart_wayland
COPY assets/desktop-origin.conf /etc/nginx/desktop-origin.conf
RUN python3 -B /usr/local/lib/dev-workspace-desktop/patch-selkies-keyboard.py && \
    chmod 0755 /usr/local/bin/start-desktop /usr/local/bin/code && \
    sed -i '/^server {/a\  include /etc/nginx/desktop-origin.conf;' /defaults/default.conf

ENTRYPOINT ["/usr/local/bin/start-desktop"]
