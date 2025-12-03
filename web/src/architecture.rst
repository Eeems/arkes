===================
System Architecture
===================

Arkēs provides an immutable, atomic Linux distribution built on key technologies.

Core Architecture
-----------------

**Key Components**:

- `OSTree <https://wiki.archlinux.org/title/OSTree>`_: Atomic updates and rollback system
- `Podman <https://wiki.archlinux.org/title/Podman>`_: Container runtime and management  
- **Immutable Filesystem**: Read-only base system
- `Systemfile <systemfile-reference>`_: Declarative system configuration

**Design Principles**:

- **Immutability**: Base system cannot be modified directly
- **Atomicity**: Updates either complete fully or not at all
- **Manual Rollback**: Ability to revert to previous system state
- **Container-Based Builds**: System builds use container technology

Atomic Updates & Rollback
-------------------------

`OSTree <https://wiki.archlinux.org/title/OSTree>`_ provides atomic updates with manual rollback capability. Updates download and build new system trees in parallel, then activate on reboot. If an update causes issues, you can manually revert to the previous working state by rebooting and selecting the previous deployment from the boot menu, then running ``os revert`` to clean up the problematic deployment.

Filesystem Structure
--------------------

Arkēs uses a hybrid filesystem with immutable and writable areas:

**Immutable Directories** (managed by `OSTree <https://wiki.archlinux.org/title/OSTree>`_):

- `/usr`, `/bin`, `/lib`, `/etc`, `/boot` - Core system files

**Writable Directories** (persistent across updates):

- `/var/home` - User home directories (instead of `/home`)
- `/var/log`, `/var/tmp`, `/var/cache` - System data

For `filesystem hierarchy <https://wiki.archlinux.org/title/Filesystem_hierarchy>`_ standards, see Arch Wiki.

Configuration Management
------------------------

System configuration is managed through overlays and `Systemfile <systemfile-reference>`_. Base system provides defaults, overlay files override configuration, and `Systemfile <systemfile-reference>`_ defines packages and settings.

