# syntax=docker/dockerfile:1.4
# x-name=Atomic
# x-depends=base
# x-templates=nvidia
ARG HASH

FROM arkes:base

RUN /usr/lib/system/package_layer \
  ghostty \
  gnome-software \
  flatpak-xdg-utils \
  fwupd \
  greetd-tuigreet \
  niri \
  xdg-desktop-portal-gnome \
  xwayland-satellite \
  gnome-keyring \
  nautilus \
  power-profiles-daemon \
  python-numpy \
  pipewire-audio \
  pipewire-pulse \
  swww \
  hyprlock \
  hypridle \
  gamescope \
  vulkan-swrast \
  ttf-roboto-mono-nerd \
  noto-fonts-emoji \
  noto-fonts-cjk \
  adw-gtk-theme \
  swaync \
  nwg-clipman \
  libnotify \
  waybar \
  fuzzel \
  brightnessctl \
  nm-connection-editor \
  gnome-power-manager \
  gnome-disk-utility \
  polkit-gnome \
  bluez-utils \
  system-config-printer \
  dex \
  cups \
  cups-pdf \
  networkmanager-dmenu \
  --aur \
  python-kdl-py \
  python-imageio-ffmpeg \
  python-screeninfo \
  waypaper \
  syshud \
  overskride \
  distroshelf \
  libwireplumber-4.0-compat \
  pwvucontrol \
  wego \
  prelockd

RUN <<EOT
  set -e
  curl -L https://github.com/Eeems/niricfg/releases/download/0.0.1/niricfg.tar.gz -o /tmp/niricfg.tar.gz
  echo "438bce30d8a68a54042771a779dbc319109ff59d482a335e0bd538f2f892050d  /tmp/niricfg.tar.gz" | sha256sum -c
  mkdir -p /opt/niricfg
  tar xf /tmp/niricfg.tar.gz -C /opt/niricfg
  rm /tmp/niricfg.tar.gz
  chmod +x /opt/niricfg/niricfg
  echo "[Desktop Entry]" > /usr/share/applications/niricfg.desktop
  echo "Name=Display Settings" >> /usr/share/applications/niricfg.desktop
  echo "Exec=/opt/niricfg/niricfg" >> /usr/share/applications/niricfg.desktop
  echo "Terminal=false" >> /usr/share/applications/niricfg.desktop
  echo "Type=Application" >> /usr/share/applications/niricfg.desktop
  echo "Categories=System;Settings;HardwareSettings;GTK;" >> /usr/share/applications/niricfg.desktop
EOT

RUN systemctl enable \
  greetd.service \
  udisks2.service \
  cups.socket

COPY overlay/atomic /

RUN systemctl enable \
  dconf.service \
  prelockd.service
