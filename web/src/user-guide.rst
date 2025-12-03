==========
User Guide
==========

This guide covers daily usage of Arkēs as an immutable, atomic Linux distribution.

Core Concepts
-------------

Immutable OS Philosophy
~~~~~~~~~~~~~~~~~~~~~~~~

Arkēs is built on the principle of **immutability**:

- **Base system (/usr)** is read-only and cannot be modified directly
- **User data (/var/home)** is fully writable and persistent
- **Configuration** is done through **Systemfile** and overlays
- **Updates** are atomic - they either complete fully or not at all

This approach provides:

- **Reliability** - System files cannot be accidentally corrupted
- **Security** - Malware cannot modify base system files
- **Consistency** - All systems start from identical base
- **Recovery** - Easy rollback from failed updates

Atomic Updates
~~~~~~~~~~~~~~~

Updates in Arkēs work differently from traditional distributions:

- **All-or-nothing** - Updates either complete successfully or not at all
- **Automatic rollback** - Failed updates automatically revert
- **Multiple deployments** - Keep previous versions for easy rollback
- **Zero-downtime** - Updates happen in background, activate on reboot

Container-Native Architecture
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Arkēs embraces containers as a primary application delivery method:

- **Podman** pre-installed and configured
- **Rootless containers** by default
- **System integration** with desktop and CLI tools
- **Isolation** for applications that need it

Daily Operations
----------------

System Management
~~~~~~~~~~~~~~~~~

The primary tool for system management is the ``os`` command.

Check System Status
^^^^^^^^^^^^^^^^^^^

See current deployment and version information:

.. code-block:: bash

   os status

Output shows:
- Current deployment version
- Available deployments
- System information
- Update status

Update System
^^^^^^^^^^^^^

Perform atomic system update:

.. code-block:: bash

   os upgrade

This will:
- Download latest packages
- Build new system image
- Deploy on next reboot
- Keep current system as rollback option

Check for Updates
^^^^^^^^^^^^^^^^^

See if updates are available without installing:

.. code-block:: bash

   os checkupdates

Rollback System
^^^^^^^^^^^^^^^

Revert to previous deployment if issues occur:

.. code-block:: bash

   os revert

This is useful when:
- New update causes problems
- Hardware compatibility issues
- Application conflicts
- User preference

Clean Old Deployments
^^^^^^^^^^^^^^^^^^^^^

Remove old system deployments to free space:

.. code-block:: bash

   os prune

Package Management
~~~~~~~~~~~~~~~~~~

Arkēs supports multiple package management approaches.

Flatpak (Recommended for Desktop Apps)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install desktop applications:

.. code-block:: bash

   # Search for applications
   flatpak search firefox
   
   # Install application
   flatpak install org.mozilla.firefox
   
   # Run application
   flatpak run org.mozilla.firefox
   
   # Update applications
   flatpak update

Podman Containers
^^^^^^^^^^^^^^^^^

Run isolated applications:

.. code-block:: bash

   # Run Ubuntu container
   podman run -it ubuntu:latest
   
   # Run with persistent storage
   podman run -it -v /home/user/data:/data ubuntu:latest
   
   # Run GUI application
   podman run -it --net=host --env=DISPLAY=$DISPLAY firefox

Systemfile (System Packages)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install system-level packages through Systemfile (see :doc:`systemfile-reference`):

.. code-block:: dockerfile

   RUN /usr/lib/system/install_packages vim git

AUR Packages
^^^^^^^^^^^^

Install AUR packages through Systemfile:

.. code-block:: dockerfile

   RUN /usr/lib/system/install_aur_packages package-name=git-ref

Filesystem Layout
~~~~~~~~~~~~~~~~~

Understanding the filesystem structure is key to using Arkēs effectively.

Immutable Directories
^^^^^^^^^^^^^^^^^^^^^

These directories are read-only and managed by the system:

- ``/usr`` - System programs and libraries
- ``/bin`` - Essential system binaries  
- ``/lib`` - System libraries
- ``/etc`` - System configuration (managed through overlays)
- ``/boot`` - Boot loader and kernel

Writable Directories
^^^^^^^^^^^^^^^^^^^^

These directories are fully writable:

- ``/var/home`` - User home directories (persistent)
- ``/var/log`` - System logs
- ``/var/tmp`` - Temporary files
- ``/var/cache`` - Application cache
- ``/opt`` - Optional software

User Data Management
^^^^^^^^^^^^^^^^^^^^

Your personal files are stored in ``/var/home/username``:

.. code-block:: bash

   # Navigate to home directory
   cd ~
   
   # Home is actually /var/home/username
   pwd
   # Output: /var/home/username
   
   # Traditional paths still work
   ls ~/Documents
   ls ~/Pictures

Configuration
~~~~~~~~~~~~~

System Configuration
^^^^^^^^^^^^^^^^^^^^

System-level configuration is done through:

1. **Systemfile** - Primary method for package and configuration changes
2. **Overlays** - Directory-based configuration for variants
3. **User configuration** - Traditional dotfiles in home directory

User Configuration
^^^^^^^^^^^^^^^^^^

Personal configuration files work as expected:

.. code-block:: bash

   # Shell configuration
   nano ~/.bashrc
   
   # Editor configuration  
   mkdir -p ~/.config/nano
   nano ~/.config/nanorc
   
   # Desktop configuration
   mkdir -p ~/.config/waybar
   nano ~/.config/waybar/config

Application Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^

Applications store configuration in standard locations:

- ``~/.config/appname`` - Application settings
- ``~/.local/share/appname`` - Application data
- ``~/.cache/appname`` - Cache files

Customization Workflow
----------------------

Making Changes to Your System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The proper workflow for customizing your Arkēs system:

1. **Edit Systemfile** to add packages or configuration
2. **Build new system** with ``os build``
3. **Deploy system** with ``os upgrade``

Testing Changes
~~~~~~~~~~~~~~~

For testing changes before deployment:

.. code-block:: bash

   # Make system temporarily mutable
   sudo os unlock
   
   # Test your changes manually
   sudo pacman -S test-package
   
   # When done testing, revert changes
   sudo reboot

   # Then make permanent changes through Systemfile
   # Edit /etc/system/Systemfile
   os build
   os upgrade

Systemfile Customization
~~~~~~~~~~~~~~~~~~~~~~~~

Example Systemfile modifications:

.. code-block:: dockerfile

   FROM arkes:atomic

   # Add system packages
   RUN /usr/lib/system/install_packages \
       vim \
       git \
       htop

   # Add AUR package
   RUN /usr/lib/system/install_aur_packages \
       visual-studio-code-bin

   # Add custom repository
   RUN /usr/lib/system/add_pacman_repository \
       --key=KEY_ID \
       --server=https://example.com/\$repo \
       custom-repo

   # Install from custom repo
   RUN /usr/lib/system/install_packages custom-package

Advanced Usage
---------------

System Unlock for Development
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``os unlock`` command makes your system temporarily mutable:

.. code-block:: bash

   # Make system mutable (changes lost on reboot)
   sudo os unlock
   
   # Make changes persist across reboots (for development)
   sudo os unlock --hotfix

**Use cases for unlock:**
- Testing package compatibility
- Development and debugging
- Emergency fixes
- Learning system internals

**Warning:** Changes made while unlocked are temporary unless using ``--hotfix``

Container Integration
~~~~~~~~~~~~~~~~~~~~~

Arkēs provides seamless container integration:

.. code-block:: bash

   # Run container with home directory access
   podman run -it -v ~/Documents:/documents ubuntu:latest
   
   # Run GUI application from container
   podman run -it --net=host --env=DISPLAY=$DISPLAY \
       -v /tmp/.X11-unix:/tmp/.X11-unix \
       firefox
   
   # Build and run custom container
   echo 'FROM alpine:latest
   RUN apk add --no-cache htop' > Containerfile
   podman build -t my-htop .
   podman run -it my-htop

System Maintenance
~~~~~~~~~~~~~~~~~~

Regular maintenance tasks:

.. code-block:: bash

   # Check system status
   os status
   
   # Clean old deployments (monthly)
   os prune
   
   # Check disk usage
   os du
   
   # Update packages
   os upgrade
   
   # Update Flatpaks
   flatpak update

Troubleshooting Daily Issues
----------------------------

Common Problems
~~~~~~~~~~~~~~~

**Application Won't Start**
- Check if package is installed: ``flatpak list`` or ``os status``
- Try running from terminal for error messages
- Check dependencies: ``flatpak info appname``

**Network Issues**
- Check NetworkManager: ``nmcli connection show``
- Restart network: ``sudo systemctl restart NetworkManager``
- Check hardware: ``ip link``

**Storage Issues**
- Check disk usage: ``os du``
- Clean old deployments: ``os prune``
- Clear package cache: ``sudo pacman -Scc``

**Update Failures**
- Check internet connection
- Free up disk space
- Try again: ``os upgrade``
- If persistent, check logs: ``journalctl -xe``

Getting Help
------------

For additional help with daily usage:

- **Documentation**: Check other guides in this manual
- **GitHub Issues**: https://github.com/Eeems/arkes/issues
- **Community**: GitHub Discussions
- **System logs**: ``journalctl`` for detailed error information

Remember that Arkēs' immutable nature means most issues can be resolved by:
1. Rolling back with ``os revert``
2. Fixing the issue in Systemfile
3. Rebuilding and upgrading with ``os build && os upgrade``
