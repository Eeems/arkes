=================
Variants Overview
=================

Arkēs provides multiple variants to suit different use cases. Each variant is built on top of base components and includes specific packages and configurations.

Variant Hierarchy
-----------------

All variants follow a dependency chain:

.. code-block:: text

    base -> base-slim
          \-> atomic -> atomic-nvidia
                      \-> eeems -> eeems-nvidia
                                 \-> eeems-system76
          \-> gnome

Available Variants
------------------

base
~~~~~

Essential server and container variant with core system tools. Foundation for all other variants.

---

base-slim
~~~~~~~~~

A slightly smaller version of the base image.

---

atomic
~~~~~~~

Modern Wayland-based desktop environment featuring Niri tiling window manager. Provides a clean, efficient desktop experience optimized for productivity and development.

---

atomic-nvidia
~~~~~~~~~~~~~

Based on atomic, adds NVIDIA driver support. Includes all atomic features plus NVIDIA proprietary drivers, CUDA support, Optimus support, and gaming optimizations.

---

gnome
~~~~~

Full GNOME desktop environment providing a familiar, user-friendly experience with extensive customization options and enterprise-ready features.

---

eeems
~~~~~

Based on atomic, this includes Eeems' personal pacman repositories and various development tools and tweaks that are used for his systems.

eeems-nvidia
~~~~~~~~~~~~

Based on eeems, adds NVIDIA driver support. Includes all eeems features plus NVIDIA proprietary drivers, CUDA support, Optimus support, and gaming optimizations.

---

eeems-system76
~~~~~~~~~~~~~~~

Based on eeems, adds System76 hardware integration. Includes all eeems features plus System76 driver support, hardware-specific optimizations, firmware management, and System76 tools integration.
