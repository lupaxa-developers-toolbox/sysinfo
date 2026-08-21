<!-- markdownlint-disable -->
<p align="center">
  <a href="https://github.com/lupaxa-developers-toolbox">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/developers-toolbox/readme-logo.png" alt="Project Logo" width="256"/><br/>
  </a>
</p>
<h3 align="center">
  The Lupaxa Developers Toolbox<br />
  Part of The Lupaxa Project
</h3>

<br />

# lupaxa-sysinfo

Cross-platform system inventory **library and CLI**: modular collectors, granular
redaction, and JSON / YAML / XML / HTML reports.

Built for automation and support workflows used by The Lupaxa Project.

## Features

- Lightweight defaults: basic host info as pretty-printed JSON
- Opt-in collectors: CPU, memory, disks, network, listening ports, processes,
  firewall, runtimes, GPU, packages
- Granular redaction for hosts, users, IPs, secrets, domains, and custom regexes
- Profiles for common workflows: `minimal`, `ci`, `support`
- Output formats (CLI): JSON, YAML, XML, human summary, and compact HTML
- Library API returns plain dictionaries with `schema_version` and `tool_version`
- Fully typed, linted, formatted, and tested
- MkDocs documentation included

## Installation

### From PyPI

```bash
pip install lupaxa-sysinfo
```

### From source (development mode)

```bash
pip install -e ".[dev]"
```

## Library quick start

```python
from lupaxa.sysinfo import collect_report

report = collect_report(cpu=True, memory=True)
```

For `CollectOptions`, `RedactOptions`, and profiles, see the
[documentation](https://sysinfo.thelupaxaproject.org/).

## CLI quick start

```bash
sysinfo --help
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

## Requirements

- Python 3.10+
- Runtime dependencies: `psutil`, `PyYAML`, `tldextract`
  (plus `distro` on Linux)

## Documentation

Online documentation:

[Documentation](https://sysinfo.thelupaxaproject.org/)

Source repository:

[GitHub](https://github.com/lupaxa-developers-toolbox/sysinfo)

### Serve docs locally

From a clone of the repository:

```bash
make mkdocs-serve
```

Then open the local URL printed by MkDocs in your browser.

## Development

Clone the repository and install with Make:

```bash
make init                # first-time makefile-skills checkout
make python-install-dev  # editable install with [dev]
make python-check        # lint, type-check, and test
```

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer-for-child-orgs.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
