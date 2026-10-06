# Installing and Managing Python | uv

## Overview

uv offers built-in Python installation and management capabilities. The system automatically detects existing Python installations, but can also independently install and manage Python versions without requiring prior installation.

## Getting Started

The basic command to install the latest Python version is:

```
$ uv python install
```

**Important note:** "Python does not publish official distributable binaries. As such, uv uses distributions from the Astral `python-build-standalone` project."

Once installed, Python becomes available to uv commands automatically, with the version added to your PATH. By default, only versioned executables (like `python3.13`) are installed; use the experimental `--default` flag to also create `python` and `python3` executables.

## Installing Specific Versions

Install a particular Python version:
```
$ uv python install 3.12
```

Install multiple versions:
```
$ uv python install 3.11 3.12
```

Install alternative implementations like PyPy:
```
$ uv python install pypy@latest
```

## Reinstalling Python

Reinstall all previously installed versions:
```
$ uv python install --reinstall
```

This may resolve bugs even without version changes, as distributions receive ongoing improvements.

## Viewing Installations

List available and installed Python versions:
```
$ uv python list
```

## Automatic Downloads

Python installation happens automatically when needed. For example, running `uv venv` without an existing Python installation will automatically download the latest version first. This behavior can be disabled if you prefer manual control.

## Using Existing Python

uv automatically detects and uses system Python installations without configuration. To force system Python usage, provide the `--no-managed-python` flag.

## Upgrading Versions

Upgrade Python to the latest patch release:
```
$ uv python upgrade 3.12
```

Upgrade all managed versions:
```
$ uv python upgrade
```

**Note:** This feature is currently in preview and subject to change.

Source: https://docs.astral.sh/uv/guides/install-python
