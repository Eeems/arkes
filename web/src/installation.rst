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

Choose the variant that best fits your needs:

- **rootfs**: Base system for developers
- **base**: Minimal server/container variant  
- **atomic**: Modern Wayland desktop
- **gnome**: Traditional GNOME desktop
- **eeems**: Personalized variant with extra tools

Creating Installation Media
---------------------------

1. **Download ISO** for your preferred variant
2. **Write to USB drive**:

   .. code-block:: bash

      # On Linux
      sudo dd if=arkes-atomic.iso of=/dev/sdX bs=4M status=progress sync
      
      # On macOS
      sudo dd if=arkes-atomic.iso of=/dev/rdiskX bs=4m

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

Network Configuration
~~~~~~~~~~~~~~~~~~~~~

- **Wired connections** should work automatically
- **Wi-Fi** can be configured:

   .. code-block:: bash

      # List available networks
      nmcli dev wifi list
      
      # Connect to network
      nmcli dev wifi connect "SSID" password "password"

Software Installation
~~~~~~~~~~~~~~~~~~~~~

Arkēs uses multiple package management methods:

- **Flatpak** (recommended for desktop applications)
- **Podman containers** for isolated applications
- **Docker containers** (alternative to Podman)
- **Systemfile** for system-level packages
- **AUR** through Systemfile (see :doc:`systemfile-reference`)

**Installing Docker (optional)**:

.. code-block:: bash

   # Install Docker
   sudo pacman -S docker
   
   # Start and enable Docker service
   sudo systemctl start docker
   sudo systemctl enable docker
   
   # Add user to docker group (optional, for running without sudo)
   sudo usermod -aG docker $USER
   
   # Log out and back in for group changes to take effect

Basic Usage
-----------

Check your current deployment:

.. code-block:: bash

   os status

Install applications with Flatpak:

.. code-block:: bash

   flatpak install org.mozilla.firefox

Use containers:

.. code-block:: bash

   podman run -it ubuntu:latest

Troubleshooting Installation
----------------------------

Common Issues
~~~~~~~~~~~~~

**UEFI Issues**
- Ensure **Secure Boot** is disabled
- Check that **CSM/Legacy** mode is disabled
- Try different USB ports

**Boot Issues**
- Verify the ISO was written correctly
- Try recreating the installation media
- Check system logs with ``journalctl -b``

**Network Issues**
- Verify network hardware compatibility
- Try manual network configuration
- Check driver availability

Recovery Options
~~~~~~~~~~~~~~~~

If installation fails, you can:

1. **Retry installation** after fixing issues
2. **Check system logs** in the live environment
3. **Boot back to live environment** to troubleshoot
4. **Ask for help** with specific error messages

Getting Help
------------

If you encounter issues during installation:

- **GitHub Issues**: https://github.com/Eeems/arkes/issues
- **Documentation**: Check :doc:`troubleshooting`
- **Community**: Join discussions in GitHub Discussions

Next Steps
----------

After successful installation:

1. Read the :doc:`user-guide` for daily usage
2. Explore :doc:`variants` to understand your chosen variant
3. Learn about :doc:`systemfile-reference` for customization
4. Check :doc:`quick-start` for a rapid overview
