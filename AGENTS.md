# Arkēs Development Guide for AI Agents

For project overview and variant details, see `web/src/*.rst` files.

## Specific Rules for Agents
- Always double check your work.
- If you start getting into a loop, stop and ask for instructions.
- Don't try to directly debug `make/*.py` files by importing them, just edit the files and clean them up when done.
- Keep any documentation concise.
- When adding documentation, link to the archwiki where possible.

## Build Commands
- `./make.py check` - Run linting, formatting, and type checking (use `--fix` to auto-fix)
- `./make.py build <variant>` - Build container image(s) for specific variant
- `./make.py workflow` - Regenerate GitHub workflow files after changes
- `./make.py scan <variant>` - Security scan with Trivy
- `./make.py add-command <name>` - Create new commands from template
- `./make.py config -p` - Show dependency chain and template mappings
- `./make.py iso <variant>` - Build ISO locally for testing
- No separate test framework - use `./make.py check` for validation
Website in the `web` folder has its own makefile that will generate the site if you run `make` or `make prod` from inside the `web` folder.

## Development Workflow
- After modifying workflow-related files, always run `./make.py workflow` and commit changes
- For current dependency chain and template mappings, run `./make.py config -p`
- Never use protected variant names "check" or "rootfs" for custom variants
- Never use a `-` in a variant name, as this indicates that a template was applied to a variant to create a new variant.
- Update `.containerignore` when adding build artifacts that shouldn't be in containers

## Template System
Templates create variant combinations using `-` separator:
- `atomic-nvidia` = atomic variant + nvidia template
- `eeems-system76` = eeems variant + system76 template
- Templates are defined in `templates/` directory
- Template metadata in Containerfile headers: `# x-templates=nvidia,system76`

## ISO Builds
- ISO builds use separate workflow: `.github/workflows/iso.yaml`
- Use `./make.py iso <variant>` for local ISO testing
- ISO-specific modifications go in specific overlay locations
- Not all container modifications apply to ISO builds

### ISO-Specific Modification Locations

#### Variant-Agnostic ISO Modifications
- `overlay/base/etc/system/Isofile` - Base ISO Dockerfile for all variants
- `overlay/base/usr/lib/system/setup_live_user` - Live user setup script
- `overlay/base/usr/lib/system/create_live_bootloader` - Bootloader creation
- `overlay/base/usr/lib/system/setup_live_user.d/` - Scripts run during live user setup

#### Variant-Specific ISO Modifications
- `overlay/{variant}/usr/lib/system/setup_live_user.d/` - Variant-specific live user setup
  - Example: `overlay/gnome/usr/lib/system/setup_live_user.d/01-gdm` for GDM autologin
  - Example: `overlay/kde/usr/lib/system/setup_live_user.d/01-sddm` for SDDM autologin

#### Important Notes
- ISO modifications are separate from container overlay modifications
- ISO-specific packages are installed in `overlay/base/etc/system/Isofile`
- Desktop environment autologin is configured via `setup_live_user.d/` scripts

## Code Style Guidelines

### Python (3.13)
- Use Ruff for formatting/linting, basedpyright for type checking.
- Type hints required on all function signatures and variables.
- Import order: standard library → third-party → local imports.
- Use `cast()` for type assertions when needed.
- Every `make/*.py` command must have exactly `register()` and `command()` functions.
- Use `[command] message` format for all command output to stderr.
- basedpyright warnings should also be addressed.

### Go (1.25.4)
- Use gofmt for formatting, go vet for static analysis
- Standard Go module structure in `tools/` directory

### Error Handling
- Use sys.exit(1) for command failures
- Print error messages to stderr
- Return boolean success/failure for internal functions
- Always check `is_root()` before attempting privileged operations

## Containerfile Conventions
- Always include dependency metadata:
  ```dockerfile
  # x-depends=rootfs
  # x-templates=slim
  ```
- Standard build args: `HASH`, `VARIANT`, `VARIANT_ID`, `VERSION_ID`, `TAR_DETERMINISTIC`, `TAR_SORT`
- Use `os-release.` prefix and Open Containers spec for labels

## Security & Best Practices
- Never commit secrets - use GitHub secrets or environment variables
- Never modify `seccomp.json` without security review
- Use provided `progress_bar()` function for long-running operations
- Use built-in caching functions for image operations

## Adding New Commands
- Use `./make.py add-command <name>` to create new commands from template
- Commands are automatically discovered after creation
- New command will be available as `./make.py <name>`
- Edit the generated file to implement your command logic
- Test with `./make.py <name> --help` and validate with `./make.py check`

## Project Structure
- Container variants in `variants/` with templates in `templates/`
- Overlays in `overlay/` for filesystem modifications
- Commands in `make/` directory with automatic discovery
