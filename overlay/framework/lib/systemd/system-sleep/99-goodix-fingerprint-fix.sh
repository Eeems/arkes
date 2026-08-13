#!/bin/sh
set -e

# Rebind USB controller 0000:c1:00.4 after resume to restore Goodix fingerprint reader.

PCI_FUNC="0000:c1:00.4"
GOODIX_ID="27c6:609c"
DRIVER_PATH="/sys/bus/pci/drivers/xhci_hcd"

log() {
  echo "$*" >&2
}

fail() {
  log "ERROR: $*"
  return 1
}

case "$1" in
post)
  # Give the system a moment to resume normally
  sleep 2

  # Check if the fingerprint reader is missing
  if ! lsusb -d "$GOODIX_ID" >/dev/null 2>&1; then
    log "Goodix missing after resume, resetting xHCI controller $PCI_FUNC"

    # Unbind and rebind only that PCI function, failing with a log on any error
    [ -w "$DRIVER_PATH/unbind" ] || fail "cannot write to $DRIVER_PATH/unbind"
    echo "$PCI_FUNC" >"$DRIVER_PATH/unbind" || fail "failed to unbind $PCI_FUNC"
    sleep 1
    echo "$PCI_FUNC" >"$DRIVER_PATH/bind" || fail "failed to rebind $PCI_FUNC"
    sleep 2

    # Verify the fingerprint reader came back after rebinding
    lsusb -d "$GOODIX_ID" >/dev/null 2>&1 || fail "$GOODIX_ID not present after rebind"

    # Restart fprintd so it picks up the reader again
    systemctl try-restart fprintd.service

    log "Goodix reader restored after resume"
  fi
  ;;
esac
