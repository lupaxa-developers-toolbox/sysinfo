# Getting started

## Requirements

- Python 3.10 or newer
- `psutil` (installed with the package)
- Optional: `distro` (Linux), `tldextract` (PSL-aware domain redaction)

Platform tools such as `nft`, `brew`, or `systemctl` are used only when
present. The tool never installs OS packages.

## Install

```bash
python3 -m pip install lupaxa-sysinfo
sysinfo --help
```

Library import:

```python
from lupaxa.sysinfo import collect_report

report = collect_report(cpu=True, memory=True)
```

Module entry point:

```bash
python -m lupaxa.sysinfo --profile ci --json out.json
```

### From source (development)

Editable install with dev extras:

```bash
make init
make python-install-dev
sysinfo --version
```

The import path is `lupaxa.sysinfo` (`python -m lupaxa.sysinfo` for the CLI).

## First run

Default: basic info to stdout as pretty JSON:

```bash
sysinfo
```

CI-friendly collection (common sections, no spinner, strict missing):

```bash
sysinfo --profile ci --json ci-sysinfo.json
```

YAML or XML output can be printed or saved directly:

```bash
sysinfo --all --output yaml
sysinfo --all --yaml sysinfo.yaml
sysinfo --all --output xml
sysinfo --profile support --xml sysinfo.xml
```

Environment variables are excluded from `--all` and every profile. Enable
them explicitly with `--env` only when they are needed.

## Makefile helpers

```bash
make init                 # clone makefile-skills into .makefiles/
make python-install-dev   # editable install with [dev]
make python-check         # lint + type + test (via makefile-skills)
```
