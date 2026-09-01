# syntax=docker/dockerfile:1.4
# x-name=Base
# x-depends=rootfs
# x-templates=slim,rolling
ARG HASH
ARG CLOVER_VERSION=5174
ARG CLOVER_ISO_SHA256=50c546054dd9b2ff973c02617670ea4bc4dc8920749abc0ee5ab8e3045778942

FROM arkes:rootfs AS clover

ARG CLOVER_VERSION
ARG CLOVER_ISO_SHA256

RUN /usr/lib/system/package_layer \
  curl \
  libarchive

RUN <<EOT
  set -e
  mkdir -p /clover
  cd /clover
  curl -fL -o Clover.iso.7z \
    "https://github.com/CloverHackyColor/CloverBootloader/releases/download/${CLOVER_VERSION}/Clover-${CLOVER_VERSION}-X64.iso.7z"
  echo "${CLOVER_ISO_SHA256}  Clover.iso.7z" | sha256sum --check -
  bsdtar -xf Clover.iso.7z
  bsdtar -xf "Clover-${CLOVER_VERSION}-X64.iso" \
    'EFI/CLOVER' \
    'usr/standalone/i386'
  rm -f Clover.iso.7z "Clover-${CLOVER_VERSION}-X64.iso"
  mv usr/standalone/i386/cdboot /clover/cdboot
  mv usr/standalone/i386 /clover/i386
  mv EFI/CLOVER /clover/CLOVER
  rm -rf EFI usr
EOT

FROM arkes:rootfs

RUN <<EOT
  set -e
  /usr/lib/system/package_layer \
    base \
    bluez \
    btrfs-progs \
    colordiff \
    debugedit \
    distrobox \
    dkms \
    dmidecode \
    dosfstools \
    e2fsprogs \
    efibootmgr \
    exfatprogs \
    fakeroot \
    fastfetch \
    flatpak \
    fuse-overlayfs \
    git \
    htop \
    less \
    linux-firmware \
    linux-zen \
    linux-zen-headers \
    micro \
    mtools \
    nano \
    networkmanager \
    ntfs-3g \
    nvme-cli \
    ostree \
    pacman-contrib \
    podman \
    pv \
    python-dbus \
    python-podman \
    python-progressbar \
    python-pyxattr \
    python-requests \
    rsync \
    run-parts \
    sbctl \
    skopeo \
    squashfs-tools \
    sudo-rs \
    terminus-font \
    tmux \
    wireless-regdb \
    xdelta3 \
    xfsprogs \
    xorriso
  rm \
    /usr/bin/su \
    /usr/share/libalpm/hooks/7*-dkms-{install,upgrade,remove}.hook \
    /usr/share/libalpm/hooks/zz-sbctl.hook
  ln -s /usr/bin/su{-rs,}
  ln -s /usr/bin/sudo{-rs,}
  ln -s /usr/bin/visudo{-rs,}
  chmod u+s /usr/bin/new{u,g}idmap
  /usr/lib/system/package_layer \
    broadcom-wl-dkms
EOT

COPY --from=clover /clover /etc/system/clover

COPY overlay/base /

# install_aur_packages is part of the overlay
RUN <<EOT
  set -e
  cp /{usr/share,etc}/containers/storage.conf
  mkdir /var/home
  /usr/lib/system/package_layer \
    --aur \
    localepurge
  rmdir /var/home
EOT

RUN <<EOT
  set -e
  systemctl enable \
    NetworkManager.service \
    bluetooth.service \
    podman.service \
    atomic-state-overlay.service \
    os-daemon.service \
    os-checkupdates.timer \
    systemd-timesyncd.service \
    pacman-initialize.service
  mkdir -p /var/lib/system
  chmod 400 /etc/sudoers
  chmod 644 /etc/pam.d/sudo{,-i}
EOT
