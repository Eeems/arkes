# syntax=docker/dockerfile:1.4
ARG HASH
ARG BASE_VARIANT_ID

FROM arkes:${BASE_VARIANT_ID}

RUN /usr/lib/system/package_layer \
  fprintd \
  framework-system \
  usbutils

COPY overlay/framework /

RUN <<EOT
if [ -f /usr/share/hypr/hypridle.conf ]; then
  cat >/usr/lib/system/niri-resume-vrr-fix <<'EOF'
#!/bin/sh
if ! pgrep -x niri >/dev/null 2>&1; then
  echo "niri-resume-vrr-fix: skipping - Niri not running" >&2
  exit 0
fi
vrr_was_on=$(niri msg -j outputs 2>/dev/null | jq -r '.[] | select(.name == "eDP-1") | .vrr_enabled' 2>/dev/null | grep -qx true && echo 1 || echo 0)
if [ "$vrr_was_on" = 0 ]; then
  echo "niri-resume-vrr-fix: skipping - VRR not enabled" >&2
  exit 0
fi
echo "niri-resume-vrr-fix: vrr_was_on=$vrr_was_on" >&2
niri msg output eDP-1 off
niri msg output eDP-1 vrr off
niri msg output eDP-1 on
niri msg output eDP-1 vrr on
echo "niri-resume-vrr-fix: done" >&2
EOF
  chmod 0755 /usr/lib/system/niri-resume-vrr-fix
  sed -i 's|^after_sleep_cmd = .*|after_sleep_cmd = /usr/lib/system/niri-resume-vrr-fix \&\& os display on|' /usr/share/hypr/hypridle.conf
fi
EOT
