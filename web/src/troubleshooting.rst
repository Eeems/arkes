===============
Troubleshooting
===============

Comprehensive guide to resolving common issues with Arkēs. This guide covers installation problems, update failures, and system recovery.

Getting Help
------------

Before diving into troubleshooting, remember these resources:

**Quick Commands**:
- ``os status`` - Check current system state
- ``os revert`` - Rollback to previous deployment
- ``journalctl -xe`` - View system error logs
- ``os unlock`` - Temporarily make system mutable for testing

**Documentation**:
- :doc:`user-guide` - Daily usage guidance
- :doc:`cli-reference` - Command reference
- :doc:`faq` - Common questions
- GitHub Issues - https://github.com/Eeems/arkes/issues

Installation Issues
-------------------

UEFI/Boot Problems
~~~~~~~~~~~~~~~~~~

**Symptoms**:
- System won't boot from USB
- "No bootable device" error
- UEFI setup doesn't show USB drive

**Solutions**:

1. **Check UEFI Settings**:
   - **Disable Secure Boot**: Find in Security/Boot menu
   - **Enable UEFI mode**: Disable CSM/Legacy boot
   - **Fast Boot**: Disable fast boot temporarily
   - **Boot Order**: Set USB as first boot device

2. **Try Different USB Ports**:
   - Use USB 2.0 ports if USB 3.0 fails
   - Try different USB ports (front vs back)
   - Avoid USB hubs for initial boot

3. **Recreate Installation Media**:
   - Verify ISO checksum: ``sha256sum arkes-*.iso``
   - Use different USB drive
   - Try different writing method:

   .. code-block:: bash

      # Alternative method using cp
      sudo cp arkes-atomic.iso /dev/sdX
      sync

4. **Check Hardware Compatibility**:
   - Verify 64-bit UEFI support
   - Check for known hardware issues
   - Try with minimal peripherals connected

**Verification**:

.. code-block:: bash

   # Check if booted in UEFI mode
   ls /sys/firmware/efi
   
   # Should show directory contents if UEFI

Installation Fails
~~~~~~~~~~~~~~~~~~

**Symptoms**:
- Installation stops with error
- Package download failures
- Disk partitioning errors

**Solutions**:

1. **Network Issues**:
   - Check internet connection: ``ping archlinux.org``
   - Try different network (wired vs wireless)
   - Check DNS: ``nslookup archlinux.org``
   - Try different mirror in installer

2. **Disk Issues**:
   - Ensure target disk has enough space (20GB minimum)
   - Check disk health: ``sudo fsck -f /dev/sdX``
   - Try manual partitioning if automatic fails
   - Disconnect other drives to avoid confusion

3. **Package Issues**:
   - Clear package cache: ``sudo pacman -Scc``
   - Update package databases: ``sudo pacman -Sy``
   - Check disk space: ``df -h``
   - Try alternative mirrors

4. **Memory Issues**:
   - Check available RAM: ``free -h``
   - Close unnecessary programs
   - Try with more RAM if available

**Error-Specific Solutions**:

**"Failed to download package"**:
.. code-block:: bash

   # Test network connectivity
   curl -I https://archive.archlinux.org/core/os/x86_64/core.db
   
   # Try different mirror
   # Edit /etc/pacman.d/mirrorlist during install

**"Partition failed"**:
.. code-block:: bash

   # Check disk state
   lsblk
   sudo fdisk -l
   
   # Manual partitioning if needed
   sudo cfdisk /dev/sdX

Post-Installation Issues
------------------------

First Boot Problems
~~~~~~~~~~~~~~~~~~~

**Symptoms**:
- System doesn't boot after installation
- Boot loops
- Black screen on boot

**Solutions**:

1. **Check Bootloader**:
   - Enter UEFI setup and check boot order
   - Look for "Arkēs" in boot menu
   - Try booting from firmware directly

2. **Emergency Shell**:
   - If system drops to emergency shell, check logs
   - Common issue: Missing kernel modules
   - Try booting previous deployment

3. **Graphics Issues**:
   - Black screen may indicate graphics driver problems
   - Try booting with different kernel parameters
   - Check if NVIDIA/AMD drivers needed

4. **Rollback Installation**:
   - Boot from USB installer
   - Use ``os revert`` from live environment
   - Reinstall with different options

Network Configuration
~~~~~~~~~~~~~~~~~~~~~

**Symptoms**:
- No internet connection
- Wi-Fi not detected
- Network manager errors

**Solutions**:

1. **Check Hardware**:
   - List network devices: ``ip link``
   - Check if drivers loaded: ``lspci -k | grep -i network``
   - Try different network hardware

2. **NetworkManager Issues**:
   - Restart NetworkManager: ``sudo systemctl restart NetworkManager``
   - Check status: ``systemctl status NetworkManager``
   - View logs: ``journalctl -u NetworkManager``

3. **Manual Configuration**:
   - Configure network manually if NetworkManager fails:

   .. code-block:: bash

      # Wired connection
      sudo ip link set eth0 up
      sudo dhcpcd eth0
      
      # Wireless connection
      sudo ip link set wlan0 up
      sudo iwctl station wlan0 scan
      sudo iwctl station wlan0 connect "SSID"

4. **Wi-Fi Specific**:
   - Check firmware: ``ls /usr/lib/firmware/``
   - Install missing firmware: ``sudo pacman -S linux-firmware``
   - Try different wireless driver

Update Issues
-------------

Update Failures
~~~~~~~~~~~~~~~

**Symptoms**:
- ``os upgrade`` fails with errors
- Update gets stuck during download
- System won't boot after update

**Solutions**:

1. **Network and Storage**:
   - Check internet connection
   - Ensure sufficient disk space: ``df -h``
   - Clean package cache: ``sudo pacman -Scc``
   - Check available updates: ``os checkupdates``

2. **Package Conflicts**:
   - View error messages carefully
   - Check for conflicting packages
   - Try manual resolution:

   .. code-block:: bash

      # Check package conflicts
      sudo pacman -Qi package-name
      
      # Remove conflicting package
      sudo pacman -R conflicting-package

3. **Partial Updates**:
   - If update partially completed, check system state
   - Try completing update: ``os upgrade``
   - If still failing, rollback: ``os revert``

4. **Boot Issues After Update**:
   - Boot into previous deployment: ``os revert``
   - Check what changed in the update
   - Report issue with specific error messages

**Common Update Errors**:

**"Failed to commit deployment"**:
.. code-block:: bash

   # Check disk space
   df -h
   
   # Clean old deployments
   os prune
   
   # Check OSTree status
   ostree status

**"Signature verification failed"**:
.. code-block:: bash

   # Update package keys
   sudo pacman-key --refresh-keys
   
   # Update keyring
   sudo pacman -Sy archlinux-keyring
   
   # Clear package cache
   sudo pacman -Scc

**"Dependency resolution failed"**:
.. code-block:: bash

   # Check dependency graph
   sudo pacman -Si package-name
   
   # Try updating database
   sudo pacman -Sy
   
   # Remove problematic package temporarily
   sudo pacman -Rdd problematic-package

System Performance
------------------

Slow Boot Times
~~~~~~~~~~~~~~~

**Symptoms**:
- System takes long time to boot
- Long delay before login screen
- Services failing to start

**Solutions**:

1. **Check Boot Time**:
   - Analyze boot process: ``systemd-analyze``
   - View detailed breakdown: ``systemd-analyze blame``
   - View critical chain: ``systemd-analyze critical-chain``

2. **Service Optimization**:
   - Disable unnecessary services:

   .. code-block:: bash

      # List enabled services
      systemctl list-unit-files --state=enabled
      
      # Disable service
      sudo systemctl disable service-name

3. **Storage Issues**:
   - Check disk health: ``sudo fsck -f /dev/sdX``
   - Monitor disk I/O: ``iotop``
   - Check for disk errors: ``sudo dmesg | grep -i error``

4. **Hardware Issues**:
   - Check RAM usage: ``free -h``
   - Monitor temperature: ``sensors``
   - Check CPU usage: ``htop``

High Memory Usage
~~~~~~~~~~~~~~~~~

**Symptoms**:
- System feels sluggish
- Applications crash frequently
- Out of memory errors

**Solutions**:

1. **Memory Analysis**:
   - Check memory usage: ``free -h``
   - Find memory hogs: ``ps aux --sort=-%mem | head``
   - Monitor over time: ``watch -n 1 free -h``

2. **Container Memory**:
   - Check container memory usage: ``podman stats``
   - Limit container memory: ``podman run -m 512m ...``
   - Clean unused containers: ``podman system prune``

3. **System Optimization**:
   - Reduce swap usage: ``sudo sysctl vm.swappiness=10``
   - Clear caches: ``sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches``
   - Restart memory-heavy services

Application Issues
------------------

Flatpak Applications
~~~~~~~~~~~~~~~~~~~~

**Symptoms**:
- Flatpak apps won't start
- Graphics issues in Flatpak apps
- Permission denied errors

**Solutions**:

1. **Installation Issues**:
   - Update Flatpak: ``flatpak update``
   - Repair installation: ``flatpak repair``
   - Reinstall problematic app:

   .. code-block:: bash

      flatpak uninstall app-id
      flatpak install app-id

2. **Permission Issues**:
   - Check permissions: ``flatpak permissions --show``
   - Grant necessary permissions:

   .. code-block:: bash

      flatpak override --filesystem=home app-id
      flatpak override --device=dri app-id

3. **Graphics Issues**:
   - Check graphics integration: ``flatpak list --show-details``
   - Update graphics drivers: ``os upgrade``
   - Try software rendering:

   .. code-block:: bash

      flatpak override --env=GSK_RENDERER=cairo app-id

Container Issues
~~~~~~~~~~~~~~~~

**Symptoms**:
- Containers won't start
- Network issues in containers
- Permission errors

**Solutions**:

1. **Container Runtime**:
   - Check Podman status: ``systemctl status podman``
   - Restart Podman: ``sudo systemctl restart podman``
   - Check Podman logs: ``journalctl -u podman``

2. **Network Issues**:
   - Test container networking:

   .. code-block:: bash

      podman run --rm alpine ping -c 3 8.8.8.8

   - Use host networking if needed:

   .. code-block:: bash

      podman run --net=host ...

3. **Permission Issues**:
   - Check user namespaces: ``podman info``
   - Ensure proper user configuration
   - Try with sudo for debugging

Hardware Issues
---------------

Graphics Problems
~~~~~~~~~~~~~~~~~

**Symptoms**:
- No display after boot
- Incorrect resolution
- Graphics artifacts

**Solutions**:

1. **Driver Issues**:
   - Check loaded drivers: ``lspci -k | grep -i vga``
   - Check X11/Wayland logs: ``journalctl -xe``
   - Try different driver variants

2. **Configuration Issues**:
   - Check graphics configuration files
   - Try different kernel parameters
   - Reset graphics configuration

3. **Hardware-Specific**:
   - **NVIDIA**: Ensure nvidia template is used
   - **AMD**: Check amdgpu driver loading
   - **Intel**: Check i915 driver status

Audio Issues
~~~~~~~~~~~~

**Symptoms**:
- No sound output
- Audio distortion
- Microphone not working

**Solutions**:

1. **Check Audio System**:
   - List audio devices: ``aplay -l``
   - Check audio service: ``systemctl status pipewire``
   - Test audio: ``speaker-test -c 2``

2. **Configuration**:
   - Check volume levels: ``pavucontrol``
   - Try different audio profiles
   - Restart audio services:

   .. code-block:: bash

      systemctl --user restart pipewire
      systemctl --user restart wireplumber

3. **Hardware Issues**:
   - Check if device is recognized: ``lsusb`` and ``lspci``
   - Try different audio ports
   - Check for hardware-specific drivers

Recovery Procedures
-------------------

System Recovery
~~~~~~~~~~~~~~~

**Complete System Recovery**:

1. **Boot from Live USB**
2. **Mount System**:

   .. code-block:: bash

      # Find Arkēs deployment
      sudo ostree admin --sysroot=/mnt os-init /mnt
      sudo mount /dev/sdX2 /mnt/var

3. **Backup Data**:

   .. code-block:: bash

      # Backup user data
      sudo cp -r /mnt/var/home /backup/location

4. **Reinstall System**:

   .. code-block:: bash

      # Reinstall from scratch
      sudo os install

5. **Restore Data**:

   .. code-block:: bash

      # Restore user data
      sudo cp -r /backup/location/home/* /var/home/

**Data Recovery**:

.. code-block:: bash

   # Access user data from any Linux system
   sudo mount /dev/sdX2 /mnt
   sudo cp -r /mnt/var/home/username /recovery/location

Emergency Procedures
--------------------

System Unresponsive
~~~~~~~~~~~~~~~~~~~

**Immediate Steps**:
1. **Try SSH**: If remote, attempt SSH connection
2. **Check Console**: Switch to TTY (Ctrl+Alt+F1-F6)
3. **Reboot**: If completely frozen, use REISUB (Alt+SysReq+R,E,I,S,U,B)

**Debugging in Emergency Shell**:

.. code-block:: bash

   # Check system status
   systemctl status
   
   # View recent errors
   journalctl -p err -n 50
   
   # Check disk space
   df -h
   
   # Check mounts
   mount | grep -v "proc\|sysfs\|devtmpfs"

**Last Resort Recovery**:

If all else fails:
1. **Boot from USB installer**
2. **Backup important data**
3. **Reinstall system**
4. **Restore from backup**

Preventive Measures
-------------------

Regular Maintenance
~~~~~~~~~~~~~~~~~~~

**Weekly Tasks**:
- Check for updates: ``os checkupdates``
- Update system: ``os upgrade``
- Clean old deployments: ``os prune``

**Monthly Tasks**:
- Clean container storage: ``podman system prune``
- Check disk usage: ``os du``
- Review system logs: ``journalctl --since "4 weeks ago"``

Backup Strategy
~~~~~~~~~~~~~~~

**Important Data to Backup**:
- ``/var/home``: User home directories
- ``/var/lib``: Application data
- ``/var/opt``: Optional software
- Configuration files in ``/etc``

**Backup Commands**:

.. code-block:: bash

   # Backup user data
   sudo rsync -av /var/home/ /backup/arkes-home/
   
   # Backup system configuration
   sudo rsync -av /etc/system/ /backup/arkes-config/

**Automated Backup**:

.. code-block:: bash

   # Create backup script
   cat > /usr/local/bin/backup-arkes << 'EOF'
   #!/bin/bash
   rsync -av --delete /var/home/ /backup/arkes-home/
   rsync -av --delete /etc/system/ /backup/arkes-config/
   EOF
   
   chmod +x /usr/local/bin/backup-arkes
   
   # Add to cron
   echo "0 2 * * * /usr/local/bin/backup-arkes" | sudo crontab -

When to Seek Help
-----------------

**Contact Support If**:
- Multiple attempts to fix issue have failed
- Error messages are unclear or not documented
- Hardware appears to be failing
- Data recovery is needed

**Useful Information for Support**:
- Arkēs version: ``os status``
- Hardware details: ``lspci``, ``lsusb``
- Error messages: ``journalctl -xe``
- Steps taken so far
- Expected vs actual behavior

**Debug Information Collection**:

.. code-block:: bash

   # System information
   os status > system-info.txt
   lspci -nn >> system-info.txt
   lsusb >> system-info.txt
   
   # Recent errors
   journalctl -p err -n 100 >> system-info.txt
   
   # Disk usage
   df -h >> system-info.txt
   os du >> system-info.txt

Remember that Arkēs' atomic nature means most issues can be resolved by rolling back with ``os revert`` and then investigating the problem in a stable system state.

For additional help, see :doc:`faq` or visit the GitHub issues page.
