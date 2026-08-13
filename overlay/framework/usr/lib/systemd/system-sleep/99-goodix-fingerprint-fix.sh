#!/bin/sh
set -e

# Rebind the xHCI controller of the Goodix fingerprint reader after resume.

GOODIX_ID="27c6:609c"
CONTROLLER_FILE="/run/goodix-xhci-controller"
DRIVER_PATH="/sys/bus/pci/drivers/xhci_hcd"

log() {
  echo "$*" >&2
}

fail() {
  log "ERROR: $*"
  return 1
}

case "$1" in
pre)
  # The device is present before suspend, so record its parent xHCI controller
  for dir in /sys/bus/usb/devices/*/; do
    if [ "$(cat "$dir/idVendor" 2>/dev/null)" != "${GOODIX_ID%:*}" ] ||
      [ "$(cat "$dir/idProduct" 2>/dev/null)" != "${GOODIX_ID#*:}" ]; then
      continue
    fi
    path=$(readlink -f "$dir")
    while [ "$path" != "/" ]; do
      case "$(basename "$path")" in
      [0-9a-f][0-9a-f][0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f].[0-9a-f])
        controller=$(basename "$path")
        break
        ;;
      esac
      path=$(dirname "$path")
    done
    break
  done
  if [ -n "$controller" ]; then
    echo "$controller" >"$CONTROLLER_FILE"
    log "recorded Goodix xHCI controller $controller"
  else
    rm -f "$CONTROLLER_FILE"
    log "cannot discover Goodix xHCI controller for $GOODIX_ID"
  fi
  ;;
post)
  # Give the system a moment to resume normally
  sleep 2
  # Use the controller recorded before suspend, skipping if unavailable
  controller=$(cat "$CONTROLLER_FILE" 2>/dev/null) || :
  [ -n "$controller" ] || {
    log "no recorded xHCI controller, skipping rebind"
    exit 0
  }
  [ -e "/sys/bus/pci/devices/$controller" ] || {
    log "xHCI controller $controller not present, skipping rebind"
    exit 0
  }
  # Nothing to do when the reader came back on its own
  if lsusb -d "$GOODIX_ID" >/dev/null 2>&1; then
    log "Goodix reader present, skipping rebind"
    exit 0
  fi
  log "Goodix missing after resume, resetting xHCI controller"
  # Unbind and rebind the controller, checking each step
  [ -w "$DRIVER_PATH/unbind" ] || fail "cannot write to $DRIVER_PATH/unbind"
  [ -w "$DRIVER_PATH/bind" ] || fail "cannot write to $DRIVER_PATH/bind"
  echo "$controller" >"$DRIVER_PATH/unbind" || fail "failed to unbind $controller"
  sleep 1
  echo "$controller" >"$DRIVER_PATH/bind" || {
    # Retry once so the controller is not left detached
    sleep 1
    echo "$controller" >"$DRIVER_PATH/bind" || fail "failed to rebind $controller"
  }
  sleep 2
  # Verify the fingerprint reader came back after rebinding
  lsusb -d "$GOODIX_ID" >/dev/null 2>&1 || fail "$GOODIX_ID not present after rebind"
  # Restart fprintd so it picks up the reader again
  if ! systemctl --no-block try-restart fprintd.service; then
    log "ERROR: failed to queue restart of fprintd.service"
  fi
  log "Goodix reader restored after resume"
  ;;
esac
