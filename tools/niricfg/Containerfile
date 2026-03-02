FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN <<EOT
  set -e
  apt-get update
  apt update --allow-releaseinfo-change
  apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    unzip \
    xz-utils \
    zip \
    libglu1-mesa \
    cmake \
    clang \
    ninja-build \
    libgtk-3-dev \
    libasound2-dev \
    libmpv-dev \
    mpv \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer-plugins-bad1.0-dev \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-tools \
    gstreamer1.0-x \
    gstreamer1.0-alsa \
    gstreamer1.0-gl \
    gstreamer1.0-gtk3 \
    gstreamer1.0-qt5 \
    gstreamer1.0-pulseaudio \
    pkg-config \
    libsecret-1-0 \
    libsecret-1-dev \
    lld \
    llvm
  apt-get clean
  rm -rf /var/lib/apt/lists/*
EOT

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV FLUTTER_VERSION=3.41.2
ENV FLUTTER_HOME=/root/flutter
ENV PATH="/root/.local/bin:${FLUTTER_HOME}/bin:${PATH}"

RUN <<EOT
  set -e
  cd /root
  curl -O https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_${FLUTTER_VERSION}-stable.tar.xz
  tar xf flutter_linux_${FLUTTER_VERSION}-stable.tar.xz
  rm flutter_linux_${FLUTTER_VERSION}-stable.tar.xz
  git config --global --add safe.directory ${FLUTTER_HOME}
  flutter --disable-analytics
  flutter --version
  flutter precache --universal --linux
  flutter doctor --no-version-check || true
EOT

ENV FLET_CLI_NO_RICH_OUTPUT=1

RUN <<EOT
  set -e
  uvx flet doctor
  cd /tmp
  uvx flet create app
  cd app
  uvx flet build linux --yes --verbose
  cd ..
  rm -rf app
EOT
