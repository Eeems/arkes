#!/bin/sh
# Rebind USB controller 0000:c1:00.4 after resume to restore Goodix fingerprint reader.

PCI_FUNC="0000:c1:00.4"
GOODIX_ID="27c6:609c"
DRIVER_PATH="/sys/bus/pci/drivers/xhci_hcd"

case "$1" in
  post)
    # Give the system a moment to resume normally
    sleep 2

    # Check if the fingerprint reader is missing
    if ! lsusb -d "$GOODIX_ID" >/dev/null 2>&1; then
      logger -t fp-rebind "Goodix missing after resume, resetting xHCI controller $PCI_FUNC"
      # Unbind and rebind only that PCI function
      echo "$PCI_FUNC" > "$DRIVER_PATH/unbind"
      sleep 1
      echo "$PCI_FUNC" > "$DRIVER_PATH/bind"
      sleep 2
      # Restart fprintd so it picks up the reader again
      systemctl try-restart fprintd.service
    fi
    ;;
esac
