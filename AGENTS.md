# Arkēs Development Guide for AI Agents

## Build Commands
- `./make.py check` - Run linting, formatting, and type checking (use --fix to auto-fix)
- `./make.py build <variant>` - Build container image(s) for specific variant
- `./make.py workflow` - Regenerate GitHub workflow files after changes
- `./make.py scan <variant>` - Security scan with Trivy
- `./make.py add-command <name>` - Create new commands from template
- No separate test framework - use `./make.py check` for validation

## Development Workflow
- After modifying workflow-related files, always run `./make.py workflow` and commit changes
- Variants follow strict dependency chain: `rootfs` → `base` → other variants
- Never use protected variant names "check" or "rootfs" for custom variants
- Update `.containerignore` when adding build artifacts that shouldn't be in containers

## Code Style Guidelines

### Python (3.13)
- Use Ruff for formatting/linting, basedpyright for type checking
- Type hints required on all function signatures and variables
- Import order: standard library → third-party → local imports
- Use `cast()` for type assertions when needed
- Every `make/*.py` command must have exactly `register()` and `command()` functions
- Use `[command] message` format for all command output to stderr

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