# Reference

## General

| Flag                                       | Description                                   |
| ------------------------------------------ | --------------------------------------------- |
| `--version`                                | Print version and exit                        |
| `--profile {minimal,ci,support}`           | Apply a preset                                |
| `--output FORMAT`                          | Stdout format (default `json`)                |
| `--json PATH`                              | Save JSON to PATH                             |
| `--yaml PATH`                              | Save YAML to PATH                             |
| `--xml PATH`                               | Save XML to PATH                              |
| `--html PATH`                              | Save HTML report to PATH                      |
| `--no-spinner`                             | Disable spinner                               |
| `--strict-missing`                         | Normalize missing tools to an error structure |

Output formats are `json`, `yaml`, `xml`, `summary`, and `both`.

## Sections

| Flag                                       | Description                                   |
| ------------------------------------------ | --------------------------------------------- |
| `--all`                                    | Enable every section except environment       |
| `--cpu` / `--no-cpu`                       | CPU counts, frequency, usage                  |
| `--memory` / `--no-memory`                 | Virtual memory and swap                       |
| `--disks` / `--no-disks`                   | Partitions, usage, I/O counters               |
| `--network` / `--no-network`               | Interfaces, routes, ARP                       |
| `--listening-ports` / `--no-…`             | TCP/UDP listeners with process IDs            |
| `--processes` / `--no-processes`           | Top processes by memory                       |
| `--firewall` / `--no-firewall`             | Firewall summary (nft/iptables/pf/netsh)      |
| `--firewall-prefer`                        | `auto`, `nft`, or `iptables`                  |
| `--runtimes` / `--no-runtimes`             | Java, .NET, Python, Ruby, Node                |
| `--gpu` / `--no-gpu`                       | GPU and driver information                    |
| `--packages` / `--no-packages`             | System, per-user packages, and RubyGems       |
| `--packages-mode`                          | `fast` (default) or `full`                    |
| `--brew-taps CSV`                          | Limit Homebrew formulas to listed taps        |
| `--services` / `--no-services`             | Services and startup configuration            |
| `--hosts-dns` / `--no-hosts-dns`           | Hosts-file and DNS configuration              |
| `--logs` / `--no-logs`                     | System log overview                           |
| `--storage` / `--no-storage`               | Storage devices and mounts                    |
| `--hardware-extra` / `--no-hardware-extra` | Additional platform-specific hardware probes  |
| `--pkg-layout` / `--no-pkg-layout`         | Package-manager installation paths            |
| `--env` / `--no-env`                       | Environment variables; excluded from `--all`  |

The `support` profile enables `--all`, uses full package enumeration, and
still excludes environment variables. Pass `--env` explicitly to include
them.

## Redaction

| Flag                         | Description                                      |
| ---------------------------- | ------------------------------------------------ |
| `--redact-all`               | Enable all redaction categories                  |
| `--redact-<category>`        | Enable one category                              |
| `--no-redact-<category>`     | Disable one category                             |
| `--redact-fqdn` …            | Explicit tokens (repeatable per type)            |
| `--redact-rx REGEX`          | Custom regex (repeatable)                        |
| `--redact-file PATH`         | File of regexes (`#` comments allowed)           |
| `--public-suffix-aware`      | Force PSL-aware domain logic on                  |
| `--no-public-suffix-aware`   | Force PSL-aware domain logic off                 |

Categories include: `fqdns`, `hosts`, `users`, `homes`, `winhomes`, `emails`,
`ipv4s`, `ipv6s`, `macs`, `secrets`, `custom`, `domains`, `domain-trees`,
`subdomains`.
