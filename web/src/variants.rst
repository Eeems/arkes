=================
Variants Overview
=================

Arkēs provides multiple variants to suit different use cases. Each variant is built on top of base components and includes specific packages and configurations.

Variant Hierarchy
-----------------

All variants follow a dependency chain:

.. code-block:: text

    rootfs -> base -> atomic -> eeems
                    \- gnome

**Templates** create additional variant combinations:
- **nvidia**: Adds NVIDIA driver support
- **system76**: Adds System76 hardware integration
- **slim**: Reduces footprint for containers/embedded

Available Variants
------------------

rootfs
~~~~~~

**Use Case**: Base system for developers building custom variants

**Description**: 
Minimal Arch Linux foundation containing only essential components. This is the starting point for all other variants and is ideal for developers who want to build completely customized systems.

**Key Features**:
- Minimal Arch Linux base
- OSTree and atomic update system
- Essential system utilities
- Container-ready foundation
- No desktop environment

**Contents**:
- Base Arch Linux packages
- OSTree for atomic updates
- Essential system tools
- Podman container runtime

**Best For**:
- Developers building custom variants
- Container base images
- Minimal server deployments
- Learning system internals

---

base
~~~~

**Use Case**: Headless servers, containers, development environments

**Description**: 
Essential server and container variant with core system tools. Built on rootfs with additional packages for server administration and container management.

**Key Features**:
- Server-ready tools and utilities
- Full container support with Podman
- Network management
- System administration tools
- Hardware support

**Additional Packages** (beyond rootfs):
- **podman** - Container runtime
- **networkmanager** - Network management
- **linux-zen** - Optimized kernel
- **grub** - Boot loader
- **efibootmgr** - UEFI management
- **Essential tools**: nano, micro, tmux, htop, fastfetch
- **Hardware support**: linux-firmware, broadcom-wl-dkms

**Best For**:
- Headless servers
- Container hosts
- Development environments
- Remote administration
- Minimal system deployments

---

atomic
~~~~~~

**Use Case**: Modern desktop usage with Wayland

**Description**: 
Modern Wayland-based desktop environment featuring the Niri tiling window manager. Provides a clean, efficient desktop experience optimized for productivity and development.

**Key Features**:
- **Niri** - Modern tiling window manager
- **greetd-tuigreet** - Console-based display manager
- **waybar** - Customizable status bar
- **fuzzel** - Application launcher
- **Container-friendly** desktop
- Modern Wayland stack

**Desktop Components**:
- **Window Manager**: Niri (tiling)
- **Display Manager**: greetd with tuigreet
- **Status Bar**: waybar
- **Launcher**: fuzzel
- **Terminal**: ghostty
- **File Manager**: nautilus
- **Notification System**: GNOME notification system

**Additional Software**:
- **Development tools**: python-numpy
- **Audio**: pipewire-audio, pipewire-pulse
- **Graphics**: swww (wallpaper), hyprlock, hypridle
- **Gaming**: gamescope
- **System**: fwupd, gnome-software, flatpak-xdg-utils

**Template Variants**:
- **atomic-nvidia**: Atomic desktop with NVIDIA support
- **atomic-system76**: Atomic desktop with System76 support

**Best For**:
- Daily desktop usage
- Development workstations
- Users preferring tiling window managers
- Modern Wayland experience
- Container-based workflows

---

gnome
~~~~~

**Use Case**: Traditional desktop experience

**Description**: 
Full GNOME desktop environment providing a familiar, user-friendly experience with extensive customization options and enterprise-ready features.

**Key Features**:
- **GNOME 40+** with Wayland support
- **Traditional desktop experience**
- **Extensive application ecosystem**
- **Enterprise-friendly features**
- **Accessibility support**

**Desktop Components**:
- **Desktop Environment**: GNOME Shell
- **Display Manager**: GDM
- **Application Suite**: GNOME applications
- **Settings**: GNOME Control Center
- **File Manager**: Nautilus

**Additional Software**:
- **GNOME applications**: Full suite of GNOME apps
- **System tools**: gnome-software, gnome-keyring
- **Accessibility**: Full accessibility stack
- **Enterprise**: PolicyKit, enterprise integration

**Template Variants**:
- **gnome-nvidia**: GNOME desktop with NVIDIA support
- **gnome-system76**: GNOME desktop with System76 support

**Best For**:
- Users preferring traditional desktop
- Enterprise environments
- Accessibility requirements
- GNOME ecosystem users
- New Linux users

---

eeems
~~~~~

**Use Case**: Personalized variant with additional tools and repositories

**Description**: 
Personalized variant built on atomic with additional repositories, development tools, and custom configurations. Includes extra software repositories and specialized tools.

**Key Features**:
- **Additional repositories**: eeems-linux, sublime-text
- **Development tools**: Extended development environment
- **Custom configurations**: Personalized settings
- **Additional software**: Specialized tools
- **Zsh shell**: Pre-configured with additional tools

**Additional Repositories**:
- **eeems-linux**: Custom package repository
- **sublime-text**: Sublime Text editor repository

**Additional Software** (beyond atomic):
- **Development**: sublime-text, zsh, man-pages, man-db
- **Network**: zerotier-one
- **System**: Additional system utilities
- **Documentation**: Extended manual pages

**Template Variants**:
- **atomic-nvidia**: Atomic desktop with NVIDIA support
- **atomic-system76**: Atomic desktop with System76 support
- **gnome-nvidia**: GNOME desktop with NVIDIA support
- **gnome-system76**: GNOME desktop with System76 support
- **eeems-nvidia**: EEEMS desktop with NVIDIA support
- **eeems-system76**: EEEMS desktop with System76 support

**Best For**:
- Power users
- Development with specialized tools
- Users needing additional repositories
- Custom workflows
- Advanced configurations

---

Template System
---------------

Templates create variant combinations by adding specific functionality:

nvidia Template
~~~~~~~~~~~~~~~

**Purpose**: Adds NVIDIA driver support to desktop variants

**Applied to**: atomic, gnome, eeems

**Features**:
- NVIDIA proprietary drivers
- CUDA support
- Optimus support (laptops)
- Gaming optimizations

**Creates**: atomic-nvidia, gnome-nvidia, eeems-nvidia

system76 Template
~~~~~~~~~~~~~~~~~

**Purpose**: Adds System76 hardware integration

**Applied to**: atomic, gnome, eeems

**Features**:
- System76 driver support
- Hardware-specific optimizations
- Firmware management
- System76 tools integration

**Creates**: atomic-system76, gnome-system76, eeems-system76

slim Template
~~~~~~~~~~~~~

**Purpose**: Reduces footprint for containers and embedded systems

**Applied to**: base

**Features**:
- Minimal package set
- Reduced disk usage
- Container optimization
- Faster boot times

**Creates**: base-slim (for containers/embedded)

Choosing the Right Variant
--------------------------

For Desktop Users
~~~~~~~~~~~~~~~~~

**New to Linux**: Choose **gnome** for familiar experience
**Developers**: Choose **atomic** for modern, efficient workflow
**Power Users**: Choose **eeems** for additional tools and repositories

**NVIDIA Graphics**: Add **-nvidia** suffix to your chosen variant
**System76 Hardware**: Add **-system76** suffix to your chosen variant

For Server/Container Use
~~~~~~~~~~~~~~~~~~~~~~~~

**Minimal Servers**: Choose **base** for essential server tools
**Custom Builds**: Choose **rootfs** as foundation for custom variants
**Containers**: Choose **base-slim** for minimal container images

For Development
~~~~~~~~~~~~~~~

**Desktop Development**: **atomic** or **atomic-nvidia**
**Server Development**: **base** with additional tools
**Custom Systems**: **rootfs** as starting point

Variant Selection Examples
--------------------------

**Gaming Desktop with NVIDIA**:
```
atomic-nvidia
```

**Traditional Desktop with System76 Laptop**:
```
gnome-system76
```

**Development Workstation with Extra Tools**:
```
eeems-nvidia
```

**Minimal Server**:
```
base
```

**Custom Container Base**:
```
rootfs
```

Switching Variants
------------------

You can switch between variants by:

1. **Download new variant ISO** from releases
2. **Reinstall** using the new variant
3. **Restore data** from backup (user data in /var/home)

Note: Variant switching requires reinstallation as they have different base configurations and packages.

Custom Variants
---------------

You can create custom variants by:

1. **Starting with base variant** (rootfs, base, atomic)
2. **Creating Containerfile** with additional packages
3. **Building custom variant** using make system
4. **Adding to build configuration**

See :doc:`creating-variants` for detailed instructions.

Variant Comparison Table
------------------------

+-----------+---------+---------+----------+----------+-------------+
| Variant   | Desktop | Server  | Minimal  | NVIDIA   | System76    |
+===========+=========+=========+==========+==========+=============+
| rootfs    | No      | No      | Yes      | No       | No          |
+-----------+---------+---------+----------+----------+-------------+
| base      | No      | Yes     | No       | No       | No          |
+-----------+---------+---------+----------+----------+-------------+
| atomic    | Yes     | No      | No       | Template | Template    |
+-----------+---------+---------+----------+----------+-------------+
| gnome     | Yes     | No      | No       | Template | Template    |
+-----------+---------+---------+----------+----------+-------------+
| eeems     | Yes     | No      | No       | Template | Template    |
+-----------+---------+---------+----------+----------+-------------+

For more detailed information about creating your own variants, see :doc:`creating-variants`.
