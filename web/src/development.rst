=================
Development Guide
=================

Guide for developing Arkēs, contributing to the project, and understanding the build system architecture.

Development Environment
-----------------------

Getting Started
~~~~~~~~~~~~~~~

1. **Clone the repository**:

   .. code-block:: bash

      git clone https://github.com/Eeems/arkes.git
      cd arkes

2. **Install dependencies**:

   .. code-block:: bash

      # Python dependencies
      pip install -r requirements.txt
      
      # System dependencies (Arch Linux)
      sudo pacman -S podman python make

3. **Set up development environment**:

   .. code-block:: bash

      # Test the build system
      python make.py --help

Project Structure
~~~~~~~~~~~~~~~~~

.. code-block:: text

   arkes/
   ├── make/                    # Python build system
   │   ├── __main__.py         # CLI entry point
   │   ├── build.py             # Build commands
   │   ├── manifest.py          # Variant management
   │   ├── os.py               # OS commands
   │   └── [other modules]
   ├── variants/                # Variant definitions
   │   ├── rootfs.Containerfile
   │   ├── base.Containerfile
   │   ├── atomic.Containerfile
   │   ├── gnome.Containerfile
   │   └── eeems.Containerfile
   ├── overlay/                 # System overlays
   │   ├── base/               # Base system overlay
   │   ├── atomic/             # Atomic desktop overlay
   │   ├── gnome/              # GNOME overlay
   │   └── eeems/             # EEEMS overlay
   ├── templates/               # Build templates
   │   ├── nvidia.Containerfile
   │   ├── system76.Containerfile
   │   └── slim.Containerfile
   └── tools/                  # Build tools
       └── builder/             # Container builder

Build System Architecture
-------------------------

Python CLI System
~~~~~~~~~~~~~~~~~

The build system is implemented in Python as a modular CLI tool:

**Core Components**:
- **make/__main__.py**: CLI entry point and argument parsing
- **make/[module].py**: Individual command modules
- **Dynamic loading**: Automatically discovers and loads commands

**Command Structure**:

.. code-block:: python

   # Example command module
   kwds = {"help": "Command description"}

   def register(parser):
       # Register command arguments
       parser.add_argument("option", help="Option description")

   def command(args):
       # Command implementation
       print("Executing command")

**Available Commands**:
- ``build``: Build variants
- ``manifest``: Manage variant manifests
- ``os``: Run OS commands
- ``pull``: Pull container images
- ``push``: Push container images
- ``scan``: Security scanning
- ``check``: System checks

Variant Build System
~~~~~~~~~~~~~~~~~~~~

Variants are built using container technology:

**Build Process**:
1. **Read Containerfile** for variant definition
2. **Apply templates** (nvidia, system76, etc.)
3. **Build container image** using Podman
4. **Create overlay** from configuration files
5. **Generate ISO** (for installable variants)

**Containerfile Processing**:
- **Dependency resolution**: Handle ``# x-depends`` directives
- **Template application**: Apply template modifications
- **Build arguments**: Pass required build arguments
- **Layer optimization**: Optimize container layers

**Template System**:
- **nvidia**: Adds NVIDIA drivers and CUDA support
- **system76**: Adds System76 hardware integration
- **slim**: Reduces footprint for containers

Overlay System
~~~~~~~~~~~~~~

Overlays provide system configuration files:

**Overlay Structure**:

.. code-block:: text

   overlay/variant/
   ├── etc/
   │   ├── system/           # System configuration
   │   ├── systemd/          # Systemd units
   │   ├── pacman.d/         # Package manager config
   │   └── [config dirs]
   └── usr/
       ├── bin/               # Custom binaries
       ├── lib/               # Custom libraries
       └── share/            # Shared data

**Overlay Processing**:
- **File merging**: Combine with base system
- **Priority handling**: Override base files
- **Service enablement**: Auto-enable systemd services
- **Configuration injection**: Add system configs

Contributing Guidelines
-----------------------

Code Style
~~~~~~~~~~

**Python Code**:
- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Document functions and classes
- Keep modules focused and small

**Example**:

.. code-block:: python

   """Module for building variants."""

   from typing import Optional
   from argparse import Namespace

   def build_variant(variant: str, options: Optional[Namespace] = None) -> bool:
       """Build a specific variant.
       
       Args:
           variant: Name of variant to build
           options: Optional build options
           
       Returns:
           True if build successful, False otherwise
       """
       # Implementation
       return True

**Containerfile Style**:
- Use consistent formatting
- Document complex operations
- Group related packages
- Use build arguments appropriately

**Example**:

.. code-block:: dockerfile

   # syntax=docker/dockerfile:1.4
   # x-depends=base
   # x-templates=nvidia
   ARG HASH

   FROM arkes:base

   ARG \
     VARIANT="ExampleVariant" \
     VARIANT_ID="example"

   # Development tools
   RUN /usr/lib/system/package_layer \
       git \
       vim \
       make

Testing
~~~~~~~

**Testing**:

.. code-block:: bash

   # Test variant builds
   make base
   make atomic
   make gnome

   # Test OS commands
   python make.py os status

**Integration Testing**:

.. code-block:: bash

   # Test variant builds
   make base
   make atomic
   make gnome

   # Test template combinations
   make atomic-nvidia
   make gnome-system76

   # Test OS commands
   python make.py os status

**Container Testing**:

.. code-block:: bash

   # Test built containers
   podman run --rm arkes:base echo "Base variant works"
   podman run --rm arkes:atomic echo "Atomic variant works"



Build System Development
------------------------

Adding New Commands
~~~~~~~~~~~~~~~~~~~

1. **Create new module** in ``make/`` directory:

.. code-block:: python

   # make/mycommand.py
   from argparse import ArgumentParser, Namespace

   kwds = {"help": "Description of my command"}

   def register(parser: ArgumentParser):
       """Register command arguments."""
       parser.add_argument(
           "argument",
           help="Argument description"
       )

   def command(args: Namespace):
       """Execute command."""
       print(f"Executing mycommand with: {args.argument}")

2. **Test the command**:

   .. code-block:: bash

      python make.py mycommand test-argument

3. **Add documentation** for the new command

Adding New Variants
~~~~~~~~~~~~~~~~~~~

1. **Create Containerfile**:

.. code-block:: dockerfile

   # syntax=docker/dockerfile:1.4
   # x-depends=base
   ARG HASH

   FROM arkes:base

   ARG \
     VARIANT="NewVariant" \
     VARIANT_ID="newvariant"

   RUN /usr/lib/system/package_layer \
       package-1 \
       package-2

2. **Create overlay directory**:

.. code-block:: bash

   mkdir -p overlay/newvariant/etc/system

3. **Add Systemfile**:

.. code-block:: dockerfile

   FROM arkes:base

   RUN \
     HOSTNAME=newvariant \
     TIMEZONE=UTC \
     KEYMAP=us \
     /usr/lib/system/setup_machine

4. **Update build system** to recognize new variant

5. **Add tests** for new variant

Adding New Templates
~~~~~~~~~~~~~~~~~~~~

1. **Create template Containerfile**:

.. code-block:: dockerfile

   # syntax=docker/dockerfile:1.4
   ARG HASH

   # Template modifications
   RUN /usr/lib/system/package_layer \
       template-package-1 \
       template-package-2

2. **Update template processing** in build system
3. **Document template features**
4. **Add tests** for template combinations

CI/CD Integration
-----------------

GitHub Actions
~~~~~~~~~~~~~~

The project uses GitHub Actions for automated builds:

**Build Workflow** (``.github/workflows/build.yaml``):
- Builds all variants
- Runs tests
- Creates container images
- Generates ISO files

**Publish Workflow** (``.github/workflows/publish.yaml``):
- Publishes images to registry
- Creates GitHub releases
- Updates documentation

**Web Workflow** (``.github/workflows/web.yaml``):
- Builds documentation
- Deploys to GitHub Pages
- Updates documentation site

Local Development
~~~~~~~~~~~~~~~~~

**Run CI locally**:

.. code-block:: bash

   # Install act (local GitHub Actions runner)
   curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
   
   # Run workflow locally
   act -j build

**Test builds**:

.. code-block:: bash

   # Build specific variant
   make base
   
   # Build with debug output
   make base --debug
   
   # Clean build
   make clean && make base

Security Considerations
-----------------------

Container Security
~~~~~~~~~~~~~~~~~~

- Use minimal base images
- Scan images for vulnerabilities
- Keep dependencies updated
- Limit container privileges
- Use non-root users when possible

System Security
~~~~~~~~~~~~~~~

- Validate all inputs
- Use secure defaults
- Implement proper access controls
- Regular security audits
- Update security patches promptly

Development Security
~~~~~~~~~~~~~~~~~~~~

- Use signed commits
- Review all code changes
- Implement proper secret management
- Use dependency scanning
- Follow secure coding practices

For more information about system architecture, see :doc:`architecture`.
