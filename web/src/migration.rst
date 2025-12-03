===============
Migration Guide
===============

Complete guide to migrating from other operating systems to Arkēs. This guide covers data migration, configuration adaptation, and workflow changes.

Migration Overview
------------------

What to Expect
~~~~~~~~~~~~~~

Migrating to Arkēs involves adapting to an **immutable, atomic** Linux distribution. Key differences from traditional systems:

**Immutable System**:
- Base system files are read-only
- Changes through Systemfile, not direct modification
- Atomic updates with manual rollback capability
- Container-based system building

**New Workflows**:
- **System customization** through Systemfile editing
- **Application installation** via Flatpak/Podman
- **Update management** with ``os`` commands
- **Data storage** in ``/var/home`` instead of ``/home``

**Benefits**:
- **Reliability** - System can't be accidentally broken
- **Security** - Core system is protected
- **Recovery** - Easy rollback from any issue
- **Consistency** - Predictable system behavior

Pre-Migration Checklist
-----------------------

System Requirements
~~~~~~~~~~~~~~~~~~~

See :doc:`installation` for system requirements and hardware compatibility.

Data Backup Strategy
~~~~~~~~~~~~~~~~~~~~

Before migrating, backup all important data:

**Essential Data to Backup**:
- **Documents**: ``~/Documents/``
- **Media**: ``~/Pictures/``, ``~/Music/``, ``~/Videos/``
- **Configuration**: ``~/.*`` and ``~/.config/``
- **Projects**: ``~/Projects/``, ``~/code/``
- **Application data**: Game saves, browser profiles, etc.

**Backup Methods**:

.. code-block:: bash

   # External drive backup
   rsync -av --progress ~/ /backup/location/
   
   # Cloud backup
   rclone sync ~/Documents/ remote:backup/Documents/
   
   # System image backup
   dd if=/dev/sdX of=backup.img bs=4M

**Verification**:
- **Check backup integrity**
- **Test restore process**
- **Verify all important files included**
- **Store backup in multiple locations**

Application Migration
~~~~~~~~~~~~~~~~~~~~~

For application alternatives and installation methods, see Arch Wiki and Flatpak documentation.

**Key differences**:
- Use Flatpak for desktop applications
- Use Systemfile for system packages
- Use Podman for containerized applications

From Traditional Linux Distributions
------------------------------------

Key Differences
~~~~~~~~~~~~~~~

**Package Management**:
- **Traditional**: ``pacman -S package``, ``apt install package``
- **Arkēs**: Edit Systemfile, ``os build && os upgrade``

**System Configuration**:
- **Traditional**: Edit files in ``/etc`` directly
- **Arkēs**: Edit ``/etc/system/Systemfile`` or overlay files

**Updates**:
- **Traditional**: Incremental package updates
- **Arkēs**: Atomic system updates with rollback

**Application Installation**:
- **Traditional**: System package manager
- **Arkēs**: Flatpak, Podman, or Systemfile

Migration Steps
~~~~~~~~~~~~~~~

1. **Install Arkēs** alongside existing system (dual boot)
2. **Boot into Arkēs** and complete initial setup
3. **Migrate user data** from old system
4. **Install applications** using Arkēs methods
5. **Configure desktop** and applications
6. **Test workflow** and adjust as needed

Data Migration
~~~~~~~~~~~~~~

**User Data Migration**:

.. code-block:: bash

   # Mount old Linux partition
   sudo mount /dev/sdXN /mnt/old-system
   
   # Copy user data to Arkēs
   sudo rsync -av /mnt/old-system/home/username/ /var/home/username/
   
   # Set correct ownership
   sudo chown -R username:username /var/home/username/

**Configuration Migration**:

.. code-block:: bash

   # Migrate shell configuration
   cp /mnt/old-system/home/username/.bashrc ~/.bashrc
   
   # Migrate application configs
   cp -r /mnt/old-system/home/username/.config/appname ~/.config/
   
   # Migrate SSH keys
   cp -r /mnt/old-system/home/username/.ssh ~/.ssh/

**Application Data Migration**:

.. code-block:: bash

   # Browser profiles
   cp -r /mnt/old-system/home/username/.mozilla ~/.mozilla/
   
   # Game saves
   cp -r /mnt/old-system/home/username/.local/share/Steam ~/.local/share/Steam
   
   # Email configuration
   cp -r /mnt/old-system/home/username/.thunderbird ~/.thunderbird/

Configuration Adaptation
~~~~~~~~~~~~~~~~~~~~~~~~

**Shell Configuration**:

.. code-block:: bash

   # Update paths for Arkēs
   sed -i 's|/home/username|/var/home/username|g' ~/.bashrc
   
   # Add Arkēs-specific aliases
   echo 'alias os-status="os status"' >> ~/.bashrc
   echo 'alias update="os upgrade"' >> ~/.bashrc

**Application Configuration**:
- **Update absolute paths** in config files
- **Check permissions** on migrated files
- **Test applications** after migration
- **Adjust for Wayland** if migrating from X11

**Desktop Environment**:
- **Atomic variant**: Configure Niri, waybar, fuzzel
- **GNOME variant**: Use GNOME Settings and Tweaks
- **Import themes**, icons, and wallpapers
- **Set up keyboard shortcuts** and gestures

Package Mapping
~~~~~~~~~~~~~~~

**Arch Linux → Arkēs**:

If coming from Arch Linux, map your packages:

.. code-block:: dockerfile

   # Add your常用 packages to Systemfile
   RUN /usr/lib/system/install_packages \
       htop \
       vim \
       git \
       curl \
       wget \
       tree \
       rsync

**Ubuntu/Debian → Arkēs**:

Common package mappings:

+----------------------+----------------------+
| Ubuntu/Debian        | Arch/Arkēs           |
+======================+======================+
| apt                  | pacman               |
| vim                  | vim                  |
| git                  | git                  |
| curl                 | curl                 |
| htop                 | htop                 |
| firefox              | firefox              |
| libreoffice          | libreoffice-fresh    |
+----------------------+----------------------+

**Migration Command**:

.. code-block:: bash

   # List installed packages on Ubuntu
   apt list --installed
   
   # Find Arch equivalents
   # Then add to Systemfile and rebuild
   os build
   os upgrade

From Other Immutable Distributions
----------------------------------

Fedora Silverblue/OpenSUSE MicroOS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Similarities**:
- **Immutable base system**
- **Atomic updates**
- **Container-based system building**
- **RPM-OSTree** vs **OSTree**

**Key Differences**:
- **Package format**: RPM vs Arch packages
- **Update system**: rpm-ostree vs os commands
- **Base distribution**: Fedora/OpenSUSE vs Arch Linux

**Migration Steps**:

1. **Document current setup**:
   - List installed applications: ``rpm-ostree status``
   - Note configuration: ``~/.var/app/`` locations
   - Identify essential Flatpaks

2. **Install Arkēs** (dual boot initially)
3. **Migrate Flatpak applications**:

   .. code-block:: bash

      # Export Flatpak list from old system
      flatpak list --columns=application > flatpaks.txt
      
      # Install on Arkēs
      flatpak install $(cat flatpaks.txt)

4. **Migrate user data**:

   .. code-block:: bash

      # Mount old system
      sudo mount /dev/sdXN /mnt/old-system
      
      # Copy user data
      sudo rsync -av /mnt/old-system/var/home/username/ /var/home/username/

5. **Adapt configurations**:
   - **Toolbx** → **Podman/Distrobox**
   - **rpm-ostree** → **os** commands
   - **Fedora packages** → **Arch/AUR packages**

**Command Mapping**:

.. list-table:: Command Mapping
   :header-rows: 1
   :widths: 30 30

   * - Fedora Silverblue
     - Arkes
   * - rpm-ostree status
     - os status
   * - rpm-ostree upgrade
     - os upgrade
   * - rpm-ostree rollback
     - boot menu + os revert
   * - toolbox
     - distrobox

From macOS
----------

Workflow Adaptation
~~~~~~~~~~~~~~~~~~~

**Key Differences**:
- **Package management**: Homebrew/Brew Casks vs Flatpak/Podman
- **System configuration**: System Preferences vs Systemfile
- **Command line**: BSD commands vs GNU commands
- **Filesystem**: APFS/HFS+ vs ext4/btrfs

**Application Mapping**:

+----------------------+------------------------+
| macOS                | Arkēs Alternative      |
+======================+========================+
| Safari               | Firefox (Flatpak)      |
| Pages                | LibreOffice (Flatpak)  |
| Preview              | Eye of GNOME (Flatpak) |
| Terminal             | Console/Tilix          |
| VS Code              | VS Code (AUR)          |
| Slack                | Slack (Flatpak)        |
| Spotify              | Spotify (AUR/Flatpak)  |
+----------------------+------------------------+

**Data Migration**:

.. code-block:: bash

   # Mount macOS drive (read-only)
   sudo mount -t hfsplus -o ro /dev/sdXN /mnt/macos
   
   # Copy user data
   sudo rsync -av /mnt/macos/Users/username/ /var/home/username/
   
   # Convert macOS paths to Linux paths
   find /var/home/username/ -name "*.DS_Store" -delete
   find /var/home/username/ -name "._*" -delete

**Configuration Migration**:

.. code-block:: bash

   # Migrate shell configuration
   echo 'export EDITOR=vim' >> ~/.bashrc
   
   # Migrate SSH keys
   cp -r /mnt/macos/Users/username/.ssh ~/.ssh/
   
   # Set up Git configuration
   git config --global user.name "Your Name"
   git config --global user.email "your.email@example.com"

**Keyboard Shortcuts**:
- **Cmd+C/V** → **Ctrl+C/V**
- **Cmd+Tab** → **Alt+Tab**
- **Cmd+Space** → **Super+Space** (application launcher)
- **Cmd+S** → **Ctrl+S** (save)

From Windows
------------

Workflow Adaptation
~~~~~~~~~~~~~~~~~~~

**Key Differences**:
- **Package management**: Installers/Store vs Flatpak/Podman
- **System configuration**: Registry vs Systemfile
- **Filesystem**: NTFS vs ext4/btrfs
- **Command line**: CMD/PowerShell vs Bash/Zsh

**Application Mapping**:

+----------------------+------------------------+
| Windows              | Arkēs Alternative      |
+======================+========================+
| Google Chrome        | Firefox (Flatpak)      |
| Microsoft Office     | LibreOffice (Flatpak)  |
| Adobe Photoshop      | GIMP (Flatpak)         |
| Steam                | Steam (native)         |
| VS Code              | VS Code (AUR)          |
| Discord              | Discord (AUR/Flatpak)  |
| Spotify              | Spotify (AUR/Flatpak)  |
+----------------------+------------------------+

**Data Migration**:

.. code-block:: bash

   # Mount Windows drive
   sudo mount -t ntfs-3g /dev/sdXN /mnt/windows
   
   # Copy user data
   sudo rsync -av /mnt/windows/Users/username/ /var/home/username/
   
   # Convert Windows paths
   find /var/home/username/ -name "*.lnk" -delete

**Gaming Migration**:

.. code-block:: bash

   # Install Steam (native)
   os build  # Add steam to Systemfile
   os upgrade
   
   # Migrate Steam data
   cp -r /mnt/windows/Program\ Files\ \(x86\)/Steam/ ~/.local/share/Steam/
   
   # Install Lutris for other games
   flatpak install com.usebottles.lutris

**Configuration Migration**:

.. code-block:: bash

   # Migrate browser data
   cp -r /mnt/windows/Users/username/AppData/Local/Google/Chrome/User\ Data/ ~/.config/google-chrome/
   
   # Set up development environment
   echo 'export PATH="$PATH:/usr/local/bin"' >> ~/.bashrc
   
   # Configure Git
   git config --global user.name "Your Name"
   git config --global user.email "your.email@example.com"

Post-Migration
--------------

Testing and Validation
~~~~~~~~~~~~~~~~~~~~~~

**Essential Tests**:
1. **Boot system** and verify all deployments work
2. **Network connectivity** and internet access
3. **Application functionality** for migrated apps
4. **Data integrity** - Check important files
5. **Performance** - System responsiveness

**Validation Checklist**:
- [ ] All important data migrated successfully
- [ ] Essential applications installed and working
- [ ] Network and internet functional
- [ ] Desktop environment configured
- [ ] Backup system working
- [ ] Update mechanism tested

**Performance Comparison**:
- **Boot time**: Compare with previous system
- **Application startup**: Note any differences
- **Resource usage**: Monitor RAM/CPU usage
- **Storage efficiency**: Check disk usage patterns

Workflow Optimization
~~~~~~~~~~~~~~~~~~~~~

**Learning Arkēs Workflow**:

1. **System Management**:
   - Get comfortable with ``os`` commands
   - Learn Systemfile editing
   - Practice rollback procedures
   - Understand update process

2. **Application Management**:
   - Use Flatpak for desktop applications
   - Learn Podman for container workflows
   - Explore AUR for niche applications
   - Set up application shortcuts

3. **Customization**:
   - Configure desktop environment
   - Set up shell environment
   - Customize application settings
   - Create backup procedures

**Advanced Features**:
- **Container development**: Set up development containers
- **System monitoring**: Use built-in monitoring tools
- **Automation**: Create scripts for common tasks
- **Security**: Learn about Arkēs security features

Troubleshooting Migration Issues
--------------------------------

Common Problems
~~~~~~~~~~~~~~~

**Data Migration Issues**:
- **Permission errors**: Use correct ownership with ``chown``
- **Path issues**: Update paths in configuration files
- **Missing files**: Verify backup completeness
- **Corrupted data**: Check backup integrity

**Application Issues**:
- **Missing dependencies**: Install required packages
- **Configuration errors**: Adapt config files for Linux
- **Performance issues**: Try alternative applications
- **Compatibility**: Use containers for problematic apps

**System Issues**:
- **Boot problems**: Use boot menu to select previous deployment, then ``os revert`` to clean up, or live USB recovery
- **Update failures**: Check network and disk space
- **Hardware issues**: Verify driver compatibility
- **Performance**: Optimize system settings

**Recovery Procedures**:

.. code-block:: bash

   # Rollback if needed
   os revert
   
   # Access old system for data recovery
   sudo mount /dev/sdXN /mnt/old-system
   
   # Restore from backup if necessary
   rsync -av /backup/location/ /var/home/username/

Getting Help
------------

**Migration Resources**:
- **Documentation**: Other guides in this manual
- **Community**: GitHub Discussions and Issues
- **Application docs**: Specific application migration guides
- **Community forums**: Linux and Arch Linux forums

**Support Channels**:
- **GitHub Issues**: https://github.com/Eeems/arkes/issues
- **Documentation**: Check other guides in this manual
- **Community**: Join discussions and ask questions

**Best Practices**:
- **Test thoroughly** before removing old system
- **Keep backups** during transition period
- **Document changes** for future reference
- **Gradual migration** - migrate applications over time

Remember that Arkēs' immutable nature means most migration issues can be resolved by rebooting and selecting previous deployment from boot menu, then running ``os revert`` to clean up and adjusting your approach.

For more information about daily usage, see :doc:`user-guide`.
