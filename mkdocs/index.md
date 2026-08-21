# sysinfo

Cross-platform Python system inventory for Linux, macOS, and Windows — modular
collectors, powerful redaction, and JSON/YAML/XML/HTML output.

Install the **`lupaxa-sysinfo`** package for the library API and the `sysinfo`
console command:

```bash
pip install lupaxa-sysinfo
sysinfo --help
```

You can also run `python -m lupaxa.sysinfo`.

## What it does

-   Collects basic host metadata by default (pretty-printed JSON)
-   Opt-in collectors for CPU, memory, disks, network, ports, processes,
    firewall, runtimes, GPU, packages, services, hosts/DNS, logs, storage,
    extra hardware, and package-manager layouts
-   Redacts hosts, users, homes, emails, IPs, MACs, secrets, domains, and
    custom regexes before output
-   Profiles for common workflows: `minimal`, `ci`, `support`
-   Exports JSON, YAML, XML, compact HTML, or a human-readable summary (CLI)

## Safe defaults

-   Only basic info is collected unless you enable sections or a profile
-   Environment variables require explicit `--env`; `--all` and profiles do
    not enable them
-   In the CLI, redaction is opt-in: raw output is printed unless you pass
    `--redact-all` (or individual `--redact-*` flags) for shareable dumps
-   In the library, `collect_report()` redacts by default; pass
    `redact=False` or a custom `RedactOptions` to change that
-   Missing OS tools are skipped or normalized with `--strict-missing`

## Next steps

- [Getting started](getting-started.md) — install and first run
- [Usage](usage.md) — profiles, sections, and redaction
- [Reference](reference.md) — command-line options
- [Examples](examples.md) — copy-paste recipes
