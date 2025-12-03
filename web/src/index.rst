=====================================
Arkēs: Atomic Arch Linux Distribution
=====================================

Arkēs is an immutable, atomic Linux distribution built on Arch Linux that provides:

- **Immutable filesystem** with atomic updates and rollbacks  
- **Container-native architecture** using Podman
- **Multiple desktop variants** for different use cases
- **Automated updates** with OSTree technology

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
