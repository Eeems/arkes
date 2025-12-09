# syntax=docker/dockerfile:1.4
ARG HASH
ARG BASE_VARIANT_ID

FROM arkes:${BASE_VARIANT_ID}

RUN /usr/lib/system/add_pacman_repository \
  --key=A64228CCD26972801C2CE6E3EC931EA46980BA1B \
  --server=https://repo.eeems.website/\$repo \
  --server=https://repo.eeems.codes/\$repo \
  eeems-system76 \
  && /usr/lib/system/remove_pacman_files

RUN /usr/lib/system/package_layer \
  system76-driver \
  system76-dkms-git \
  system76-acpi-dkms \
  system76-io-dkms \
  system76-power \
  system76-scheduler \
  system76-keyboard-configurator \
  firmware-manager

RUN systemctl enable \
  system76 \
  system76-firmware-daemon \
  com.system76.PowerDaemon \
  com.system76.Scheduler

COPY overlay/system76 /
