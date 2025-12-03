==========
User Guide
==========

This guide covers daily usage of Arkēs as an immutable, atomic Linux distribution.

Daily Operations
----------------

Essential System Commands
~~~~~~~~~~~~~~~~~~~~~~~

The primary tool for system management is the ``os`` command.

.. code-block:: bash

   # Check system status and available deployments
   os status
   
   # Check for available updates
   os checkupdates
   
   # Update system (atomic update)
   os upgrade
   
   # Rollback to previous deployment if needed
   os revert
   
   # Clean old deployments to free space
   os prune

Package Management
~~~~~~~~~~~~~~~~~

Arkēs uses Systemfile for system-level packages. See :doc:`systemfile-reference` for details.

For desktop applications, use Flatpak. For containers, use Podman.

Filesystem Layout
~~~~~~~~~~~~~~~~

Arkēs uses an immutable filesystem. See :doc:`architecture` for detailed filesystem information.

Key difference: User data is stored in ``/var/home`` instead of ``/home``.

Configuration
~~~~~~~~~~~~~

System-level configuration is done through Systemfile. User configuration works normally in ``~/.config``.



Customization Workflow
----------------------

Making Changes to Your System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The proper workflow for customizing your Arkēs system:

1. **Edit Systemfile** to add packages or configuration
2. **Build new system** with ``os build``
3. **Deploy system** with ``os upgrade``

For testing changes, use ``sudo os unlock`` to make system temporarily mutable.

See :doc:`systemfile-reference` for Systemfile details and :doc:`architecture` for filesystem information.

Getting Help
------------

For additional help with daily usage:

- **Documentation**: Check other guides in this manual
- **GitHub Issues**: https://github.com/Eeems/arkes/issues
- **Community**: GitHub Discussions

Remember that Arkēs' immutable nature means most issues can be resolved by:
1. Rolling back with ``os revert``
2. Fixing the issue in Systemfile
3. Rebuilding and upgrading with ``os build && os upgrade``
