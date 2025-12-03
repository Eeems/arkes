===
FAQ
===

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

What does "immutable" mean?
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Immutable means the core system files (in ``/usr``, ``/bin``, ``/lib``, ``/etc``) cannot be directly modified by users or applications.

**What's immutable**:
- System programs and libraries
- Core configuration files
- Package management system
- Boot loader and kernel

**What's writable**:
- User home directories (``/var/home``)
- User data (``/var/lib``, ``/var/cache``)
- Temporary files (``/var/tmp``)
- Application data

**Benefits**:
- **Reliability** - System files can't be accidentally corrupted
- **Security** - Malware can't modify core system
- **Consistency** - All systems start from identical base
- **Easy recovery** - Rollback from any issue

How do updates work?
~~~~~~~~~~~~~~~~~~~~

Updates in Arkēs are **atomic** - they either complete successfully or not at all.

**Update Process**:
1. **Download** new packages and updates
2. **Build** new system tree in parallel
3. **Verify** integrity of new system
4. **Deploy** on next reboot
5. **Keep** previous system for rollback

**Key Features**:
- **All-or-nothing** - No partial updates that break system
- **Background** - Updates happen while system is running
- **Automatic rollback** - Failed updates automatically revert
- **Multiple versions** - Keep several system versions

**Commands**:
- ``os checkupdates`` - Check for updates
- ``os upgrade`` - Perform update
- ``os revert`` - Make rollback permanent

Installation and Setup
----------------------

How do I install Arkēs?
~~~~~~~~~~~~~~~~~~~~~~~

1. **Download ISO** from https://github.com/Eeems/arkes/releases
2. **Create bootable USB**:

   .. code-block:: bash

      sudo dd if=arkes-atomic.iso of=/dev/sdX bs=4M status=progress sync

3. **Boot from USB** and run:

   .. code-block:: bash

      sudo os install

4. **Follow prompts** for disk setup, user creation, etc.

**Requirements**:
- UEFI firmware (no legacy BIOS)
- 64-bit processor
- 4GB RAM minimum (8GB recommended)
- 20GB storage minimum (30GB recommended)

Which variant should I choose?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**For Desktop Users**:
- **atomic** - Modern Wayland desktop (recommended)
- **gnome** - Traditional GNOME desktop
- **eeems** - Personalized with extra tools

**For Server/Container Use**:
- **base** - Essential server tools
- **rootfs** - Minimal base for custom builds

**Hardware-Specific**:
- Add **-nvidia** for NVIDIA graphics
- Add **-system76** for System76 hardware

**Examples**:
- Gaming desktop: ``atomic-nvidia``
- Traditional desktop: ``gnome``
- Development server: ``base``

Can I dual boot with other OSes?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Yes, Arkēs supports dual booting:

**Setup Process**:
1. **Install other OS first** (Windows, other Linux)
2. **Install Arkēs** - It will detect existing OS
3. **Bootloader** - Arkēs will configure dual boot

**Considerations**:
- **UEFI required** - Both OSes must use UEFI
- **Disk space** - Ensure enough space for both
- **Time sync** - May need to configure time settings
- **Boot order** - Configure in firmware/BIOS

**Switching OSes**:
- Use firmware boot menu to select OS
- Or configure bootloader timeout

System Customization
--------------------

How do I install packages?
~~~~~~~~~~~~~~~~~~~~~~~~~~

Arkēs uses multiple package management methods:

**System Packages** (through Systemfile):
Edit ``/etc/system/Systemfile`` to add system packages:

.. code-block:: dockerfile

   RUN /usr/lib/system/install_packages \
       vim \
       git \
       htop

Then rebuild and upgrade:

.. code-block:: bash

   os build
   os upgrade

**Desktop Applications** (Flatpak - recommended):

.. code-block:: bash

   # Install applications
   flatpak install org.mozilla.firefox
   flatpak install org.libreoffice.LibreOffice
   
   # Update applications
   flatpak update

**AUR Packages** (through Systemfile):

.. code-block:: dockerfile

   RUN /usr/lib/system/install_aur_packages \
       visual-studio-code-bin \
       discord

**Containers** (Podman):

.. code-block:: bash

   # Run applications in containers
   podman run -it firefox
   podman run -it ubuntu:latest

**Distrobox** (for running applications):

.. code-block:: bash

   # Install distrobox
   sudo pacman -S distrobox
   
   # Create container with your favorite distro
   distrobox create --image ubuntu:latest --name ubuntu-container
   distrobox enter ubuntu-container
   
   # Install applications inside container
   sudo apt update && sudo apt install firefox
   
   # Run applications with integration
   distrobox-export --app /usr/bin/firefox

**Important**: You don't need to ``os unlock`` to make changes through Systemfile. The unlock command is only for testing changes manually before committing them to Systemfile.

Can I modify system files directly?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**No** - Direct modification of immutable directories is not possible and not recommended.

**What happens if you try**:
- ``/usr``, ``/bin``, ``/lib``: Read-only filesystem
- ``/etc``: Managed through overlays and Systemfile
- Changes will be lost on reboot

**Proper way to customize**:
1. **Edit Systemfile** for system-level changes
2. **Use overlays** for configuration files
3. **User configuration** in home directory
4. **Containers** for isolated applications

**For testing only**:

.. code-block:: bash

   # Temporary mutable system (changes lost on reboot)
   sudo os unlock
   
   # Persistent changes until next upgrade
   sudo os unlock --hotfix

How do I customize the desktop?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Desktop customization depends on your variant:

**Atomic (Wayland/Niri)**:
- **Configuration**: ``~/.config/niri/config.kdl``
- **Status bar**: ``~/.config/waybar/config``
- **Style**: ``~/.config/waybar/style.css``
- **Launcher**: ``~/.config/fuzzel/fuzzel.ini``

**GNOME**:
- **Settings**: GNOME Settings application
- **Extensions**: GNOME Extensions app
- **Themes**: GNOME Tweaks application
- **Configuration**: ``~/.config/gnome-...`` directories

**General customization**:
- **Wallpapers**: ``~/Pictures/`` or system wallpapers
- **Icons**: ``~/.local/share/icons/``
- **Fonts**: ``~/.local/share/fonts/``
- **Terminal**: ``~/.config/`` for terminal emulator

**Application settings**:
- Store in standard ``~/.config/appname/`` locations
- Persist across updates (in writable directories)

Applications and Software
-------------------------

Can I install AUR packages?
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Yes** - AUR packages can be installed through Systemfile:

.. code-block:: dockerfile

   # Install latest version
   RUN /usr/lib/system/install_aur_packages package-name
   
   # Install specific version
   RUN /usr/lib/system/install_aur_packages package-name=git-ref

**Popular AUR packages**:
- **Development**: visual-studio-code-bin, jetbrains-toolbox
- **Communication**: discord, slack-desktop
- **Multimedia**: spotify, obs-studio

**Process**:
1. Add to Systemfile
2. Run ``os build``
3. Run ``os upgrade``

**Note**: AUR packages are built from source, so updates may take longer than official packages.

How do I run Windows applications?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Several options for Windows applications:

**Wine (through Systemfile)**:

.. code-block:: dockerfile

   RUN /usr/lib/system/install_packages wine

**Bottles (Flatpak - recommended)**:

.. code-block:: bash

   flatpak install com.usebottles.bottles

**Steam for Windows games**:

.. code-block:: dockerfile

   RUN /usr/lib/system/install_packages steam

**Crossover (Flatpak)**:

.. code-block:: bash

   flatpak install com.codeweavers.CrossOver

**Performance**: For best performance, use ``atomic-nvidia`` variant with NVIDIA graphics.

How do I run Docker containers?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Arkēs uses **Podman** instead of Docker, but they're compatible:

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

**Benefits of regular updates**:
- **Security** - Latest security patches
- **Features** - New functionality and improvements
- **Stability** - Bug fixes and optimizations
- **Compatibility** - Latest hardware support

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
- **Network issues** - Check internet connection
- **Disk space** - Free up space with ``os prune``
- **Power loss** - System will revert automatically
- **Package conflicts** - Check error messages

**Prevention**:
- **Stable internet** during updates
- **Sufficient disk space** (check with ``os du``)
- **Don't interrupt** update process

What if I can't boot?
~~~~~~~~~~~~~~~~~~~~~

Boot issues have several recovery options:

**Immediate Steps**:
1. **Try previous deployment** in boot menu
2. **Boot from USB installer** for recovery
3. **Check hardware** - RAM, disk connections

**Recovery from USB**:

1. **Boot Arkēs USB**
2. **Mount system** for data access
3. **Backup important data**
4. **Reinstall** if necessary

**Prevention**:
- **Don't modify** system files directly
- **Test updates** before important events
- **Keep backups** of important data

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

.. code-block:: bash

   # Clean containers
   podman system prune
   
   # Remove unused images
   podman image prune
   
   # Clean volumes
   podman volume prune

**Package cache cleanup** (if unlocked):

.. code-block:: bash

   sudo os unlock
   sudo pacman -Scc
   sudo reboot

**Regular maintenance**:
- **Weekly**: Check disk usage with ``os du``
- **Monthly**: Clean old deployments with ``os prune``
- **Quarterly**: Full container cleanup

**Space usage breakdown**:
- **Deployments**: System versions (keep 2-3)
- **Containers**: Images and containers
- **User data**: Documents, downloads, etc.
- **Cache**: Package and application cache

For more detailed troubleshooting, see :doc:`troubleshooting`.
