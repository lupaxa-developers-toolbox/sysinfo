# Examples

## Basics

```bash
sysinfo
sysinfo --output both
```

## Selective collection

```bash
sysinfo --cpu --memory
sysinfo --all --no-firewall --no-gpu
sysinfo --network --listening-ports --processes
sysinfo --services --hosts-dns --logs --storage
sysinfo --hardware-extra --pkg-layout
```

## Support dump (shareable)

```bash
sysinfo --profile support --redact-all \
  --json sysreport.json --html sysreport.html
```

## CI artifact

```bash
sysinfo --profile ci --output json --json ci-sysinfo.json
```

## YAML report

```bash
sysinfo --all --output yaml
sysinfo --profile ci --yaml ci-sysinfo.yaml
```

## XML report

```bash
sysinfo --all --output xml
sysinfo --profile support --xml sysreport.xml
```

## Environment variables

Environment variables are excluded from `--all` and every profile. Include
them explicitly and consider redaction before sharing the report:

```bash
sysinfo --profile support --env --redact-all --yaml support.yaml
```

## Redaction

```bash
sysinfo --all --redact-fqdns --redact-hosts --redact-emails --redact-ipv4s

sysinfo --redact-domain-trees \
  --redact-domain-tree foo.bar.example.co.uk

sysinfo --redact-custom \
  --redact-rx "[A-Za-z0-9]{32}" \
  --redact-file patterns.txt
```
