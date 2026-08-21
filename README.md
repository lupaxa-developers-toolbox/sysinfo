<p align="center">
  <a href="https://github.com/lupaxa-developers-toolbox">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/developers-toolbox/readme-logo.png" alt="Developers Toolbox" />
  </a>
</p>

<h1 align="center">sysinfo</h1>

Cross-platform system inventory with modular collectors, redaction, and JSON/YAML/XML/HTML reports.

<p align="center">
  <a href="https://sysinfo.thelupaxaproject.org/">Documentation</a>
  ·
  <a href="https://github.com/lupaxa-developers-toolbox/sysinfo">GitHub</a>
</p>

## Install

```bash
pip install lupaxa-sysinfo
sysinfo --help
```

## Features

- Lightweight defaults: basic host info as pretty-printed JSON
- Opt-in collectors: CPU, memory, disks, network, listening ports, processes, firewall, runtimes, GPU, packages
- Granular redaction for hosts, users, IPs, secrets, domains, and custom regexes
- Profiles for common workflows: `minimal`, `ci`, `support`
- JSON, YAML, XML, human summary, and compact HTML output (CLI)

## Requirements

- Python 3.10+
- Runtime: `psutil` (plus `distro` on Linux; `tldextract` for PSL-aware redaction)

## Library quick start

```python
from lupaxa.sysinfo import collect_report

report = collect_report(cpu=True, memory=True)
```

Reports are plain dictionaries with `schema_version` and `tool_version` keys,
ready for JSON serialisation. See the
[documentation](https://sysinfo.thelupaxaproject.org/) for `CollectOptions`,
`RedactOptions`, and profiles.

## CLI quick start

```bash
sysinfo --version
sysinfo --profile ci --json report.json
sysinfo --all --yaml report.yaml
sysinfo --all --output xml
sysinfo --profile support --xml report.xml
```

You can also run the CLI as a module:

```bash
python -m lupaxa.sysinfo --help
python -m lupaxa.sysinfo --profile ci --json out.json
```

## Development

From a clone of this repository:

```bash
make init                # first-time makefile-skills checkout
make python-install-dev  # editable install with [dev]
make python-check        # lint, type-check, and test
make mkdocs-serve        # after skills are installed
```

Community standards (code of conduct, contributing, security) are in [`docs/`](docs/).

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer-for-child-orgs.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
