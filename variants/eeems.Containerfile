# syntax=docker/dockerfile:1.4
# x-name=Eeems
# x-depends=atomic
# x-templates=nvidia,system76
# x-clean
ARG HASH

FROM arkes:atomic

RUN /usr/lib/system/add_pacman_repository \
  --keyfile=https://download.sublimetext.com/sublimehq-pub.gpg \
  --key=8A8F901A \
  --server=https://download.sublimetext.com/arch/stable/\$arch \
  sublime-text \
  && /usr/lib/system/add_pacman_repository \
  --key=A64228CCD26972801C2CE6E3EC931EA46980BA1B \
  --server=https://repo.eeems.website/\$repo \
  --server=https://repo.eeems.codes/\$repo \
  eeems-linux \
  && /usr/lib/system/install_packages eeems-keyring \
  && /usr/lib/system/remove_pacman_files

RUN /usr/lib/system/package_layer \
  sublime-text \
  zsh \
  man-pages \
  man-db \
  zerotier-one \
  kdeconnect \
  zram-generator \
  v4l2loopback-utils \
  v4l2loopback-dkms \
  pyenv \
  spotify \
  podman-docker \
  podman-compose \
  --aur \
  wego

RUN systemctl enable zerotier-one

COPY overlay/eeems /
