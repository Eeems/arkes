# Arkēs

Atomic Arch Linux distribution with immutable filesystem and container-based builds.

For more information see https://arkes.eeems.codes

## Development

### Core Commands
- `./make.py check` - Lint, format, and type check
- `./make.py build <variant>` - Build container image
- `./make.py iso <variant>` - Build live CD
- `./make.py scan <variant>` - Run a security scan on a variant image
- `./make.py workflow` - Regenerate workflows
- `./make.py config --pretty` - Output the current configuration
- `./make.py add-command <name>` - Add a new make.py command

### Project Structure
- `variants/` - Container variants.
- `templates/` - Templates used for commonly created sub-variants.
- `overlay/` - Filesystem modifications.
- `make/` - Build commands.

### Adding New Variants

Create `variants/{name}.Containerfile` with the following structure:

```dockerfile
# syntax=docker/dockerfile:1.4
# x-depends=base
# x-templates=nvidia,slim
ARG HASH

FROM arkes:base

ARG \
  VARIANT="My Variant" \
  VARIANT_ID="myvariant"

RUN /usr/lib/system/package_layer \
  package1 \
  package2 \
  --aur \
  aur_package

COPY overlay/myvariant /

ARG VERSION_ID HASH

LABEL \
  os-release.VARIANT="${VARIANT}" \
  os-release.VARIANT_ID="${VARIANT_ID}" \
  os-release.VERSION_ID="${VERSION_ID}" \
  org.opencontainers.image.ref.name="${VARIANT_ID}" \
  hash="${HASH}"

RUN /usr/lib/system/set_variant
```

- Required elements:

   - `# x-depends=parent` metadata header
   - `ARG HASH` at top, `ARG VERSION_ID HASH` before labels
   - `VARIANT` (display name) and `VARIANT_ID` (identifier) arguments
   - All five LABEL entries for os-release and Open Containers spec compliance
   - Final `RUN /usr/lib/system/set_variant` call

- Use `/usr/lib/system/package_layer` for package installation with `--aur` flag for AUR packages.
- The `COPY overlay/myvariant /` step requires creating the `overlay/myvariant` folder and is only necessary if you have files to overlay.
- The `# x-templates=nvidia,slim` metadata header will automatically generate `myvariant-nvidia` and `myvariant-slim` subvariants.
