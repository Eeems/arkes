#!/bin/sh
set -e

# Rebind the xHCI controller of the Goodix fingerprint reader after resume.

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
    log "Goodix missing after resume, resetting xHCI controller"

    # Known xHCI controller BDFs per CPU vendor (AMD: 0000:c1:00.4, Intel: 0000:00:14.0)
    case "$(grep -m1 '^vendor_id' /proc/cpuinfo)" in
    *AuthenticAMD*) pci_func="0000:c1:00.4" ;;
    *GenuineIntel*) pci_func="0000:00:14.0" ;;
    *)
      log "unsupported CPU vendor, skipping rebind"
      exit 0
      ;;
    esac
    [ -e "/sys/bus/pci/devices/$pci_func" ] || {
      log "xHCI controller $pci_func not present, skipping rebind"
      exit 0
    }

    # Unbind and rebind the controller, checking each step
    [ -w "$DRIVER_PATH/unbind" ] || fail "cannot write to $DRIVER_PATH/unbind"
    [ -w "$DRIVER_PATH/bind" ] || fail "cannot write to $DRIVER_PATH/bind"
    echo "$pci_func" >"$DRIVER_PATH/unbind" || fail "failed to unbind $pci_func"
    sleep 1
    echo "$pci_func" >"$DRIVER_PATH/bind" || {
      # Retry once so the controller is not left detached
      sleep 1
      echo "$pci_func" >"$DRIVER_PATH/bind" || fail "failed to rebind $pci_func"
    }
    sleep 2

    # Verify the fingerprint reader came back after rebinding
    lsusb -d "$GOODIX_ID" >/dev/null 2>&1 || fail "$GOODIX_ID not present after rebind"

    # Restart fprintd so it picks up the reader again
    systemctl try-restart fprintd.service

    log "Goodix reader restored after resume"
  fi
  ;;
esac
