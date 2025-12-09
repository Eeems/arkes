# syntax=docker/dockerfile:1.4
# x-name=Base
# x-depends=rootfs
# x-templates=slim
ARG HASH

FROM arkes:rootfs

RUN /usr/lib/system/package_layer \
  base \
  nano \
  micro \
  sudo-rs \
  tmux \
  less \
  htop \
  fastfetch \
  bluez \
  broadcom-wl-dkms \
  linux-firmware \
  linux-zen \
  linux-zen-headers \
  networkmanager \
  fuse-overlayfs \
  podman \
  efibootmgr \
  grub \
  flatpak \
  ostree \
  xorriso \
  mtools \
  rsync \
  dmidecode \
  squashfs-tools \
  btrfs-progs \
  e2fsprogs \
  exfatprogs \
  ntfs-3g \
  xfsprogs \
  dosfstools \
  git \
  fakeroot \
  debugedit \
  terminus-font \
  pv \
  nvme-cli \
  run-parts \
  skopeo \
  pacman-contrib \
  python-pyxattr \
  python-requests \
  python-dbus \
  distrobox \
  xdelta3 \
  && rm /usr/bin/su \
  && ln -s /usr/bin/su{-rs,} \
  && ln -s /usr/bin/sudo{-rs,} \
  && ln -s /usr/bin/visudo{-rs,} \
  && chmod u+s /usr/bin/new{u,g}idmap \
  && rm /etc/containers/storage.conf

COPY overlay/base /

# install_aur_packages is part of the overlay
RUN cp /{usr/share,etc}/containers/storage.conf \
  &&mkdir /var/home \
  && /usr/lib/system/package_layer \
  --aur \
  localepurge \
  python-podman \
  && rmdir /var/home

RUN systemctl enable \
  NetworkManager \
  bluetooth \
  podman \
  atomic-state-overlay \
  os-daemon \
  os-checkupdates.timer \
  systemd-timesyncd \
  && mkdir -p /var/lib/system \
  && chmod 400 /etc/sudoers \
  && chmod 644 /etc/pam.d/sudo{,-i}
