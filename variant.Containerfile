# syntax=docker/dockerfile:1.4
ARG BUILD_TAG

FROM ${BUILD_TAG} as build

RUN <<EOT
  set -e
  /usr/lib/system/package_layer ccache
  python -m venv .venv
  source .venv/bin/activate
  pip install nuitka
EOT

RUN <<EOT
  set -e
  source .venv/bin/activate
  for module in cli daemon;do
    cd "/usr/lib/system/_os/$module"
    for file in *.py;do
      if [[ "$file" != "__init__.py" ]];then
        echo "# nuitka-project: --include-module=_os.$(basename --suffix .py "$file")" >> __init__.py
      fi
    done
    echo "from . import *" >> __init__.py
    echo "__all__ = [" >> __init__.py
    for file in *.py;do
      if [[ "$file" != "__init__.py" ]];then
        echo "  \"$(basename --suffix .py "$file")\"," >> __init__.py
      fi
    done
    echo "]" >> __init__.py
    cat __init__.py
  done
  cd /usr/lib/system
  python -m nuitka \
    --include-package=_os \
    --output-dir=/output \
    --module \
    _os
EOT

FROM ${BUILD_TAG}

COPY --from=build /output/_os*.so /usr/lib/system/

ARG \
  BUG_REPORT_URL \
  HASH \
  HOME_URL \
  ID \
  MIRRORLIST \
  NAME \
  PACKAGES \
  PRETTY_NAME \
  VARIANT \
  VARIANT_ID \
  VERSION \
  VERSION_ID

LABEL \
  os-release.NAME="${NAME}" \
  os-release.PRETTY_NAME="${PRETTY_NAME}" \
  os-release.ID="${ID}" \
  os-release.HOME_URL="${HOME_URL}" \
  os-release.BUG_REPORT_URL="${BUG_REPORT_URL}" \
  os-release.VERSION="${VERSION}" \
  os-release.VERSION_ID="${VERSION_ID}" \
  os-release.VARIANT="${VARIANT}" \
  os-release.VARIANT_ID="${VARIANT_ID}" \
  org.opencontainers.image.authors="eeems@eeems.email" \
  org.opencontainers.image.source="https://github.com/Eeems/arkes" \
  org.opencontainers.image.ref.name="${VARIANT_ID}" \
  hash="${HASH}" \
  mirrorlist="${MIRRORLIST}" \
  packages="${PACKAGES}"

RUN <<EOT
  set -e
  rm -r /usr/lib/system/_os
  /usr/lib/system/set_variant
EOT

WORKDIR /
ENTRYPOINT [ "/bin/bash" ]
