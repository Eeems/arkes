# syntax=docker/dockerfile:1.4
ARG ARCHIVE_YEAR=2026
ARG ARCHIVE_MONTH=04
ARG ARCHIVE_DAY=10
ARG GOLANG_VERSION=1.25.5
ARG PACSTRAP=${PACSTRAP:-docker.io/library/archlinux:base-devel-20260104.0.477168}
ARG PACSTRAP_PLATFORM=${PACSTRAP_PLATFORM:-linux/amd64}
ARG HASH VERSION_ID
ARG MIRRORLIST
ARG MIRRORS
ARG REPOS

FROM golang:${GOLANG_VERSION}-alpine as dockerfile2llbjson
USER root
WORKDIR /app
COPY tools/dockerfile2llbjson/go.mod tools/dockerfile2llbjson/go.sum ./
RUN go mod download
COPY tools/dockerfile2llbjson/main.go ./
RUN CGO_ENABLED=0 go build -trimpath -ldflags "-s -w" -o /app/dockerfile2llbjson .

FROM --platform=${PACSTRAP_PLATFORM} ${PACSTRAP} AS pacstrap

ARG \
  ARCHIVE_YEAR \
  ARCHIVE_MONTH \
  ARCHIVE_DAY \
  MIRRORS \
  REPOS

COPY overlay/rootfs/etc/pacman.d/base.config.conf /etc/pacman.d/base.config.conf
COPY overlay/rootfs/etc/pacman.conf /etc/pacman.conf

RUN truncate -s 0 /etc/pacman.d/mirrorlist \
  && for mirror in ${MIRRORS:?}; do echo "[mirror] $mirror" && echo "Server = ${mirror}" >> /etc/pacman.d/mirrorlist; done \
  && for repo in ${REPOS:?}; do echo "[repo] $repo" && echo "[$repo]" > /etc/pacman.d/"$repo".repo.conf && echo "Include = /etc/pacman.d/mirrorlist" >> /etc/pacman.d/"$repo".repo.conf; done \
  && sed -i '/\[options\]/aInclude=/etc/pacman.d/base.config.conf' /etc/pacman.conf

RUN pacman-key --init \
  && sed -i 's/DownloadUser = alpm/#DownloadUser = alpm/' /etc/pacman.conf \
  && pacman --disable-sandbox -Syu --needed --noconfirm \
  archlinux-keyring \
  moreutils \
  base-devel

RUN mkdir /rootfs

WORKDIR /rootfs

RUN <<EOT
  set -e
  mkdir -m 0755 -p \
    var/{cache/pacman/pkg,lib/pacman,log} \
    dev \
    run \
    etc
  mkdir -m 1777 tmp
  mkdir -m 0555 sys proc
EOT
RUN chronic fakeroot pacman -r . -Sy --noconfirm \
  base \
  mkinitcpio \
  moreutils

COPY overlay/rootfs /overlay
COPY --from=dockerfile2llbjson /app/dockerfile2llbjson /overlay/usr/bin/dockerfile2llbjson

RUN rm usr/share/libalpm/hooks/60-mkinitcpio-remove.hook \
  && rm usr/share/libalpm/hooks/90-mkinitcpio-install.hook \
  && cp -a {/,}etc/pacman.d/mirrorlist \
  && cp -a /etc/pacman.d/*.repo.conf etc/pacman.d/ \
  && rm -rf home && ln -s var/home home \
  && rm -rf mnt && ln -s var/mnt mnt \
  && rm -rf root && ln -s var/roothome root \
  && rm -rf srv && ln -s var/srv srv \
  && rm -rf usr/local && ln -s ../var/usrlocal usr/local \
  && truncate -s 0 etc/machine-id \
  && cp -a /overlay/. /rootfs/. \
  && cd / \
  && tar --sort=name \
  --owner=0 --group=0 \
  --numeric-owner \
  --pax-option=exthdr.name=%d/PaxHeaders/%p,delete=atime,delete=ctime \
  --mtime="@1735689640" \
  -C rootfs \
  -cf rootfs.tar . \
  && rm -rf rootfs \
  && mkdir rootfs \
  && tar -C rootfs -xf rootfs.tar \
  && rm rootfs.tar

FROM scratch AS rootfs

ARG \
  ARCHIVE_YEAR \
  ARCHIVE_MONTH \
  ARCHIVE_DAY \
  HASH \
  MIRRORLIST

LABEL \
  os-release.NAME="Arkēs" \
  os-release.PRETTY_NAME="Arkēs Arch Linux" \
  os-release.ID="arkes" \
  os-release.HOME_URL="https://github.com/Eeems/arkes" \
  os-release.BUG_REPORT_URL="https://github.com/Eeems/arkes/issues" \
  os-release.VERSION="${ARCHIVE_YEAR}.${ARCHIVE_MONTH}.${ARCHIVE_DAY}" \
  os-release.VERSION_ID="${ARCHIVE_YEAR}.${ARCHIVE_MONTH}.${ARCHIVE_DAY}" \
  org.opencontainers.image.authors="eeems@eeems.email" \
  org.opencontainers.image.source="https://github.com/Eeems/arkes" \
  org.opencontainers.image.ref.name="rootfs" \
  org.opencontainers.image.description="Atomic and immutable Linux distribution as a container." \
  hash="${HASH}" \
  mirrorlist="${MIRRORLIST}"

WORKDIR /

COPY --from=pacstrap /rootfs /

RUN  echo 'NAME="Arkēs"' > /usr/lib/os-release \
  && echo 'PRETTY_NAME="Arkēs Arch Linux"' >> /usr/lib/os-release \
  && echo 'ID=arkes' >> /usr/lib/os-release \
  && echo 'HOME_URL="https://github.com/Eeems/arkes"' >> /usr/lib/os-release \
  && echo 'SUPPORT_URL="https://github.com/Eeems/arkes/issues"' >> /usr/lib/os-release \
  && echo 'BUG_REPORT_URL="https://github.com/Eeems/arkes/issues"' >> /usr/lib/os-release \
  && echo "VERSION=${ARCHIVE_YEAR}.${ARCHIVE_MONTH}.${ARCHIVE_DAY}" >> /usr/lib/os-release \
  && echo "VERSION_ID=${ARCHIVE_YEAR}.${ARCHIVE_MONTH}.${ARCHIVE_DAY}" >> /usr/lib/os-release \
  && echo "VARIANT=Base" >> /usr/lib/os-release \
  && echo "VARIANT_ID=base" >> /usr/lib/os-release

ENTRYPOINT [ "/bin/bash" ]
