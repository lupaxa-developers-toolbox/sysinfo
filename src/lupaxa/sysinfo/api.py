"""Public library API for collecting sysinfo reports."""

from __future__ import annotations

from dataclasses import fields, replace
from typing import Any

from .collectors import aggregate
from .options import (
    CollectOptions,
    RedactOptions,
    apply_profile_to_collect,
    collect_options_to_aggregate_opts,
)
from .redact import public_suffix_available, redact_data


def _default_redact_options() -> RedactOptions:
    return RedactOptions(enabled=True, psl_aware=public_suffix_available())


def _merge_collect_options(opts: CollectOptions, kwargs: dict[str, Any]) -> CollectOptions:
    field_names = {f.name for f in fields(CollectOptions)}
    unknown = sorted(set(kwargs) - field_names)
    if unknown:
        names = ", ".join(repr(name) for name in unknown)
        raise TypeError(f"collect_report() got an unexpected keyword argument: {names}")
    if kwargs:
        return replace(opts, **kwargs)
    return opts


def collect_report(
    *,
    collect: CollectOptions | None = None,
    redact: RedactOptions | bool | None = None,
    **kwargs: object,
) -> dict[str, Any]:
    """Collect a system report, redacted by default.

    Extra keyword arguments override individual :class:`CollectOptions` fields;
    names that are not fields raise :class:`TypeError`. ``redact`` defaults to
    full redaction, Public Suffix List aware when ``tldextract`` is installed.
    """
    opts = _merge_collect_options(collect or CollectOptions(), kwargs)
    opts = apply_profile_to_collect(opts)
    data = aggregate(collect_options_to_aggregate_opts(opts))

    if redact is None:
        redact_opts = _default_redact_options()
    elif isinstance(redact, bool):
        redact_opts = _default_redact_options() if redact else RedactOptions(enabled=False)
    else:
        redact_opts = redact

    if not redact_opts.enabled:
        return data
    return redact_data(
        data,
        enable=redact_opts.as_enable_map(),
        extra=redact_opts.extra,
        custom_files=redact_opts.custom_files,
        custom_inline=redact_opts.custom_inline,
        psl_aware=redact_opts.psl_aware,
    )
