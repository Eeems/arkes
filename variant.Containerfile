# syntax=docker/dockerfile:1.4
ARG BUILD_TAG

FROM ${BUILD_TAG}

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

RUN /usr/lib/system/set_variant

WORKDIR /
ENTRYPOINT [ "/bin/bash" ]
