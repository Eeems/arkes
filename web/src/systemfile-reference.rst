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

- **FROM**: Base :doc:`variant <variants>` (rootfs, base, atomic, gnome, eeems)
- **RUN**: Execute system commands

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

Installing Packages
~~~~~~~~~~~~~~~~~~~

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
   RUN /usr/lib/system/install_aur_packages \
       visual-studio-code-bin

   # Install multiple AUR packages
   RUN /usr/lib/system/install_aur_packages \
       visual-studio-code-bin \
       spotify \
       discord

Custom Commands
---------------

You can run any custom commands in Systemfile:

.. code-block:: dockerfile

   FROM arkes:base

   # Custom system setup
   RUN <<EOT
       set -ex
       echo "Custom system setup"
       systemctl enable custom-service
       useradd -m customuser
   EOT

   # File operations
   RUN <<EOT
       set -ex
       mkdir -p /opt/custom-app
       echo "export CUSTOM_VAR=value" >> /etc/environment
   EOT

   # Download and install custom software
   RUN curl -L https://example.com/app.tar.gz | tar -xz -C /opt/

**Best Practices**:

- Use heredocs to chain commands
- Quote paths with spaces
- Test commands in unlocked system first
- Use absolute paths when possible

Advanced Configuration
----------------------

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Set system-wide environment variables:

.. code-block:: dockerfile

   FROM arkes:base

   # Set environment variables
   RUN <<EOT
       set -ex
       echo "export EDITOR=vim" >> /etc/environment
       echo "export BROWSER=firefox" >> /etc/environment
       echo "export JAVA_HOME=/usr/lib/jvm/default" >> /etc/environment
   EOT

Service Configuration
~~~~~~~~~~~~~~~~~~~~~

Enable and configure systemd services:

.. code-block:: dockerfile

   FROM arkes:base

   # Enable services
   RUN systemctl enable \
       sshd \
       docker \
       NetworkManager

   # Create custom service
   RUN <<EOT
       set -ex
       cat > /etc/systemd/system/custom.service << 'EOF'
   [Unit]
   Description=Custom Service
   After=network.target

   [Service]
   ExecStart=/usr/bin/custom-app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   EOF
       systemctl enable custom
   EOT

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
   RUN <<EOT
       set -ex
       /usr/lib/system/add_pacman_repository \
         --key=A64228CCD26972801C2CE6E3EC931EA46980BA1B \
         --server=https://repo.eeems.codes/\$repo \
         eeems-linux
       /usr/lib/system/install_packages eeems-keyring
   EOT

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
   RUN systemctl enable \
       nginx \
       mariadb \
       ufw \
       fail2ban

   # Security configuration
   RUN <<EOT
       set -ex
       ufw allow 22/tcp
       ufw allow 80/tcp
       ufw allow 443/tcp
       ufw --force enable
   EOT

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
   RUN <<EOT
       set -ex
       echo "vm.swappiness=10" >> /etc/sysctl.conf
       echo "kernel.sched_migration_cost_ns=5000000" >> /etc/sysctl.conf
   EOT

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
