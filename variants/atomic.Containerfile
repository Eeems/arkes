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
  --aur \
  python-imageio-ffmpeg \
  python-screeninfo \
  waypaper \
  syshud \
  overskride \
  networkmanager-dmenu-git \
  distroshelf \
  libwireplumber-4.0-compat \
  pwvucontrol \
  wego \
  prelockd

RUN systemctl enable \
  greetd.service \
  udisks2.service \
  cups.socket

COPY overlay/atomic /

RUN systemctl enable \
  dconf.service \
  prelockd.service
