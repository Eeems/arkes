=============
CLI Reference
=============

The ``make`` command is the primary interface for building and managing Arkēs variants. This reference is generated from the actual command-line interface.

.. note::
   This documentation is generated from the actual ``make`` command implementation. 
   Run ``make --help`` for the most up-to-date command information.

.. raw:: html

   <div class="cli-help">
   <pre><code>$ make --help</code></pre>
   </div>

.. note::
   The above help output is automatically generated from the command-line interface.
   See the detailed command reference below for comprehensive usage information.

Build Commands
--------------

make build
~~~~~~~~~~

**Purpose**: Build Arkēs variants

**Usage**:

.. code-block:: bash

   make build [variant] [options]

**Description**:
Builds container images for Arkēs variants using Podman. This is the primary command for creating system images.

**Arguments**:
- ``variant``: Name of variant to build (base, atomic, gnome, eeems, etc.)

**Options**:
- ``--push``: Push image to registry after building
- ``--no-cache``: Build without using cache
- ``--pull``: Always pull base images

**Examples**:

.. code-block:: bash

   # Build base variant
   make build base
   
   # Build and push atomic variant
   make build atomic --push
   
   # Build without cache
   make build gnome --no-cache

---

make manifest
~~~~~~~~~~~~~

**Purpose**: Manage variant manifests

**Usage**:

.. code-block:: bash

   make manifest [action] [options]

**Description**:
Creates and manages multi-architecture container manifests for variant distribution.

**Actions**:
- ``create``: Create new manifest
- ``push``: Push manifest to registry
- ``inspect``: Show manifest details

**Examples**:

.. code-block:: bash

   # Create manifest for atomic variant
   make manifest create atomic
   
   # Push manifest
   make manifest push atomic

---

Container Management Commands
-----------------------------

make pull
~~~~~~~~~

**Purpose**: Pull container images from registry

**Usage**:

.. code-block:: bash

   make pull [image] [options]

**Description**:
Downloads container images from configured registries.

**Examples**:

.. code-block:: bash

   # Pull base image
   make pull arkes:base
   
   # Pull latest variants
   make pull arkes:atomic arkes:gnome

---

make push
~~~~~~~~~

**Purpose**: Push container images to registry

**Usage**:

.. code-block:: bash

   make push [image] [options]

**Description**:
Uploads built container images to configured registries.

**Examples**:

.. code-block:: bash

   # Push atomic variant
   make push arkes:atomic
   
   # Push multiple variants
   make push arkes:base arkes:gnome

---

System Commands
---------------

make os
~~~~~~~

**Purpose**: Execute operating system commands

**Usage**:

.. code-block:: bash

   make os [command] [options]

**Description**:
Interface for system management operations including installation, updates, and maintenance.

**Available Commands**:
- ``install``: Perform system installation (requires arguments)
- ``upgrade``: Update system
- ``status``: Show system status
- ``revert``: Rollback to previous deployment
- ``checkupdates``: Check for available updates
- ``build``: Build from Systemfile
- ``unlock``: Make system mutable
- ``prune``: Clean old deployments
- ``du``: Show disk usage

**Examples**:

.. code-block:: bash

   # Check system status
   make os status
   
   # Check for updates
   make os checkupdates
   
   # Upgrade system
   make os upgrade
   
   # Install system (requires arguments)
   sudo make os install --system-partition /dev/sda2 --boot-partition /dev/sda1

---

Development Commands
--------------------

make shell
~~~~~~~~~~

**Purpose**: Open interactive shell in container

**Usage**:

.. code-block:: bash

   make shell [variant] [options]

**Description**:
Opens an interactive shell in the specified variant container for development and debugging.

**Examples**:

.. code-block:: bash

   # Shell in base variant
   make shell base
   
   # Shell with custom command
   make shell atomic --command /bin/bash

---

make run
~~~~~~~~

**Purpose**: Run commands in containers

**Usage**:

.. code-block:: bash

   make run [variant] [command] [options]

**Description**:
Executes commands within variant containers for testing and development.

**Examples**:

.. code-block:: bash

   # Run command in atomic variant
   make run atomic "pacman -Syu"
   
   # Interactive session
   make run gnome --interactive

---

make builder-shell
~~~~~~~~~~~~~~~~~~

**Purpose**: Open builder container shell

**Usage**:

.. code-block:: bash

   make builder-shell [options]

**Description**:
Opens a shell in the build environment container with all development tools available.

---

Utility Commands
----------------

make check
~~~~~~~~~~

**Purpose**: Perform system checks

**Usage**:

.. code-block:: bash

   make check [options]

**Description**:
Runs various system checks to validate the build environment and configuration.

---

make scan
~~~~~~~~~

**Purpose**: Security scanning

**Usage**:

.. code-block:: bash

   make scan [image] [options]

**Description**:
Performs security vulnerability scanning on container images.

---

make hash
~~~~~~~~~

**Purpose**: Generate content hashes

**Usage**:

.. code-block:: bash

   make hash [path] [options]

**Description**:
Generates cryptographic hashes for files and directories used in builds.

---

make inspect
~~~~~~~~~~~~

**Purpose**: Inspect container images

**Usage**:

.. code-block:: bash

   make inspect [image] [options]

**Description**:
Displays detailed information about container images including layers, configuration, and metadata.

---

make config
~~~~~~~~~~~

**Purpose**: Configuration management

**Usage**:

.. code-block:: bash

   make config [action] [options]

**Description**:
Manages build system configuration and settings.

---

make iso
~~~~~~~~

**Purpose**: Create ISO images

**Usage**:

.. code-block:: bash

   make iso [variant] [options]

**Description**:
Generates bootable ISO images from variant containers for installation media.

---

make workflow
~~~~~~~~~~~~~

**Purpose**: Workflow management

**Usage**:

.. code-block:: bash

   make workflow [action] [options]

**Description**:
Manages build workflows and CI/CD processes.

---

Command Summary Table
---------------------

+----------------+-------------------+-------------------+----------+
| Command        | Purpose           | Context           | Section  |
+================+===================+===================+==========+
| make build     | Build variants    | Development       | Build    |
+----------------+-------------------+-------------------+----------+
| make manifest  | Manage manifests  | Development       | Build    |
+----------------+-------------------+-------------------+----------+
| make pull      | Pull images       | Development       | Container|
+----------------+-------------------+-------------------+----------+
| make push      | Push images       | Development       | Container|
+----------------+-------------------+-------------------+----------+
| make os        | System management | System/Dev        | System   |
+----------------+-------------------+-------------------+----------+
| make shell     | Container shell   | Development       | Dev      |
+----------------+-------------------+-------------------+----------+
| make run       | Run in container  | Development       | Dev      |
+----------------+-------------------+-------------------+----------+
| make check     | System checks     | Development       | Utility  |
+----------------+-------------------+-------------------+----------+
| make scan      | Security scan     | Development       | Utility  |
+----------------+-------------------+-------------------+----------+
| make iso       | Create ISO        | Development       | Utility  |
+----------------+-------------------+-------------------+----------+

Common Development Workflows
----------------------------

Building All Variants
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Build core variants
   make build base
   make build atomic
   make build gnome
   make build eeems

Testing Variants
~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Test atomic variant
   make shell atomic
   # Run tests inside container
   
   # Test with specific command
   make run gnome "echo 'Testing GNOME variant'"

Container Management
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Pull latest images
   make pull arkes:base
   
   # Build and push new version
   make build atomic --push
   make manifest push atomic

System Operations
~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Check system status
   make os status
   
   # Create ISO for testing
   make iso atomic
   
   # Security scan
   make scan arkes:atomic

For detailed system management commands, see the ``make os`` section above or refer to :doc:`user-guide`.
