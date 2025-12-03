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

For application installation and container usage, see general Linux documentation or Arch Wiki.

System Management
-----------------

For system management commands (status, updates, rollback), see :doc:`user-guide`.

Troubleshooting
---------------

For detailed troubleshooting, see :doc:`troubleshooting`.
