<p align="center">
  <a href="https://github.com/lupaxa-developers-toolbox">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/developers-toolbox/readme-logo.png" alt="Developers Toolbox" />
  </a>
</p>

<h1 align="center">Sysinfo</h1>

Cross-platform system inventory for Linux, macOS, and Windows — modular
collectors, granular redaction, and JSON / YAML / XML / HTML reports.

## Install

```bash
pip install lupaxa-sysinfo
sysinfo --help
```

You can also run `python -m lupaxa.sysinfo`.

## Features

-   Lightweight defaults: basic host info as pretty-printed JSON
-   Opt-in collectors: CPU, memory, disks, network, listening ports, processes,
  firewall, runtimes, GPU, packages, services, hosts/DNS, logs, storage,
  extra hardware, and package-manager layouts
-   Granular redaction for hosts, users, homes, emails, IPs, MACs, secrets,
  domains, and custom regexes
-   Profiles for common workflows: `minimal`, `ci`, `support`
-   JSON, YAML, XML, human summary, and compact HTML output (CLI)

## Safe Defaults

-   Only basic info is collected unless you enable sections or a profile
-   Environment variables require explicit `--env`; `--all` and every profile
  leave them off (they often hold credentials)
-   In the CLI, redaction is opt-in: raw output unless you pass `--redact-all`
  or individual `--redact-*` flags
-   In the library, `collect_report()` redacts by default; pass `redact=False`
  or a custom `RedactOptions` to change that
-   Missing OS tools are skipped, or normalized with `--strict-missing`
-   Platform tools (`nft`, `brew`, `systemctl`, …) are used only when present;
  the package never installs OS packages

## Requirements

- Python 3.10+
- Runtime: `psutil`, `PyYAML`, `tldextract` (plus `distro` on Linux)

## Library Quick Start

```python
from lupaxa.sysinfo import collect_report

report = collect_report(cpu=True, memory=True)
```

Reports are plain dictionaries with `schema_version` and `tool_version`,
ready for JSON serialisation. Use `CollectOptions` / `RedactOptions` (or the
`redact=` argument) when you need finer control than keyword flags.

## Redaction

Redaction runs **after collection and before any stdout or file write**. Use
it whenever a report might leave your machine.

**CLI vs library defaults (easy to miss):**

| Surface | Default                         | Shareable dumps                                       |
| ------- | ------------------------------- | ----------------------------------------------------  |
| CLI     | **Off** (raw output)            | Pass `--redact-all` (or selective `--redact-*` flags) |
| Library | **On** via `collect_report()`   | Already redacted; use `redact=False` only if you must |

Categories include FQDNs, hosts, users, homes, Windows homes, emails, IPv4/IPv6,
MACs, secrets, domains, domain trees, subdomains, and custom regexes. Secrets
mode masks dict values whose keys look secret-like (`KEY`, `TOKEN`,
`PASSWORD`, …).

```bash
# Full redaction for a support dump
sysinfo --profile support --redact-all \
  --json sysreport.json --html sysreport.html

# Selective categories, or carve one out after --redact-all
sysinfo --all --redact-emails --redact-hosts --redact-ipv4s
sysinfo --all --redact-all --no-redact-macs

# Explicit tokens and custom patterns
sysinfo --redact-email "admin@example.com"
sysinfo --redact-domain-trees --redact-domain-tree foo.bar.example.co.uk
sysinfo --redact-custom \
  --redact-rx "[A-Za-z0-9]{32}" \
  --redact-file patterns.txt
```

```python
from lupaxa.sysinfo import collect_report, RedactOptions

# Library default: redacted (all categories on)
report = collect_report(cpu=True, memory=True)

# Keep redaction but carve out a category
report = collect_report(cpu=True, redact=RedactOptions(macs=False))

# Raw (local debugging only)
raw = collect_report(cpu=True, redact=False)
```

If you enable `--env`, always pair it with redaction before sharing:

```bash
sysinfo --profile support --env --redact-all --yaml support.yaml
```

## CLI Quick Start

```bash
sysinfo
sysinfo --version
sysinfo --profile ci --json report.json
sysinfo --all --yaml report.yaml
sysinfo --all --output xml
sysinfo --profile support --xml report.xml
```

### Profiles

| Profile   | Behaviour                                                              |
| --------- | ---------------------------------------------------------------------- |
| `minimal` | Basic only; spinner off                                                |
| `ci`      | CPU, memory, disks, network, runtimes, packages (fast); strict missing |
| `support` | All non-environment sections; full package enumeration                 |

### Common Recipes

```bash
sysinfo --profile ci --json ci-sysinfo.json
sysinfo --cpu --memory
sysinfo --all --no-firewall --no-gpu
sysinfo --packages --packages-mode fast
```

Stdout formats are `json` (default), `yaml`, `xml`, `summary`, and `both`.
File writers: `--json PATH`, `--yaml PATH`, `--xml PATH`, `--html PATH`.
Full flag list: `sysinfo --help`.

## Development

From a clone of this repository:

```bash
make init                # first-time makefile-skills checkout
make python-install-dev  # editable install with [dev]
make python-check        # lint, type-check, and test
```

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer-for-child-orgs.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
