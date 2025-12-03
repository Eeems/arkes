==========
User Guide
==========

This guide covers daily usage of Arkēs as an immutable, atomic Linux distribution.

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
~~~~~~~~~~~~~~~~~

Arkēs uses Systemfile for system-level packages. See :doc:`systemfile-reference` for details.

For desktop applications, use Flatpak. For containers, use Podman.

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

**Storage Issues**
- Check disk usage: ``os du``
- Clean old deployments: ``os prune``

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
