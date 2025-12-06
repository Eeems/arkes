==========
User Guide
==========

This guide covers daily usage of Arkēs as an immutable, atomic Linux distribution.

Daily Operations
----------------

Essential System Commands
~~~~~~~~~~~~~~~~~~~~~~~~~

The primary tool for system management is the ``os`` command.

.. code-block:: bash

   # Check system status and available deployments
   os status
   
   # Check for available updates
   os checkupdates
   
   # Build the latest Systemfile and deploy it
   os upgrade
   
   # Build the latest Systemfile, but do not deploy it.
   os build
   
   # Remove most recent deployment
   os revert

Package Management
~~~~~~~~~~~~~~~~~~

Arkēs uses the :doc:`Systemfile <systemfile-reference>` for installing system-level packages.

You will have `flatpak <https://wiki.archlinux.org/title/Flatpak>`_, `podman <https://wiki.archlinux.org/title/Podman>`_, and `distrobox <https://wiki.archlinux.org/title/Distrobox>`_ available for managing applications without having to rebuild and deploy a new system.

Configuration
~~~~~~~~~~~~~

Generally you will use the :doc:`Systemfile <systemfile-reference>` to make configuration changes to your system, but you can also modify files in ``/etc`` and changes will be merged when there is a new deployment.

Customization Workflow
----------------------

Making Changes to Your System
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The proper workflow for customizing your Arkēs system:

1. Optionally make the system temporarily mutable with ``os unlock`` to test out changes on the running system.
2. Edit Systemfile to add packages or configuration.
3. Optionally build new system image with ``os build`` to test out the changes.
4. Build the new system image and deploy it with ``os upgrade``.
