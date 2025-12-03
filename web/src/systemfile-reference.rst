====================
Systemfile Reference
====================

Complete reference for Systemfile configuration. Systemfile is the primary method for customizing your Arkēs system - defining packages, repositories, and system configuration.

What is Systemfile?
-------------------

Systemfile is a **Dockerfile-like configuration** that defines how your system is built. It's stored at ``/etc/system/Systemfile`` and processed during system builds.

**Key Concepts**:

- **Declarative**: Define what you want, not how to install it
- **Immutable**: Changes require rebuilding system
- **Atomic**: All changes applied together or not at all
- **Version controlled**: Track changes to your system configuration

**Location**: ``/etc/system/Systemfile``

**Processing**: Systemfile is processed when you run ``os build``

Basic Structure
---------------

Systemfile uses standard Dockerfile syntax with system-specific helper scripts:

.. code-block:: dockerfile

   # Base variant to build from
   FROM arkes:atomic
   
   # System configuration
   RUN \
     HOSTNAME=myhost \
     TIMEZONE=America/New_York \
     KEYMAP=us \
     FONT=ter-124n \
     LANGUAGE=en_US \
     ENCODING=UTF-8 \
     /usr/lib/system/setup_machine

**Components**:
- **FROM**: Base variant (rootfs, base, atomic, gnome, eeems)
- **RUN**: Execute system commands
- **ARG**: Build-time variables
- **Comments**: Lines starting with ``#``

System Configuration
--------------------

Basic System Settings
~~~~~~~~~~~~~~~~~~~~~

Configure essential system settings:

.. code-block:: dockerfile

   FROM arkes:base

   RUN \
     HOSTNAME=arkes-system \
     TIMEZONE=Canada/Mountain \
     KEYMAP=us \
     FONT=ter-124n \
     LANGUAGE=en_CA \
     ENCODING=UTF-8 \
     /usr/lib/system/setup_machine

**Available Settings**:
- **HOSTNAME**: System hostname
- **TIMEZONE**: Timezone (e.g., America/New_York)
- **KEYMAP**: Keyboard layout (e.g., us, dvorak)
- **FONT**: Console font (e.g., ter-124n, lat2-16)
- **LANGUAGE**: Locale language (e.g., en_US, en_CA)
- **ENCODING**: Character encoding (e.g., UTF-8)

Package Management
------------------

Installing Official Packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``/usr/lib/system/install_packages`` to install Arch Linux packages:

.. code-block:: dockerfile

   FROM arkes:base

   # Install single package
   RUN /usr/lib/system/install_packages vim

   # Install multiple packages
   RUN /usr/lib/system/install_packages \
       git \
       htop \
       tmux \
       fastfetch

   # Install with specific options
   RUN /usr/lib/system/install_packages \
       --asdeps \
       --needed \
       package-name

**Common Package Categories**:

.. code-block:: dockerfile

   # Development tools
   RUN /usr/lib/system/install_packages \
       git \
       vim \
       code \
       make \
       gcc

   # System utilities
   RUN /usr/lib/system/install_packages \
       htop \
       btop \
       neofetch \
       tree \
       rsync

   # Network tools
   RUN /usr/lib/system/install_packages \
       curl \
       wget \
       nmap \
       wireshark-cli

   # Multimedia
   RUN /usr/lib/system/install_packages \
       vlc \
       gimp \
       inkscape

Adding Package Repositories
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add custom repositories with ``/usr/lib/system/add_pacman_repository``:

.. code-block:: dockerfile

   FROM arkes:atomic

   # Add repository with GPG key
   RUN /usr/lib/system/add_pacman_repository \
       --key=A64228CCD26972801C2CE6E3EC931EA46980BA1B \
       --server=https://repo.eeems.codes/\$repo \
       --server=https://repo.eeems.website/\$repo \
       eeems-linux

   # Install repository keyring
   RUN /usr/lib/system/install_packages eeems-keyring

   # Install packages from repository
   RUN /usr/lib/system/install_packages custom-package

**Repository Options**:

- ``--key=KEY_ID``: GPG key fingerprint
- ``--keyfile=URL``: GPG key file URL
- ``--server=URL``: Repository server URL
- ``--name=NAME``: Repository name

Installing AUR Packages
~~~~~~~~~~~~~~~~~~~~~~~

Use ``/usr/lib/system/install_aur_packages`` to install AUR packages:

.. code-block:: dockerfile

   FROM arkes:atomic

   # Install AUR package (latest)
   RUN /usr/lib/system/install_aur_packages visual-studio-code-bin

   # Install AUR package (specific git ref)
   RUN /usr/lib/system/install_aur_packages \
       package-name=git-ref

   # Install multiple AUR packages
   RUN /usr/lib/system/install_aur_packages \
       visual-studio-code-bin \
       spotify \
       discord

**AUR Options**:

- **package-name**: Install latest version
- **package-name=git-ref**: Install specific git reference
- **package-name=tag**: Install specific tag

**Popular AUR Packages**:

.. code-block:: dockerfile

   # Development tools
   RUN /usr/lib/system/install_aur_packages \
       visual-studio-code-bin \
       jetbrains-toolbox \
       postman-bin

   # Communication
   RUN /usr/lib/system/install_aur_packages \
       discord \
       slack-desktop \
       zoom

   # Multimedia
   RUN /usr/lib/system/install_aur_packages \
       spotify \
       spotube \
       obs-studio

Custom Commands
---------------

You can run any custom commands in Systemfile:

.. code-block:: dockerfile

   FROM arkes:base

   # Custom system setup
   RUN echo "Custom system setup" && \
       systemctl enable custom-service && \
       useradd -m customuser

   # File operations
   RUN mkdir -p /opt/custom-app && \
       echo "export CUSTOM_VAR=value" >> /etc/environment

   # Download and install custom software
   RUN curl -L https://example.com/app.tar.gz | tar -xz -C /opt/

**Best Practices**:

- Use ``&&`` to chain commands
- Quote paths with spaces
- Test commands in unlocked system first
- Use absolute paths when possible

Advanced Configuration
----------------------

Conditional Installation
~~~~~~~~~~~~~~~~~~~~~~~~

Use ARG for conditional builds:

.. code-block:: dockerfile

   FROM arkes:base

   ARG INCLUDE_DEV_TOOLS=false
   ARG INCLUDE_MULTIMEDIA=false

   # Conditional development tools
   RUN if [ "$INCLUDE_DEV_TOOLS" = "true" ]; then \
       /usr/lib/system/install_packages git vim make gcc; \
       fi

   # Conditional multimedia
   RUN if [ "$INCLUDE_MULTIMEDIA" = "true" ]; then \
       /usr/lib/system/install_packages vlc gimp; \
       fi

**Build with arguments**:

.. code-block:: bash

   os build --build-arg INCLUDE_DEV_TOOLS=true

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Set system-wide environment variables:

.. code-block:: dockerfile

   FROM arkes:base

   # Set environment variables
   RUN echo "export EDITOR=vim" >> /etc/environment && \
       echo "export BROWSER=firefox" >> /etc/environment && \
       echo "export JAVA_HOME=/usr/lib/jvm/default" >> /etc/environment

Service Configuration
~~~~~~~~~~~~~~~~~~~~~

Enable and configure systemd services:

.. code-block:: dockerfile

   FROM arkes:base

   # Enable services
   RUN systemctl enable sshd && \
       systemctl enable docker && \
       systemctl enable NetworkManager

   # Create custom service
   RUN echo "[Unit]
   Description=Custom Service
   After=network.target

   [Service]
   ExecStart=/usr/bin/custom-app
   Restart=always

   [Install]
   WantedBy=multi-user.target" > /etc/systemd/system/custom.service && \
       systemctl enable custom

Complete Examples
-----------------

Example 1: Development Workstation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: dockerfile

   FROM arkes:atomic

   # System configuration
   RUN \
     HOSTNAME=dev-workstation \
     TIMEZONE=America/New_York \
     KEYMAP=us \
     FONT=ter-124n \
     LANGUAGE=en_US \
     ENCODING=UTF-8 \
     /usr/lib/system/setup_machine

   # Development tools
   RUN /usr/lib/system/install_packages \
       git \
       vim \
       code \
       make \
       gcc \
       python \
       nodejs \
       docker

   # AUR development tools
   RUN /usr/lib/system/install_aur_packages \
       visual-studio-code-bin \
       jetbrains-toolbox \
       postman-bin

   # Custom repositories
   RUN /usr/lib/system/add_pacman_repository \
       --key=A64228CCD26972801C2CE6E3EC931EA46980BA1B \
       --server=https://repo.eeems.codes/\$repo \
       eeems-linux && \
       /usr/lib/system/install_packages eeems-keyring

Example 2: Minimal Server
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: dockerfile

   FROM arkes:base

   # Server configuration
   RUN \
     HOSTNAME=web-server \
     TIMEZONE=UTC \
     KEYMAP=us \
     /usr/lib/system/setup_machine

   # Server packages
   RUN /usr/lib/system/install_packages \
       nginx \
       mariadb \
       php \
       ufw \
       fail2ban

   # Enable services
   RUN systemctl enable nginx && \
       systemctl enable mariadb && \
       systemctl enable ufw && \
       systemctl enable fail2ban

   # Security configuration
   RUN ufw allow 22/tcp && \
       ufw allow 80/tcp && \
       ufw allow 443/tcp && \
       ufw --force enable

Example 3: Gaming Desktop
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: dockerfile

   FROM arkes:atomic-nvidia

   # Gaming configuration
   RUN \
     HOSTNAME=gaming-rig \
     TIMEZONE=America/Los_Angeles \
     KEYMAP=us \
     FONT=ter-124n \
     LANGUAGE=en_US \
     ENCODING=UTF-8 \
     /usr/lib/system/setup_machine

   # Gaming tools
   RUN /usr/lib/system/install_packages \
       steam \
       lutris \
       wine \
       gamemode \
       mangohud

   # AUR gaming tools
   RUN /usr/lib/system/install_aur_packages \
       heroic-games-launcher-bin \
       bottles \
       protonup-qt

   # Performance optimizations
   RUN echo "vm.swappiness=10" >> /etc/sysctl.conf && \
       echo "kernel.sched_migration_cost_ns=5000000" >> /etc/sysctl.conf

Best Practices
--------------

1. **Start Simple**: Begin with minimal changes and build up
2. **Test First**: Use ``os unlock`` to test changes before building
3. **Version Control**: Keep your Systemfile in git
4. **Document**: Comment complex configurations
5. **Modular**: Break complex setups into logical sections
6. **Security**: Only add necessary repositories and packages

Common Pitfalls
----------------

1. **Missing Dependencies**: AUR packages may need manual dependencies
2. **Repository Keys**: Ensure GPG keys are properly added
3. **Service Conflicts**: Don't enable conflicting services
4. **Path Issues**: Use absolute paths in custom commands
5. **Build Failures**: Check logs for specific error messages

Troubleshooting
---------------

**Build Failures**:

.. code-block:: bash

   # Check build logs
   journalctl -xe
   
   # Test commands manually
   sudo os unlock
   # Run failing command manually
   sudo reboot

**Package Issues**:

.. code-block:: bash

   # Check package availability
   pacman -Ss package-name
   
   # Check AUR package
   curl https://aur.archlinux.org/packages/package-name

**Repository Issues**:

.. code-block:: bash

   # Test repository
   curl -I https://repo.example.com/core.db
   
   # Check GPG key
   gpg --recv-keys KEY_ID

For more advanced customization, see :doc:`creating-variants`.
