# Usage

## Profiles

Presets flip a sensible set of flags; you can still override with explicit
options.

| Profile   | Behaviour                                                              |
| --------- | ---------------------------------------------------------------------- |
| `minimal` | Basic only; spinner off                                                |
| `ci`      | CPU, memory, disks, network, runtimes, packages (fast); strict missing |
| `support` | All non-environment sections; full package enumeration                 |

```bash
sysinfo --profile support --redact-all --json sysreport.json --html sysreport.html
```

## Sections

By default only basic info is collected. Enable sections individually or with
`--all`. Every section supports a matching `--no-…` negation.

| Section flag        | Collected data                              |
| ------------------- | ------------------------------------------- |
| `--cpu`             | CPU counts, frequency, and usage            |
| `--memory`          | Virtual memory and swap                     |
| `--disks`           | Partitions, usage, and I/O counters         |
| `--network`         | Interfaces, routes, and ARP                 |
| `--listening-ports` | TCP/UDP listeners with process IDs          |
| `--processes`       | Top processes by memory                     |
| `--firewall`        | Firewall summary                            |
| `--runtimes`        | Installed language runtimes                 |
| `--gpu`             | GPU and driver information                  |
| `--packages`        | System and per-user packages                |
| `--services`        | Services and startup configuration          |
| `--hosts-dns`       | Hosts-file and DNS configuration            |
| `--logs`            | System log overview                         |
| `--storage`         | Storage devices and mounts                  |
| `--hardware-extra`  | Additional platform-specific hardware data  |
| `--pkg-layout`      | Package-manager installation paths          |
| `--env`             | Environment variables; always explicit only |

`--all` enables every optional section except `--env`. Environment variables
can contain credentials and other sensitive values, so `--env` must always be
passed explicitly. The `support` profile uses `--all` and therefore does not
enable `--env`.

```bash
sysinfo --cpu --memory
sysinfo --all --no-firewall --no-gpu
sysinfo --profile support --env --redact-all
```

## Output

| Option                                     | Purpose                                  |
| ------------------------------------------ | ---------------------------------------- |
| `--output json\|yaml\|xml\|summary\|both`  | What to print to stdout (default `json`) |
| `--json PATH`                              | Also write JSON to a file                |
| `--yaml PATH`                              | Also write YAML to a file                |
| `--xml PATH`                               | Also write XML to a file                 |
| `--html PATH`                              | Also write a compact HTML report         |
| `--no-spinner`                             | Disable the progress spinner             |

## Redaction

Redaction runs after collection and before any stdout or file write.

```bash
sysinfo --all --redact-all --no-redact-macs
sysinfo --redact-emails --redact-email "admin@example.com"
```

Use `--redact-all` for shareable support dumps. Secrets mode masks dict values
whose keys look secret-like (`KEY`, `TOKEN`, `PASSWORD`, …).

## Packages

```bash
sysinfo --packages --packages-mode fast
sysinfo --packages --packages-mode full
sysinfo --packages --brew-taps "homebrew/core,hashicorp/tap"
```
