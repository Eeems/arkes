==========================
Frequently Asked Questions
==========================

Frequently asked questions about Arkēs atomic Linux distribution.

General Questions
-----------------

What is Arkēs?
~~~~~~~~~~~~~~

Arkēs is an **immutable, atomic Linux distribution** built on Arch Linux. It provides:

- **Immutable filesystem** - Core system files cannot be modified directly
- **Atomic updates** - Updates either complete fully or not at all
- **Rollback capability** - Always able to revert to previous system state
- **Container-native** - Built around Podman for application isolation
- **Declarative configuration** - System customization through Systemfile

**Key difference from traditional distributions**: The base system is read-only and managed through atomic updates rather than direct package installation.



Installation and Setup
----------------------

See :doc:`installation` for complete installation guide and :doc:`variants` for variant selection.

System Customization
--------------------

See :doc:`systemfile-reference` for package installation and system customization.

Can I modify system files directly?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**No** - Direct modification of immutable directories is not possible. Use Systemfile for system changes and ``os unlock`` for testing only.

Applications and Software
-------------------------

For application installation and Windows compatibility, see general Linux documentation or Arch Wiki.

**Podman commands** (Docker-compatible):

.. code-block:: bash

   # Pull image
   podman pull ubuntu:latest
   
   # Run container
   podman run -it ubuntu:latest
   
   # Build image
   podman build -t myapp .
   
   # Compose (with podman-compose)
   podman-compose up

**Docker compatibility**:
- **Same CLI**: Most Docker commands work with Podman
- **Same images**: Docker Hub images work with Podman
- **Same Dockerfiles**: No changes needed
- **Podman-compose**: Install for Docker Compose support

**Benefits of Podman**:
- **Rootless**: No root daemon required
- **Systemd integration**: Better service management
- **Security**: More secure by default

System Management
-----------------

How do I rollback to a previous version?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Rollback is simple and always available:

.. code-block:: bash

   # View available deployments
   os status
   
   # Rollback to previous deployment
   os revert

**When to rollback**:
- **After problematic update**
- **Hardware compatibility issues**
- **Application conflicts**
- **User preference**

**Rollback process**:
1. **Select** previous deployment
2. **Update** bootloader configuration
3. **Reboot** into selected deployment
4. **Verify** system functionality

**Safety**:
- **Always available** - Can't lose rollback capability
- **Instant** - Reboot and you're back
- **Safe** - Previous deployment was working

How do I check system status?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the ``os status`` command:

.. code-block:: bash

   os status

**Output shows**:
- **Current deployment** version and build ID
- **Available deployments** for rollback
- **Update status** - if updates are available
- **System information** - variant, hostname, etc.

**Example output**:

.. code-block:: text

   0: arkes:atomic (pinned)
     Version:   2024.12.1
     Build:     20241201120000
     Stateroot: arkes
     Timestamp: 2024-12-01 12:00:00

**Other status commands**:
- ``os checkupdates`` - Check for updates
- ``os du`` - Disk usage analysis
- ``journalctl`` - System logs

How often should I update?
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Recommended update frequency**:

**Desktop Users**: Update when you receive update notifications
- ``os checkupdates`` - Check manually if desired
- ``os upgrade`` - Update when notified

**Servers**: Monthly or for critical security updates
- Test updates on staging system first
- Schedule maintenance windows

**Process**:

.. code-block:: bash

   # Check for updates
   os checkupdates
   
   # If updates available
   os upgrade
   
   # Clean old deployments (monthly)
   os prune



Troubleshooting
---------------

What if an update fails?
~~~~~~~~~~~~~~~~~~~~~~~~

Update failures are handled automatically by the atomic system:

**Automatic Recovery**:
- **Failed updates** automatically revert
- **System remains** in previous working state
- **No manual intervention** required

**Manual Recovery**:
1. **Check status**: ``os status``
2. **If needed**: ``os revert``
3. **Investigate**: Check logs for failure cause
4. **Retry**: ``os upgrade`` when ready

**Common failure causes**:
- Network issues
- Insufficient disk space
- Power loss
- Package conflicts

What if I can't boot?
~~~~~~~~~~~~~~~~~~~~~

Boot issues have several recovery options:

**Immediate Steps**:
1. **Try previous deployment** in boot menu
2. **Boot from USB installer** for recovery
3. **Check hardware** - RAM, disk connections

**Recovery from USB**:
Boot from USB installer to access system or reinstall.

**Prevention**:
- Don't modify system files directly
- Test updates before important events
- Keep backups of important data

How do I free up disk space?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Arkēs provides several ways to manage disk space:

**Clean old deployments**:

.. code-block:: bash

   os prune

**Check disk usage**:

.. code-block:: bash

   os du

**Container cleanup**:
Use standard container cleanup commands.

**Regular maintenance**:
- Weekly: Check disk usage with ``os du``
- Monthly: Clean old deployments with ``os prune``

For more detailed troubleshooting, see :doc:`troubleshooting`.
