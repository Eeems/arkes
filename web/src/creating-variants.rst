=================
Creating Variants
=================

Complete guide to creating custom Arkēs variants. This guide covers creating new variants, using templates, and integrating with the build system.

Understanding Variants
----------------------

A **variant** is a specific configuration of Arkēs built for a particular use case. Each variant is defined by:

- **Containerfile**: Build instructions and package definitions
- **Overlay directory**: System configuration files
- **Dependencies**: Base variant(s) it builds upon
- **Templates**: Optional modifications (NVIDIA, System76, etc.)

**Variant Hierarchy**:
```
rootfs (base)
├── base (server/container)
├── atomic (Wayland desktop)
├── gnome (GNOME desktop)
└── eeems (personalized desktop)
```

**Templates** create variant combinations:
- **nvidia**: Adds NVIDIA driver support
- **system76**: Adds System76 hardware integration
- **slim**: Reduces footprint for containers

Variant Structure
-----------------

Directory Layout
~~~~~~~~~~~~~~~~

Each variant follows this structure:

.. code-block:: text

   variants/
   ├── myvariant.Containerfile
   └── overlay/
       └── myvariant/
           ├── etc/
           │   ├── system/
           │   │   └── Systemfile
           │   └── [other config dirs]
           └── usr/
               └── [custom binaries/scripts]

**Essential Files**:
- **Containerfile**: Build instructions
- **overlay/etc/system/Systemfile**: System configuration
- **overlay/**: Additional configuration files

Containerfile Syntax
~~~~~~~~~~~~~~~~~~~~

Containerfile uses Dockerfile syntax with Arkēs-specific directives:

.. code-block:: dockerfile

   # syntax=docker/dockerfile:1.4
   # x-depends=base
   # x-templates=nvidia,system76
   ARG HASH

   FROM arkes:base

   ARG \
     VARIANT="MyVariant" \
     VARIANT_ID="myvariant"

   RUN /usr/lib/system/package_layer \
       package-1 \
       package-2 \
       package-3

**Directives**:
- ``# x-depends=variant``: Base variant dependency
- ``# x-templates=template1,template2``: Templates to apply
- ``ARG HASH``: Required build argument
- ``FROM arkes:variant``: Base variant to build from
- ``ARG VARIANT``: Variant display name
- ``ARG VARIANT_ID``: Variant identifier

Creating a Basic Variant
------------------------

Step 1: Create Containerfile
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``variants/myvariant.Containerfile``:

.. code-block:: dockerfile

   # syntax=docker/dockerfile:1.4
   # x-depends=base
   ARG HASH

   FROM arkes:base

   ARG \
     VARIANT="MyVariant" \
     VARIANT_ID="myvariant"

   RUN /usr/lib/system/package_layer \
       htop \
       tree \
       rsync \
       curl \
       wget

**Explanation**:
- Builds from ``base`` variant
- Adds utility packages
- Sets variant name and ID

Step 2: Create Overlay Directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create overlay structure:

.. code-block:: bash

   mkdir -p variants/overlay/myvariant/etc/system

Step 3: Create Systemfile
~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``variants/overlay/myvariant/etc/system/Systemfile``:

.. code-block:: dockerfile

   FROM arkes:base

   RUN \
     HOSTNAME=myvariant \
     TIMEZONE=America/New_York \
     KEYMAP=us \
     FONT=ter-124n \
     LANGUAGE=en_US \
     ENCODING=UTF-8 \
     /usr/lib/system/setup_machine

   RUN /usr/lib/system/install_packages \
       vim \
       git \
       tmux

Step 4: Add to Build System
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add variant to build configuration (see build system integration below).

Step 5: Build Variant
~~~~~~~~~~~~~~~~~~~~~

Build your new variant:

.. code-block:: bash

   # Using make system
   make myvariant
   
   # Or directly with podman
   podman build -t arkes:myvariant -f variants/myvariant.Containerfile .

Advanced Variant Creation
-------------------------

Using Templates
~~~~~~~~~~~~~~~

Apply templates to your variant:

.. code-block:: dockerfile

   # syntax=docker/dockerfile:1.4
   # x-depends=atomic
   # x-templates=nvidia,system76
   ARG HASH

   FROM arkes:atomic

   ARG \
     VARIANT="MyGamingVariant" \
     VARIANT_ID="mygaming"

   RUN /usr/lib/system/package_layer \
       steam \
       lutris \
       gamemode

This creates:
- **mygaming**: Base variant
- **mygaming-nvidia**: With NVIDIA support
- **mygaming-system76**: With System76 support
- **mygaming-nvidia-system76**: With both

Custom Repositories
~~~~~~~~~~~~~~~~~~~

Add custom repositories to your variant:

.. code-block:: dockerfile

   # syntax=docker/dockerfile:1.4
   # x-depends=base
   ARG HASH

   FROM arkes:base

   ARG \
     VARIANT="CustomRepoVariant" \
     VARIANT_ID="customrepo"

   RUN /usr/lib/system/add_pacman_repository \
       --key=A64228CCD26972801C2CE6E3EC931EA46980BA1B \
       --server=https://repo.eeems.codes/\$repo \
       eeems-linux && \
       /usr/lib/system/install_packages eeems-keyring

   RUN /usr/lib/system/package_layer \
       custom-package-1 \
       custom-package-2

AUR Packages
~~~~~~~~~~~~

Include AUR packages in your variant:

.. code-block:: dockerfile

   # syntax=docker/dockerfile:1.4
   # x-depends=atomic
   ARG HASH

   FROM arkes:atomic

   ARG \
     VARIANT="DevVariant" \
     VARIANT_ID="dev"

   RUN /usr/lib/system/install_aur_packages \
       visual-studio-code-bin \
       discord \
       spotify

   RUN /usr/lib/system/package_layer \
       git \
       make \
       gcc

Custom Configuration
~~~~~~~~~~~~~~~~~~~~

Add custom configuration files:

.. code-block:: bash

   # Create custom configuration
   mkdir -p variants/overlay/myvariant/etc/default
   cat > variants/overlay/myvariant/etc/default/custom-setting << 'EOF'
   CUSTOM_VAR=value
   ANOTHER_SETTING=enabled
   EOF

   # Create custom service
   mkdir -p variants/overlay/myvariant/etc/systemd/system
   cat > variants/overlay/myvariant/etc/systemd/system/custom.service << 'EOF'
   [Unit]
   Description=Custom Service
   After=network.target

   [Service]
   ExecStart=/usr/bin/custom-app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   EOF

   # Enable service in Systemfile
   echo "RUN systemctl enable custom" >> variants/overlay/myvariant/etc/system/Systemfile

Build System Integration
------------------------

Adding to Make System
~~~~~~~~~~~~~~~~~~~~~

Integrate your variant with the Arkēs build system:

1. **Update make/manifest.py** (if it exists)
2. **Add to GitHub Actions** (if using CI/CD)
3. **Update documentation** with new variant

**Example GitHub Actions Update**:

.. yaml

   # In .github/workflows/build.yaml
   - name: Build myvariant
     run: |
       make myvariant

   - name: Build myvariant-nvidia
     run: |
       make myvariant-nvidia

Variant Naming Conventions
--------------------------

**Base Variant Names**:
- Use lowercase, descriptive names
- Avoid conflicts with existing variants
- Keep names relatively short

**Template Combinations**:
- ``variant-nvidia``: NVIDIA support
- ``variant-system76``: System76 support
- ``variant-nvidia-system76``: Both NVIDIA and System76

**Examples**:
- ``gaming`` → ``gaming-nvidia``
- ``server`` → ``server-slim``
- ``workstation`` → ``workstation-system76``

Testing Your Variant
--------------------

Local Testing
~~~~~~~~~~~~~

1. **Build variant locally**:

   .. code-block:: bash

      podman build -t arkes:myvariant -f variants/myvariant.Containerfile .

2. **Test in container**:

   .. code-block:: bash

      podman run -it arkes:myvariant

3. **Check packages**:

   .. code-block:: bash

      podman run arkes:myvariant pacman -Q

4. **Test Systemfile**:

   .. code-block:: bash

      podman run arkes:myvariant cat /etc/system/Systemfile

Integration Testing
~~~~~~~~~~~~~~~~~~~

1. **Create test ISO** (if supported)
2. **Install in VM** for full testing
3. **Test all template combinations**
4. **Verify hardware compatibility**

Quality Assurance
-----------------

Variant Checklist
~~~~~~~~~~~~~~~--

Before releasing your variant, ensure:

**Base Requirements**:
- [ ] Containerfile syntax is valid
- [ ] Required directives are present
- [ ] Variant name and ID are set
- [ ] Base dependency is correct

**Functionality**:
- [ ] All packages install correctly
- [ ] Systemfile processes without errors
- [ ] Services start properly
- [ ] Network configuration works
- [ ] User can login and use system

**Templates**:
- [ ] All template combinations build
- [ ] Template-specific features work
- [ ] No conflicts between templates

**Documentation**:
- [ ] Variant is documented
- [ ] Use cases are clear
- [ ] Installation instructions are provided
- [ ] Known limitations are listed

Example Variants
----------------

Example 1: Minimal Server Variant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Containerfile**:

.. code-block:: dockerfile

   # syntax=docker/dockerfile:1.4
   # x-depends=base
   # x-templates=slim
   ARG HASH

   FROM arkes:base

   ARG \
     VARIANT="MinimalServer" \
     VARIANT_ID="minimal-server"

   RUN /usr/lib/system/package_layer \
       nginx \
       ufw \
       fail2ban

**Use Case**: Lightweight web server with minimal footprint

**Template Combinations**:
- ``minimal-server`` (base)
- ``minimal-server-slim`` (ultra-minimal)

---

Example 2: Development Workstation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Containerfile**:

.. code-block:: dockerfile

   # syntax=docker/dockerfile:1.4
   # x-depends=atomic
   # x-templates=nvidia
   ARG HASH

   FROM arkes:atomic

   ARG \
     VARIANT="DevWorkstation" \
     VARIANT_ID="dev-workstation"

   RUN /usr/lib/system/install_aur_packages \
       visual-studio-code-bin \
       jetbrains-toolbox

   RUN /usr/lib/system/package_layer \
       docker \
       code \
       make \
       gcc \
       python

**Use Case**: Development workstation with NVIDIA GPU support

**Template Combinations**:
- ``dev-workstation`` (base)
- ``dev-workstation-nvidia`` (with NVIDIA)

---

Example 3: Multimedia Station
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Containerfile**:

.. code-block:: dockerfile

   # syntax=docker/dockerfile:1.4
   # x-depends=gnome
   # x-templates=nvidia
   ARG HASH

   FROM arkes:gnome

   ARG \
     VARIANT="MultimediaStation" \
     VARIANT_ID="multimedia"

   RUN /usr/lib/system/package_layer \
       kodi \
       vlc \
       gimp \
       inkscape \
       audacity

   RUN /usr/lib/system/install_aur_packages \
       spotify \
       discord

**Use Case**: Home multimedia and content creation

**Template Combinations**:
- ``multimedia`` (base)
- ``multimedia-nvidia`` (with GPU acceleration)

Publishing Your Variant
-----------------------

Sharing Your Variant
~~~~~~~~~~~~~~~~~~~~

1. **Fork Arkēs repository**
2. **Add your variant** to ``variants/`` directory
3. **Update documentation** with variant description
4. **Submit pull request**

**Variant Documentation Template**:

.. rst

   myvariant
   ==========

   **Use Case**: Brief description of intended use
   **Based on**: base variant
   **Templates**: Available templates

   Description
   -----------

   Detailed description of your variant, including:
   - Target audience
   - Key features
   - Special configurations
   - Hardware requirements

   Installation
   -----------

   Download and installation instructions.

   Template Variants
   ----------------

   List of template combinations and their purposes.

   Configuration
   ------------

   Any special configuration or setup required.

Community Guidelines
--------------------

**Variant Quality**:
- Test thoroughly before submitting
- Follow naming conventions
- Document clearly and completely
- Consider security implications

**Maintenance**:
- Keep variants updated with base changes
- Respond to user feedback
- Fix reported issues promptly
- Update documentation as needed
