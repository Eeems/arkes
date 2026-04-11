# syntax=docker/dockerfile:1.4
# x-name=Atomic
# x-depends=base
# x-templates=nvidia
ARG HASH

FROM ghcr.io/eeems/arkes:base_2026.03.13 as pwvucontrol

RUN <<EOT
  /usr/lib/system/initialize_pacman
  mkdir /var/home

  /usr/lib/system/install_aur_packages libwireplumber-4.0-compat
  echo "[system] Installing fakeroot debugedit pkg-config"
  chronic pacman -Syu --asdeps --needed --noconfirm fakeroot debugedit pkg-config
  chronic useradd -m aur
  chronic passwd -d aur
  echo "aur ALL=(ALL:ALL) NOPASSWD: ALL" >/etc/sudoers.d/aur
  chronic sudo -u aur git clone \
    --branch pwvucontrol \
    --single-branch \
    https://github.com/archlinux/aur.git \
    /tmp/src
  cd /tmp/src
  sudo -u aur chronic makepkg \
    --noconfirm \
    --needed \
    --syncdeps \
    --install
  rm pwvucontrol-debug-*.pkg.tar.zst
  mv pwvucontrol-*.pkg.tar.zst /pwvucontrol.pkg.tar.zst

  cd ..
  chronic rm -r src
  chronic rm /etc/sudoers.d/aur
  chronic userdel aur
  chronic rm -r /home/aur
  /usr/lib/system/remove_unused_packages
  rmdir /var/home
  /usr/lib/system/remove_pacman_files
EOT

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
  awww \
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
  python-imageio-ffmpeg \
  python-screeninfo \
  waypaper \
  syshud \
  overskride \
  distroshelf \
  libwireplumber-4.0-compat \
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

RUN --mount=target=/mnt,from=pwvucontrol,src=/ <<EOT
  set -e
  /usr/lib/system/initialize_pacman
  echo "[system] Installing pwvucontrol"
  chronic pacman -U --needed --noconfirm /mnt/pwvucontrol.pkg.tar.zst
  /usr/lib/system/remove_pacman_files
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
