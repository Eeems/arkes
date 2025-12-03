===================
System Architecture
===================

Technical deep dive into Arkēs architecture, including atomic updates, container integration, and immutable filesystem design.

Core Architecture
-----------------

Overview
~~~~~~~~

Arkēs is built on several key technologies that work together to provide an immutable, atomic Linux distribution:

**Core Components**:
- **OSTree**: Atomic updates and rollback system
- **Podman**: Container runtime and management
- **Immutable Filesystem**: Read-only base system
- **Container-based Builds**: Variant construction
- **Systemd**: Service management and initialization

**Design Principles**:
- **Immutability**: Base system cannot be modified directly
- **Atomicity**: Updates either complete fully or not at all
- **Rollback**: Always able to revert to previous state
- **Container-First**: Applications run in containers when possible
- **Declarative**: System configuration through Systemfile

OSTree Integration
-------------------

Atomic Updates
~~~~~~~~~~~~~~

OSTree provides the foundation for Arkēs' atomic update system:

**Update Process**:
1. **Download** new packages and updates
2. **Build** new system tree in parallel
3. **Verify** integrity of new system
4. **Switch** bootloader to new deployment
5. **Activate** new system on next reboot

**Deployment Structure**:

.. code-block:: text

   /ostree/deploy/
   ├── arkes/
   │   ├── deploy-0/          # Current deployment
   │   ├── deploy-1/          # Previous deployment
   │   └── deploy-2/          # Older deployment
   └── var/

**Benefits**:
- **Zero-downtime updates**: Updates happen in background
- **Automatic rollback**: Failed updates don't break system
- **Multiple versions**: Keep several system versions
- **Space efficient**: Shared storage between deployments

Rollback System
~~~~~~~~~~~~~~~

Rollback is always available through OSTree:

**Rollback Process**:
1. **Select** previous deployment
2. **Update** bootloader configuration
3. **Reboot** into selected deployment
4. **Verify** system functionality

**Rollback Commands**:

.. code-block:: bash

   # View available deployments
   os status
   
   # Revert to previous deployment
   os revert

**Rollback Scenarios**:
- **Failed updates**: Automatic or manual rollback
- **Compatibility issues**: Revert to working version
- **User preference**: Return to previous configuration
- **Testing**: Switch between versions for testing

Filesystem Layout
-----------------

Immutable Structure
~~~~~~~~~~~~~~~~~~~

Arkēs uses a hybrid filesystem approach with immutable and writable areas:

**Immutable Directories** (managed by OSTree):
- ``/usr``: System programs and libraries
- ``/bin``: Essential system binaries
- ``/lib``: System libraries
- ``/etc``: System configuration (managed through overlays)
- ``/boot``: Boot loader and kernel
- ``/ostree``: OSTree metadata and deployments

**Writable Directories** (persistent across updates):
- ``/var/home``: User home directories
- ``/var/log``: System logs
- ``/var/tmp``: Temporary files
- ``/var/cache``: Application cache
- ``/var/opt``: Optional software
- ``/var/lib``: Application data

**Directory Mappings**:

.. code-block:: text

   Traditional Path → Arkēs Path
   /home/username → /var/home/username
   /usr/local → /var/opt
   /tmp → /var/tmp

**Benefits**:
- **System integrity**: Core system files protected
- **Easy updates**: Replace entire system tree
- **User data safety**: Personal data separate from system
- **Consistency**: All systems start from identical base

Overlay System
~~~~~~~~~~~~~~

System configuration is managed through overlays:

**Overlay Structure**:

.. code-block:: text

   overlay/variant/
   ├── etc/
   │   ├── system/           # System configuration
   │   ├── systemd/          # Systemd service files
   │   ├── pacman.d/         # Package manager config
   │   └── [config dirs]    # Other system configs
   └── usr/
       ├── bin/               # Custom binaries
       ├── lib/               # Custom libraries
       └── share/            # Shared data

**Overlay Processing**:
1. **Base system** provides default configuration
2. **Overlay files** override base configuration
3. **Systemfile** defines additional packages and settings
4. **Build process** merges all layers into final system

**Configuration Priority**:
1. **Overlay files** (highest priority)
2. **Systemfile** settings
3. **Base system defaults** (lowest priority)

Container Architecture
----------------------

Podman Integration
~~~~~~~~~~~~~~~~~~

Podman is the primary container runtime in Arkēs:

**Integration Features**:
- **Rootless containers** by default
- **Systemd integration** for container services
- **User namespace isolation**
- **Network integration** with host networking
- **Storage integration** with host filesystem

**Container Workflow**:

.. code-block:: bash

   # Run container with home directory access
   podman run -it -v /var/home/user:/data ubuntu:latest
   
   # Run GUI application
   podman run -it --net=host --env=DISPLAY=$DISPLAY firefox
   
   # Run system service
   podman run -d --name web-server nginx:alpine

**Container Benefits**:
- **Isolation**: Applications isolated from system
- **Security**: Compromised container doesn't affect system
- **Portability**: Containers work across systems
- **Versioning**: Easy to manage application versions
- **Resource management**: Control resource usage

Container Storage
~~~~~~~~~~~~~~~~~

Container storage is integrated with Arkēs filesystem:

**Storage Locations**:
- **Images**: ``/var/lib/containers/storage/``
- **Volumes**: ``/var/home/user/.local/share/containers/volumes/``
- **Networks**: ``/var/home/user/.local/share/containers/networks/``

**Storage Optimization**:
- **Deduplication**: Shared layers between containers
- **Compression**: Reduced storage usage
- **Cleanup**: Automatic cleanup of unused images
- **Quotas**: User-level storage limits

Build System Architecture
-------------------------

Variant Construction
~~~~~~~~~~~~~~~~~~~~

Variants are built using container technology:

**Build Process**:
1. **Base variant** provides foundation
2. **Containerfile** defines packages and configuration
3. **Templates** add specific functionality (NVIDIA, System76)
4. **Overlay** provides configuration files
5. **Build system** creates final container image

**Containerfile Processing**:

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
       package-2

**Build Stages**:
1. **Dependency resolution**: Handle variant dependencies
2. **Template application**: Apply template modifications
3. **Package installation**: Install specified packages
4. **Configuration**: Apply overlay configurations
5. **Image creation**: Create final container image

Template System
~~~~~~~~~~~~~~~

Templates provide modular functionality:

**Available Templates**:
- **nvidia**: NVIDIA driver and CUDA support
- **system76**: System76 hardware integration
- **slim**: Minimal footprint for containers

**Template Application**:
1. **Base variant** provides foundation
2. **Template** adds specific packages and configuration
3. **Combination** creates new variant (e.g., atomic-nvidia)
4. **Build system** processes all templates together

**Template Benefits**:
- **Modularity**: Reusable functionality
- **Combinability**: Multiple templates can be combined
- **Maintainability**: Changes in one place affect all variants
- **Testing**: Templates can be tested independently

System Integration
------------------

Systemd Integration
~~~~~~~~~~~~~~~~~~~

Systemd manages system services and initialization:

**Service Management**:
- **System services**: Core system functionality
- **User services**: Per-user background processes
- **Container services**: Services running in containers
- **Socket activation**: On-demand service startup

**Integration Features**:
- **Boot process**: Systemd-managed boot sequence
- **Service dependencies**: Proper service ordering
- **Resource management**: Control service resource usage
- **Logging**: Centralized logging with journald

**Service Examples**:

.. code-block:: systemd

   [Unit]
   Description=Arkēs Update Service
   After=network.target

   [Service]
   Type=oneshot
   ExecStart=/usr/lib/system/update-system
   RemainAfterExit=yes

   [Install]
   WantedBy=multi-user.target

Network Integration
~~~~~~~~~~~~~~~~~~~

NetworkManager provides network management:

**Network Features**:
- **Automatic configuration**: DHCP, auto-detection
- **Multiple interfaces**: Wired, wireless, mobile
- **Connection management**: Save and restore connections
- **VPN integration**: Support for various VPN types

**Container Networking**:
- **Host networking**: Containers access host network
- **Bridge networking**: Isolated container networks
- **Port mapping**: Expose container ports to host
- **DNS integration**: Container DNS resolution

Security Architecture
---------------------

Immutable Security
~~~~~~~~~~~~~~~~~~

Immutability provides inherent security benefits:

**Security Benefits**:
- **System integrity**: Core system files cannot be modified
- **Malware resistance**: Malware cannot modify base system
- **Configuration management**: Changes are declarative and tracked
- **Update security**: Updates are verified before activation

**Security Layers**:
1. **Immutable base**: Protected core system
2. **Container isolation**: Application isolation
3. **User permissions**: Standard Linux permissions
4. **Network security**: Firewall and network isolation
5. **Update verification**: Cryptographic verification of updates

Container Security
~~~~~~~~~~~~~~~~~~

Containers provide additional security:

**Isolation Features**:
- **Process isolation**: Separate process namespaces
- **Filesystem isolation**: Separate filesystem views
- **Network isolation**: Separate network stacks
- **User isolation**: Non-root container users

**Security Practices**:
- **Rootless containers**: Run without root privileges
- **Read-only filesystems**: Containers use read-only base
- **Resource limits**: Control container resource usage
- **Seccomp filters**: Restrict system calls

Update Security
~~~~~~~~~~~~~~~

Updates include security verification:

**Verification Process**:
1. **Cryptographic signatures**: Verify package authenticity
2. **Checksum verification**: Verify package integrity
3. **Dependency checking**: Validate dependency graph
4. **Test deployment**: Verify system boots and runs
5. **Rollback capability**: Keep previous working system

Performance Considerations
--------------------------

Storage Efficiency
~~~~~~~~~~~~~~~~~~

Arkēs optimizes storage usage:

**Efficiency Features**:
- **Deduplication**: Shared files between deployments
- **Compression**: Compressed filesystem storage
- **Layer optimization**: Optimized container layers
- **Garbage collection**: Automatic cleanup of unused data

**Storage Management**:

.. code-block:: bash

   # Check disk usage
   os du
   
   # Clean old deployments
   os prune
   
   # Clean container storage
   podman system prune

Boot Performance
~~~~~~~~~~~~~~~~

Boot performance is optimized for fast startup:

**Optimizations**:
- **Parallel startup**: Systemd parallel service startup
- **Lazy loading**: Load components on demand
- **Cached initialization**: Cache expensive operations
- **Minimal services**: Only run necessary services

Runtime Performance
~~~~~~~~~~~~~~~~~~~

Runtime performance considerations:

**Performance Features**:
- **Container overhead**: Minimal container performance impact
- **Resource management**: Efficient resource allocation
- **Caching**: Aggressive caching of frequently used data
- **Optimization**: System-specific optimizations

Monitoring and Observability
----------------------------

System Monitoring
~~~~~~~~~~~~~~~~~

Arkēs provides comprehensive monitoring:

**Monitoring Tools**:
- **System status**: ``os status`` command
- **Resource usage**: Standard Linux tools (htop, etc.)
- **Container monitoring**: Podman statistics
- **Log aggregation**: Systemd journal integration

**Monitoring Commands**:

.. code-block:: bash

   # System status
   os status
   
   # Resource usage
   htop
   
   # Container status
   podman ps
   
   # System logs
   journalctl -xe

Performance Metrics
~~~~~~~~~~~~~~~~~~~

Performance can be monitored through:

**Available Metrics**:
- **Boot time**: Time from boot to usable system
- **Update time**: Time to complete system updates
- **Container performance**: Container resource usage
- **Storage usage**: Disk space consumption and efficiency

**Monitoring Integration**:
- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboards
- **Alerting**: Automated alerting for issues

Future Architecture
-------------------

Scalability
~~~~~~~~~~~

Arkēs architecture supports future growth:

**Scalability Features**:
- **Modular design**: Easy to add new components
- **Plugin architecture**: Support for extensions
- **API integration**: External system integration
- **Multi-architecture**: Support for different CPU architectures

**Planned Enhancements**:
- **Cross-architecture**: ARM64, RISC-V support
- **Cloud integration**: Cloud-native deployment options
- **Advanced monitoring**: Enhanced observability
- **Performance optimization**: Further performance improvements

This architecture provides a solid foundation for an immutable, atomic Linux distribution that prioritizes security, reliability, and maintainability while supporting modern container-based workflows.

For more information about contributing to Arkēs, see :doc:`development`.
