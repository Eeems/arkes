# syntax=docker/dockerfile:1.4
ARG BASE_VARIANT_ID

FROM arkes:${BASE_VARIANT_ID} AS build

RUN /usr/lib/system/initialize_pacman \
  && echo "[system] Installing bleachbit" \
  && mkdir -p /var/roothome/.config \
  && chronic pacman -S --noconfirm bleachbit \
  && echo "[system] Running bleachbit" \
  && chronic bleachbit --clean \
  system.cache \
  system.custom \
  system.desktop_entry \
  system.localizations \
  system.recent_documents \
  system.rotated_logs \
  system.tmp \
  system.trash \
  && echo "[system] Removing bleachbit" \
  && chronic pacman -R --noconfirm bleachbit \
  && echo "[system] Removing orphaned packages" \
  && pacman -Qqd | chronic pacman -Rsu --noconfirm - \
  && /usr/lib/system/remove_pacman_files \
  && echo "[system] Removing unneeded files from /usr" \
  && chronic find /usr/lib -name '.a' -exec rm -v {} \; \
  && chronic rm -rf \
  /usr/{include,share/{doc,info,man}} \
  /usr/lib/python*/test \
  && chronic find /usr/lib/python* -name '*.pyo' -exec rm -v {} \;

FROM scratch

COPY --from=build / /
