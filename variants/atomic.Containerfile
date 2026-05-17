# syntax=docker/dockerfile:1.4
# x-name=Atomic
# x-depends=base
# x-templates=nvidia
ARG HASH

FROM arkes:base

RUN /usr/lib/system/package_layer \
  adw-gtk-theme \
  awww \
  bluez-utils \
  brightnessctl \
  cups \
  cups-pdf \
  dex \
  flatpak-xdg-utils \
  fuzzel \
  fwupd \
  gamescope \
  ghostty \
  gnome-disk-utility \
  gnome-keyring \
  gnome-power-manager \
  gnome-software \
  greetd-tuigreet \
  hypridle \
  hyprlock \
  libnotify \
  nautilus \
  networkmanager-dmenu \
  niri \
  nm-connection-editor \
  noto-fonts-cjk \
  noto-fonts-emoji \
  nwg-clipman \
  pipewire-audio \
  pipewire-pulse \
  polkit-gnome \
  power-profiles-daemon \
  python-numpy \
  swaync \
  system-config-printer \
  ttf-dejavu-nerd \
  ttf-roboto-mono-nerd \
  vulkan-swrast \
  waybar \
  xdg-desktop-portal-gnome \
  xwayland-satellite \
  --aur \
  python-imageio-ffmpeg \
  python-screeninfo \
  waypaper \
  syshud \
  overskride \
  distroshelf \
  libwireplumber-4.0-compat \
  pwvucontrol \
  wego \
  prelockd \
  --rm \
  distroshelf-debug \
  libwireplumber-4.0-compat-debug \
  overskride-debug \
  syshud-debug \
  wego-debug

RUN <<EOT
  set -e
  echo "[system] Symlinking awww -> swww"
  ln -s /usr/bin/awww /usr/bin/swww
  ln -s /usr/bin/awww-daemon /usr/bin/swww-daemon
EOT

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
