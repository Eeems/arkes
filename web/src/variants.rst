=================
Variants Overview
=================

Arkēs provides multiple variants to use as a base for your system. These can include a different desktop environment, specific hardware support, or even just a small reduction in image size.

Variant Hierarchy
-----------------

All variants are extensions of the base variant:

.. code-block:: text

    base -> base-slim
          \-> atomic -> atomic-nvidia
                      \-> eeems -> eeems-nvidia
                                  \-> eeems-system76
          \-> gnome
          \-> kde

Available Variants
------------------

base
~~~~~

This variant contains the essential system tools. It is the foundation for all other variants.

---

base-slim
~~~~~~~~~

A slightly smaller version of the base image.

---

atomic
~~~~~~~

This variant provides an opinionated modern Wayland-based desktop environment featuring the Niri tiling window manager. It provides a clean, efficient desktop experience.

---

atomic-nvidia
~~~~~~~~~~~~~

Based on the atomic variant. It adds the `NVIDIA <https://wiki.archlinux.org/title/NVIDIA>`_ open drivers, `CUDA <https://wiki.archlinux.org/title/General-purpose_computing_on_graphics_processing_units#CUDA>`_ support, `Optimus <https://wiki.archlinux.org/title/NVIDIA_Optimus>`_ support, and gaming optimizations.

---

gnome
~~~~~

A simple `GNOME <https://www.gnome.org/>`_ variant.

---

kde
~~~~

A simple `KDE Plasma <https://kde.org/>`_ variant.

---

eeems
~~~~~

Based on atomic, this includes `Eeems' personal pacman repositories <https://repo.eeems.codes/>`_ and various development tools and tweaks that are used for his systems.

eeems-nvidia
~~~~~~~~~~~~

Based on the eeems variant. It adds the `NVIDIA <https://wiki.archlinux.org/title/NVIDIA>`_ open drivers, `CUDA <https://wiki.archlinux.org/title/General-purpose_computing_on_graphics_processing_units#CUDA>`_ support, `Optimus <https://wiki.archlinux.org/title/NVIDIA_Optimus>`_ support, and gaming optimizations.

---

eeems-system76
~~~~~~~~~~~~~~~

Based on the eeems variant. It adds `System76 <https://system76.com/>`_ drivers and tools.
