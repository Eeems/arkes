==================
Installation Guide
==================

This guide will walk you through installing Arkēs on your system.

System Requirements
-------------------

- **UEFI** firmware (legacy BIOS not supported)
- **64-bit x86_64** processor
- **4GB RAM** minimum (8GB recommended)
- **20GB storage** minimum (30GB recommended)
- **Internet connection** for installation

Downloading Arkēs
-----------------

You can download Arkēs from:

- **GitHub Releases**: https://github.com/Eeems/arkes/releases
- **Container Registry**: ``podman pull ghcr.io/eeems/arkes:atomic``

Choose the variant that best fits your needs. See :doc:`variants` for complete variant information.

Creating Installation Media
---------------------------

1. **Download ISO** for your preferred variant
2. **Create bootable USB** using Arch Wiki: https://wiki.archlinux.org/title/USB_flash_installation

3. **Boot from USB** - Enter your firmware/BIOS and select the USB drive

Installation Process
--------------------

1. **Boot Live Environment**

   The live environment will automatically start. You'll be presented with a console interface.

2. **Start Installation**

   .. code-block:: bash

      sudo os install --system-partition /dev/sda2 --boot-partition /dev/sda1

   Replace ``/dev/sda2`` with your system partition and ``/dev/sda1`` with your boot partition.

**Common partition layouts**:

- **Single disk**: ``/dev/sda1`` (boot), ``/dev/sda2`` (system)
- **NVMe**: ``/dev/nvme0n1p1`` (boot), ``/dev/nvme0n1p2`` (system)

**Additional options**:

- ``--format-partitions``: Format partitions before installing
- ``--nvidia``: Install NVIDIA drivers
- ``--package``: Add extra packages (can be used multiple times)

3. **Installation Process**

The installer will:

- **Mount partitions** to ``/mnt``
- **Install base system** from current Systemfile
- **Configure bootloader** (GRUB)
- **Set root password** (prompted if not provided)
- **Generate fstab** and system configuration

4. **Wait for Completion**

   The installation process typically takes 10-20 minutes depending on your internet speed and storage.

5. **Reboot**

   Remove the USB drive and reboot into your new Arkēs system.

Post-Installation
-----------------

First Boot
~~~~~~~~~~

1. **Login** with the user account created during installation
2. **Check system status**:

   .. code-block:: bash

      os status

3. **Update system** (recommended):

   .. code-block:: bash

      os upgrade



Getting Help
------------

If you encounter issues during installation:

- **GitHub Issues**: https://github.com/Eeems/arkes/issues
- **Documentation**: Check :doc:`troubleshooting`
- **Community**: Join discussions in GitHub Discussions
