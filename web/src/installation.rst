==================
Installation Guide
==================

This guide will walk you through installing Arkēs on your system.

System Requirements
-------------------

- **UEFI** firmware (legacy BIOS not supported without manual intervention)
- **64-bit x86_64** processor
- **4GB RAM** minimum (8GB recommended)
- **20GB storage** minimum (30GB recommended)
- **Internet connection** for installation

Downloading Arkēs
-----------------

You can download a live boot ISO of Arkēs from: https://github.com/Eeems/arkes/releases

Choose the variant that best fits your needs. See :doc:`variants` for complete variant information.

Installation Process
--------------------

1. Boot Live Environment

   The live environment will automatically start. Depending on the variant you choose, you'll be presented with a console interface, or a desktop environment. You will be automatically logged in as the ``live`` user.

2. Partition the disks

   https://wiki.archlinux.org/title/Installation_guide#Partition_the_disks

3. Install

   .. code-block:: bash

      sudo os install \
        --system-partition /dev/sda2 \
        --boot-partition /dev/sda1

   Replace ``/dev/sda2`` with your system partition and ``/dev/sda1`` with your boot partition.

   For additional options, run ``os install --help``

   The installer will:

   - Mount partitions to ``/mnt``
   - Install base system from current :doc:`Systemfile <systemfile-reference>`
   - Configure bootloader (GRUB)
   - Set root password (prompted if not provided)
   - Generate fstab and system configuration

5. Reboot

Post-Installation
-----------------

First Boot
~~~~~~~~~~

1. Login as the root user using the password set during installation.

2. Create your user account: https://wiki.archlinux.org/title/Users_and_groups#User_management
