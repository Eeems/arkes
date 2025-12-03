=================
Quick Start Guide
=================

Get up and running with Arkēs in 15 minutes. This guide covers the essential steps to install and start using your new atomic Linux distribution.

Step 1: Download and Boot
-------------------------

1. **Download Arkēs ISO** from https://github.com/Eeems/arkes/releases
   - Choose **atomic** for modern desktop (recommended)
   - Choose **gnome** for traditional desktop
   - Choose **base** for server/container use

2. **Create bootable USB**:

   .. code-block:: bash

      # On Linux
      sudo dd if=arkes-atomic.iso of=/dev/sdX bs=4M status=progress sync

3. **Boot from USB** - Restart computer and select USB drive in boot menu

Step 2: Install Arkēs
---------------------

1. **Start installer** in the live environment:

   .. code-block:: bash

      sudo os install

2. **Follow the prompts**:
   - Select disk (automatic partitioning)
   - Create user account
   - Set hostname and timezone
   - Wait for installation (10-20 minutes)

3. **Reboot** into your new Arkēs system

Step 3: First Boot Configuration
--------------------------------

1. **Login** with your user account

2. **Check system status**:

   .. code-block:: bash

      os status

3. **Update system** (recommended):

   .. code-block:: bash

      os upgrade

4. **Configure network** (if needed):

   .. code-block:: bash

      # List Wi-Fi networks
      nmcli dev wifi list
      
      # Connect to network
      nmcli dev wifi connect "YourNetwork" password "YourPassword"

Step 4: Install Your First Application
--------------------------------------

**Option A: Install with Flatpak (Recommended)**

.. code-block:: bash

   # Install Firefox
   flatpak install org.mozilla.firefox
   
   # Install VLC media player
   flatpak install org.videolan.VLC

**Option B: Use Podman Container**

.. code-block:: bash

   # Run Ubuntu container
   podman run -it ubuntu:latest
   
   # Run Firefox from container
   podman run -it --net=host --env=DISPLAY=$DISPLAY firefox

Step 5: Basic System Management
-------------------------------

**Check for updates**:

.. code-block:: bash

   os checkupdates

**Update system**:

.. code-block:: bash

   os upgrade

**View system information**:

.. code-block:: bash

   os status

**Clean old deployments** (occasionally):

.. code-block:: bash

   os prune

Step 6: Understanding Your System
---------------------------------

**Immutable Base System**:
- ``/usr`` is read-only (managed by system)
- ``/var/home`` contains your personal files
- Configuration through ``/etc/system/Systemfile``

**Your Home Directory**:

.. code-block:: bash

   # Navigate to your documents
   cd ~/Documents
   
   # Create a new folder
   mkdir MyProject
   
   # Your files are stored in /var/home/username
   pwd
   # Output: /var/home/username

**Installing System Packages**:

Edit ``/etc/system/Systemfile`` to add packages:

.. code-block:: dockerfile

   RUN /usr/lib/system/install_packages vim git

Then rebuild and upgrade:

.. code-block:: bash

   os build
   os upgrade

Step 7: Common Tasks
--------------------

**Take a screenshot** (atomic variant):

.. code-block:: bash

   # With grim (Wayland screenshot tool)
   grim ~/Pictures/screenshot.png

**Manage applications**:

.. code-block:: bash

   # List installed Flatpaks
   flatpak list
   
   # Update Flatpaks
   flatpak update
   
   # Remove application
   flatpak remove org.mozilla.firefox

**Use terminal multiplexer**:

.. code-block:: bash

   # Start tmux session
   tmux
   
   # Create new window
   Ctrl-b c
   
   # Switch between windows
   Ctrl-b 0, Ctrl-b 1
   
   # Detach session
   Ctrl-b d
   
   # Reattach session
   tmux attach

Step 8: Getting Help
--------------------

**If something goes wrong**:

1. **Rollback system** if update causes issues:

   .. code-block:: bash

      os revert

2. **Check system logs**:

   .. code-block:: bash

      journalctl -xe

3. **Unlock system temporarily** for testing:

   .. code-block:: bash

      sudo os unlock

**For more help**:
- :doc:`user-guide` - Comprehensive usage guide
- :doc:`troubleshooting` - Common issues and solutions
- :doc:`faq` - Frequently asked questions
- GitHub Issues: https://github.com/Eeems/arkes/issues

Step 9: Next Steps
------------------

Congratulations! You now have a working Arkēs system. Here's what to explore next:

**For Desktop Users**:
- Explore your desktop environment (Niri or GNOME)
- Install applications with Flatpak
- Customize your desktop settings
- Try container workflows

**For Developers**:
- Set up development environment
- Explore Podman for containerized development
- Learn about Systemfile customization
- Check out :doc:`creating-variants`

**For System Administrators**:
- Explore system management with ``os`` command
- Set up automated updates
- Learn about atomic deployment
- Read :doc:`architecture`

**Essential Commands to Remember**:

.. code-block:: bash

   os status          # Check system status
   os upgrade         # Update system
   os revert          # Rollback if needed
   flatpak install    # Install applications
   podman run        # Run containers

**Important Concepts**:
- System is **immutable** - changes through Systemfile
- Updates are **atomic** - all or nothing
- **Rollback** is always available
- **Containers** are first-class citizens

Welcome to Arkēs! Enjoy your atomic, immutable Linux experience.
