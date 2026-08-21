"""System information collectors and report aggregation."""

from __future__ import annotations

import datetime
import os
import platform
import shutil
import socket
import subprocess
import sys
from collections.abc import Callable, Sequence
from types import ModuleType
from typing import Any, TypeVar

from .version import get_version

try:
    import psutil
except Exception as exc:
    raise ImportError("psutil is required. Install with: pip install psutil") from exc

distro: ModuleType | None
try:
    import distro as _distro
except Exception:
    distro = None
else:
    distro = _distro

SCHEMA_VERSION: int = 1

_T = TypeVar("_T")

# -------------------- Utils --------------------


def run_cmd(cmd: str | Sequence[str], timeout: float = 20) -> dict[str, Any]:
    """Run an external command and return its outcome as a mapping.

    The result always contains ``ok``, ``code``, ``stdout``, ``stderr``, and
    ``cmd`` keys; failures to launch are reported rather than raised.
    """
    try:
        # Commands are literals defined in this module, never caller-supplied input.
        completed = subprocess.run(  # noqa: S603
            cmd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=timeout
        )
        return {
            "ok": completed.returncode == 0,
            "code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "cmd": cmd if isinstance(cmd, str) else " ".join(cmd),
        }
    except Exception as e:
        return {"ok": False, "code": None, "stdout": "", "stderr": str(e), "cmd": cmd}


def safe_get(fn: Callable[[], _T], default: _T | None = None) -> _T | None:
    """Call ``fn`` and return ``default`` if it raises."""
    try:
        return fn()
    except Exception:
        return default


def which(name: str) -> bool:
    """Return whether an executable named ``name`` is on ``PATH``."""
    return shutil.which(name) is not None


# Strict-missing normalization helper
STRICT_MISSING: bool = False


def set_strict_missing(enabled: bool) -> None:
    """Normalize results for absent external tools to ``not_found()`` when enabled."""
    global STRICT_MISSING
    STRICT_MISSING = bool(enabled)


def not_found() -> dict[str, Any]:
    """Return the canonical result for an external tool that is unavailable."""
    return {"ok": False, "stderr": "not found"}


# -------------------- Collectors --------------------


def basic_info() -> dict[str, Any]:
    """Collect host identity, platform, and boot-time details."""
    info: dict[str, Any] = {}
    info["timestamp_utc"] = (
        datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    )
    info["hostname"] = socket.gethostname()
    info["fqdn"] = socket.getfqdn()
    info["platform"] = platform.system()
    info["platform_release"] = platform.release()
    info["platform_version"] = platform.version()
    info["machine"] = platform.machine()
    info["processor"] = platform.processor()
    info["python_version"] = platform.python_version()
    info["python_executable"] = sys.executable
    info["boot_time"] = datetime.datetime.fromtimestamp(psutil.boot_time()).isoformat()
    if info["platform"].lower() == "linux" and distro:
        info["distro"] = {
            "id": distro.id(),
            "name": distro.name(pretty=True),
            "version": distro.version(),
            "like": distro.like(),
        }
    else:
        info["distro"] = None
    return info


def cpu_info() -> dict[str, Any]:
    """Collect CPU counts, frequency, and utilisation samples."""
    cpu: dict[str, Any] = {}
    cpu["logical_cpus"] = psutil.cpu_count(logical=True)
    cpu["physical_cores"] = psutil.cpu_count(logical=False)
    cpu["freq"] = safe_get(lambda: psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None)
    cpu["percent_per_cpu"] = safe_get(lambda: psutil.cpu_percent(percpu=True, interval=1))
    cpu["overall_percent"] = safe_get(lambda: psutil.cpu_percent(interval=0.5))
    return cpu


def memory_info() -> dict[str, Any]:
    """Collect virtual and swap memory statistics."""
    v = psutil.virtual_memory()
    s = psutil.swap_memory()
    return {"virtual": v._asdict(), "swap": s._asdict()}


def disks_info() -> dict[str, Any]:
    """Collect mounted partitions, their usage, and per-disk IO counters."""
    info: dict[str, Any] = {"partitions": []}
    for p in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(p.mountpoint)._asdict()
        except Exception:
            usage = None
        info["partitions"].append(
            {
                "device": p.device,
                "mountpoint": p.mountpoint,
                "fstype": p.fstype,
                "opts": p.opts,
                "usage": usage,
            }
        )
    try:
        di = psutil.disk_io_counters(perdisk=True)
        info["disk_io_counters"] = (
            {k: v._asdict() for k, v in di.items()} if di is not None else None
        )
    except Exception:
        info["disk_io_counters"] = None
    return info


def network_info() -> dict[str, Any]:
    """Collect interface addresses, IO counters, routing table, and ARP cache."""
    net: dict[str, Any] = {}
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    net["interfaces"] = {}
    for name, addr_list in addrs.items():
        net["interfaces"][name] = {
            "addrs": [a._asdict() for a in addr_list],
            "stats": stats[name]._asdict() if name in stats else None,
        }
    try:
        io = psutil.net_io_counters(pernic=True)
        net["net_io_counters"] = {k: v._asdict() for k, v in io.items()}
    except Exception:
        net["net_io_counters"] = None

    sysname = platform.system().lower()
    if sysname == "linux":
        net["route"] = run_cmd("ip route show") if which("ip") else run_cmd("route -n")
    elif sysname == "darwin":
        net["route"] = run_cmd("netstat -nr")
    elif sysname == "windows":
        net["route"] = run_cmd("route print")
    else:
        net["route"] = None

    net["arp"] = run_cmd("arp -a")
    return net


def listening_ports() -> list[dict[str, Any]] | dict[str, str]:
    """Collect sockets in the listening state, or an error mapping on failure."""
    out: list[dict[str, Any]] = []
    try:
        conns = psutil.net_connections(kind="inet")
        for c in conns:
            if getattr(psutil, "CONN_LISTEN", "LISTEN") in (c.status,):
                out.append(
                    {
                        "laddr": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else None,
                        "raddr": (
                            f"{getattr(c.raddr, 'ip', None)}:{getattr(c.raddr, 'port', None)}"
                        )
                        if c.raddr
                        else None,
                        "pid": c.pid,
                        "fd": getattr(c, "fd", None),
                        "type": getattr(c, "type", None),
                        "family": str(getattr(c, "family", None)),
                    }
                )
    except Exception as e:
        return {"error": str(e)}
    return out


def processes_info(limit: int = 30) -> list[dict[str, Any]] | dict[str, str]:
    """Collect the ``limit`` heaviest processes by memory, or an error mapping."""
    procs: list[dict[str, Any]] = []
    try:
        for p in psutil.process_iter(
            [
                "pid",
                "name",
                "username",
                "cpu_percent",
                "memory_percent",
                "exe",
                "cmdline",
                "create_time",
            ]
        ):
            procs.append(p.info)
        procs_sorted = sorted(procs, key=lambda x: x.get("memory_percent") or 0, reverse=True)
        return procs_sorted[:limit]
    except Exception as e:
        return {"error": str(e)}


def services_and_startup() -> dict[str, Any] | None:
    """Collect the platform's service or startup-item listing."""
    sysname = platform.system().lower()
    if sysname == "linux":
        if which("systemctl"):
            return run_cmd("systemctl list-units --type=service --no-pager --all")
        return run_cmd("service --status-all || true")
    if sysname == "darwin":
        return run_cmd("launchctl list")
    if sysname == "windows":
        return run_cmd(
            'powershell -Command "Get-Service | '
            'Select-Object Name,Status,StartType | ConvertTo-Json"'
        )
    return None


# -------- Firewall (nft vs iptables) --------


def linux_firewall_preference(dinfo: dict[str, Any] | None) -> str:
    """Return ``"nft"`` or ``"iptables"`` for the given Linux distribution info."""
    if not which("nft"):
        return "iptables"
    if not dinfo:
        return "nft"
    did = (dinfo.get("id") or "").lower()
    dver = (dinfo.get("version") or "").split(".")
    try:
        major = int(dver[0]) if dver and dver[0].isdigit() else 0
    except Exception:
        major = 0
    modern = {
        "ubuntu",
        "debian",
        "fedora",
        "rhel",
        "centos",
        "rocky",
        "almalinux",
        "arch",
        "opensuse",
        "opensuse-leap",
        "opensuse-tumbleweed",
    }
    if did in modern:
        if did == "ubuntu" and major >= 20:
            return "nft"
        if did == "debian" and major >= 10:
            return "nft"
        if did in {"fedora", "arch", "opensuse", "opensuse-leap", "opensuse-tumbleweed"}:
            return "nft"
        if did in {"rhel", "centos", "rocky", "almalinux"} and major >= 8:
            return "nft"
    return "nft"


def firewall_rules(
    firewall_prefer: str = "auto", distro_info: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Collect the active firewall ruleset for the current platform."""
    sysname = platform.system().lower()
    if sysname == "linux":
        pref = (
            linux_firewall_preference(distro_info) if firewall_prefer == "auto" else firewall_prefer
        )
        result: dict[str, Any] = {"preference": pref}
        if pref == "nft":
            result["nft_ruleset"] = run_cmd("nft list ruleset")
            if which("iptables"):
                result["iptables_version"] = run_cmd("iptables -V")
                result["iptables_filter"] = run_cmd("iptables -L -n --line-numbers || true")
        else:
            result["iptables_version"] = (
                run_cmd("iptables -V")
                if which("iptables")
                else (
                    not_found() if STRICT_MISSING else {"ok": False, "stderr": "iptables not found"}
                )
            )
            result["iptables_filter"] = run_cmd("iptables -L -n --line-numbers || true")
            if which("nft"):
                result["nft_ruleset"] = run_cmd("nft list ruleset")
        if which("update-alternatives"):
            result["alternatives_iptables"] = run_cmd(
                "update-alternatives --display iptables || true"
            )
        return result
    if sysname == "darwin":
        return {"pf_rules": run_cmd("pfctl -sr || true")}
    if sysname == "windows":
        return {
            "netsh": run_cmd("netsh advfirewall firewall show rule name=all"),
            "powershell_GetNetFirewallRule": run_cmd(
                'powershell -Command "Get-NetFirewallRule -PolicyStore ActiveStore | '
                "Select-Object Name,DisplayName,Enabled,Direction,Action | "
                'ConvertTo-Json"'
            ),
        }
    return {"ok": False, "stderr": f"unsupported platform: {sysname}"}


# -------- Hosts/DNS, logs, env, storage --------


def hosts_and_dns() -> dict[str, Any]:
    """Collect the hosts file and the platform's DNS resolver configuration."""
    out: dict[str, Any] = {}
    hosts_path = (
        "/etc/hosts"
        if platform.system().lower() != "windows"
        else os.path.join(
            os.environ.get("SYSTEMROOT", "C:\\Windows"), "System32\\drivers\\etc\\hosts"
        )
    )
    try:
        with open(hosts_path, encoding="utf-8", errors="ignore") as f:
            out["hosts"] = f.read()
    except Exception as e:
        out["hosts"] = f"error reading hosts: {e}"
    sysname = platform.system().lower()
    if sysname == "linux":
        try:
            with open("/etc/resolv.conf", encoding="utf-8", errors="ignore") as f:
                out["resolv.conf"] = f.read()
        except Exception as e:
            out["resolv.conf"] = f"error: {e}"
    elif sysname == "darwin":
        out["scutil_dns"] = run_cmd("scutil --dns")
    elif sysname == "windows":
        out["ipconfig_all"] = run_cmd("ipconfig /all")
    return out


def logs_overview(limit_lines: int = 200) -> dict[str, Any]:
    """Collect the most recent ``limit_lines`` of the platform's system logs."""
    out: dict[str, Any] = {}
    sysname = platform.system().lower()
    if sysname == "linux":
        if which("journalctl"):
            out["journalctl_recent"] = run_cmd(f"journalctl -n {limit_lines} --no-pager")
        for f in ("/var/log/syslog", "/var/log/messages", "/var/log/kern.log"):
            if os.path.exists(f):
                out[f] = run_cmd(f"tail -n {limit_lines} {f}")
    elif sysname == "darwin":
        if which("log"):
            out["log_show"] = run_cmd(
                "log show --style syslog --last 1d --info --debug "
                f"--style json | tail -n {limit_lines}"
            )
    elif sysname == "windows":
        out["event_query"] = run_cmd(
            'powershell -Command "Get-EventLog -LogName System -Newest 200 | ConvertTo-Json"'
        )
    return out


def env_and_misc() -> dict[str, Any]:
    """Collect environment variables plus timezone, uptime, and mount details."""
    out: dict[str, Any] = {}
    out["env"] = dict(os.environ)
    out["timezone"] = run_cmd("timedatectl status || date")
    out["uptime"] = (
        run_cmd("uptime")
        if which("uptime")
        else {
            "stdout": str(
                datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())
            )
        }
    )
    out["mounted_filesystems"] = run_cmd("mount") if which("mount") else None
    out["arp"] = run_cmd("arp -a")
    return out


def storage_and_mounts() -> dict[str, Any]:
    """Collect filesystem usage and the current mount table."""
    out: dict[str, Any] = {}
    out["df"] = run_cmd("df -h") if which("df") else None
    sysname = platform.system().lower()
    if sysname in ("darwin", "linux"):
        out["mounts"] = run_cmd("mount")
    else:
        out["mounts"] = None
    return out


def hardware_extra() -> dict[str, Any]:
    """Collect platform-specific hardware probes such as ``lscpu`` or ``wmic``."""
    sysname = platform.system().lower()
    info: dict[str, Any] = {}
    if sysname == "linux":
        info["lscpu"] = (
            run_cmd("lscpu")
            if which("lscpu")
            else (not_found() if STRICT_MISSING else {"ok": False, "stderr": "lscpu not found"})
        )
        info["lspci"] = (
            run_cmd("lspci -nnk || true")
            if which("lspci")
            else (not_found() if STRICT_MISSING else {"ok": False, "stderr": "lspci not found"})
        )
        info["dmidecode"] = (
            run_cmd("dmidecode -t system || true")
            if which("dmidecode")
            else (not_found() if STRICT_MISSING else {"ok": False, "stderr": "dmidecode not found"})
        )
    elif sysname == "darwin":
        info["system_profiler_hardware"] = run_cmd("system_profiler SPHardwareDataType")
        info["system_profiler_displays"] = run_cmd("system_profiler SPDisplaysDataType")
    elif sysname == "windows":
        info["wmic_cpu"] = run_cmd(
            "wmic cpu get name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed /format:list"
        )
        info["wmic_bios"] = run_cmd("wmic bios get manufacturer,serialnumber,version /format:list")
        info["wmic_gpu"] = run_cmd("wmic path win32_VideoController get name /format:list")
    return info


# -------- Packages (system, user, gems) --------


def collect_packages(mode: str = "fast") -> dict[str, Any]:
    """Collect system package inventories; ``mode`` selects fast or full listings."""
    pkgs: dict[str, Any] = {}
    pkgs["pip"] = run_cmd(f'"{sys.executable}" -m pip list --format=json')
    sysname = platform.system().lower()
    if sysname == "linux":
        if which("dpkg"):
            pkgs["dpkg_list"] = run_cmd("dpkg -l")
        if which("apt"):
            if mode == "full":
                pkgs["apt_list_installed"] = run_cmd("apt list --installed 2>/dev/null")
            else:
                if which("apt-mark"):
                    pkgs["apt_mark_manual"] = run_cmd("apt-mark showmanual")
        if which("rpm"):
            pkgs["rpm_qa"] = run_cmd("rpm -qa")
    elif sysname == "darwin":
        if which("brew"):
            pkgs["brew_list"] = run_cmd("brew list --versions")
            pkgs["brew_cask_list"] = run_cmd("brew list --cask --versions")
    elif sysname == "windows":
        if which("choco"):
            pkgs["choco_list_local"] = run_cmd("choco list -lo")
    return pkgs


def collect_user_packages() -> dict[str, Any]:
    """Collect per-user pip, npm, and yarn package inventories."""
    user: dict[str, Any] = {}
    user["pip_user"] = run_cmd(f'"{sys.executable}" -m pip list --user --format=json')
    if which("npm"):
        user["npm_list_global_json"] = run_cmd("npm list -g --depth=0 --json")
        user["npm_prefix_user"] = run_cmd("npm config get prefix")
        user["npm_root_global"] = run_cmd("npm root -g")
    if which("yarn"):
        user["yarn_global_list"] = run_cmd("yarn global list --depth=0")
        user["yarn_global_dir"] = run_cmd("yarn global dir")
    return user


def collect_user_rubygems() -> dict[str, Any]:
    """Collect RubyGems environment and installed gem listings."""
    gems: dict[str, Any] = {}
    if which("gem"):
        gems["gem_env"] = run_cmd("gem env")
        gems["gem_list_user"] = run_cmd("gem list --user-install")
        gems["gem_list_local"] = run_cmd("gem list --local")
    else:
        gems["error"] = not_found() if STRICT_MISSING else {"ok": False, "stderr": "gem not found"}
    return gems


# -------- Homebrew taps --------


def brew_formulas_for_taps(taps: Sequence[str] | None) -> dict[str, Any]:
    """Collect installed Homebrew formulas grouped by the requested taps."""
    result: dict[str, Any] = {}
    if not taps:
        return result
    if not which("brew"):
        return {"error": "brew not found"} if not STRICT_MISSING else not_found()
    all_formulas = run_cmd("brew list --formula --versions --full-name")
    lines = (all_formulas.get("stdout") or "").splitlines()
    for tap in taps:
        tap = tap.strip()
        if not tap:
            continue
        prefix = f"{tap}/"
        matched = [ln for ln in lines if ln.startswith(prefix)]
        result[tap] = matched
    return result


# -------- Package manager layout --------


def package_managers_layout() -> dict[str, Any]:
    """Collect install prefixes and versions for the available package managers."""
    layout: dict[str, Any] = {}
    layout["pip_user_base"] = run_cmd(f'"{sys.executable}" -m site --user-base')
    layout["pip_user_site"] = run_cmd(f'"{sys.executable}" -m site --user-site')

    if which("npm"):
        layout["npm_version"] = run_cmd("npm -v")
        layout["npm_prefix_global"] = run_cmd("npm config get prefix -g")
        layout["npm_root_global"] = run_cmd("npm root -g")
        layout["npm_prefix_user"] = run_cmd("npm config get prefix")
    if which("yarn"):
        layout["yarn_version"] = run_cmd("yarn -v")
        layout["yarn_global_dir"] = run_cmd("yarn global dir")

    if which("gem"):
        layout["gem_env"] = run_cmd("gem env")

    if which("brew"):
        layout["brew_prefix"] = run_cmd("brew --prefix")
        layout["brew_cellar"] = run_cmd("brew --cellar")
        layout["brew_repo"] = run_cmd("brew --repo")

    if which("choco"):
        layout["choco_version"] = run_cmd("choco --version")
        layout["choco_info"] = run_cmd("choco info chocolatey")

    if which("dotnet"):
        layout["dotnet_info"] = run_cmd("dotnet --info")
        layout["dotnet_tools_list_global"] = run_cmd("dotnet tool list -g")

    return layout


# -------- Runtimes (normalized “not found”) --------


def _looks_like_java_missing(stderr_text: str) -> bool:
    if not stderr_text:
        return False
    s = stderr_text.lower()
    return any(
        sig in s
        for sig in [
            "unable to locate a java runtime",
            "no java runtime present",
            "do you want to install a jdk",
            "java runtime could not be located",
        ]
    )


def runtimes_info() -> dict[str, Any]:
    """Collect installed language runtimes, normalising absent tools to ``not found``."""
    r: dict[str, Any] = {}
    # Java
    if which("java"):
        j = run_cmd("java -version")
        if (not j["ok"]) or _looks_like_java_missing(j.get("stderr", "")):
            r["java_version"] = (
                not_found() if STRICT_MISSING else {"ok": False, "stderr": "java not found"}
            )
        else:
            r["java_version"] = {"ok": True, "stdout": j["stdout"], "stderr": j["stderr"]}
        r["java_home"] = os.environ.get("JAVA_HOME")
    else:
        r["java_version"] = (
            not_found() if STRICT_MISSING else {"ok": False, "stderr": "java not found"}
        )

    # .NET
    if which("dotnet"):
        r["dotnet_info"] = run_cmd("dotnet --info")
        r["dotnet_sdks"] = run_cmd("dotnet --list-sdks")
        r["dotnet_runtimes"] = run_cmd("dotnet --list-runtimes")
    else:
        r["dotnet_info"] = (
            not_found() if STRICT_MISSING else {"ok": False, "stderr": "dotnet not found"}
        )

    # Python (current + other shims)
    r["python_current"] = {
        "executable": sys.executable,
        "version": platform.python_version(),
        "impl": platform.python_implementation(),
    }
    python3_path = shutil.which("python3")
    if python3_path is not None and os.path.realpath(python3_path) != os.path.realpath(
        sys.executable
    ):
        r["python3_other"] = run_cmd("python3 -V")
        r["python3_path"] = python3_path
    python_path = shutil.which("python")
    if python_path is not None and os.path.realpath(python_path) != os.path.realpath(
        sys.executable
    ):
        r["python_legacy"] = run_cmd("python -V")
        r["python_path"] = python_path

    # Ruby
    if which("ruby"):
        r["ruby_version"] = run_cmd("ruby -v")
        if which("gem"):
            r["gem_version"] = run_cmd("gem -v")
        else:
            r["gem_version"] = (
                not_found() if STRICT_MISSING else {"ok": False, "stderr": "gem not found"}
            )
    else:
        r["ruby_version"] = (
            not_found() if STRICT_MISSING else {"ok": False, "stderr": "ruby not found"}
        )

    # Node.js (and npm/npx/yarn)
    if which("node"):
        r["node_version"] = run_cmd("node -v")
    else:
        r["node_version"] = (
            not_found() if STRICT_MISSING else {"ok": False, "stderr": "node not found"}
        )
    if which("npm"):
        r["npm_version"] = run_cmd("npm -v")
        r["npx_version"] = (
            run_cmd("npx -v")
            if which("npx")
            else (not_found() if STRICT_MISSING else {"ok": False, "stderr": "npx not found"})
        )
    else:
        r["npm_version"] = (
            not_found() if STRICT_MISSING else {"ok": False, "stderr": "npm not found"}
        )
    if which("yarn"):
        r["yarn_version"] = run_cmd("yarn -v")
    else:
        r["yarn_version"] = (
            not_found() if STRICT_MISSING else {"ok": False, "stderr": "yarn not found"}
        )

    return r


# -------- GPU --------


def gpu_info() -> dict[str, Any]:
    """Collect GPU and display-driver details for the current platform."""
    sysname = platform.system().lower()
    out: dict[str, Any] = {}

    if sysname == "windows":
        ps = (
            'powershell -Command "Get-WmiObject Win32_VideoController | '
            'Select-Object Name,DriverVersion,DriverDate | ConvertTo-Json"'
        )
        out["win32_videocontroller"] = run_cmd(ps)
        out["dxdiag"] = run_cmd("dxdiag /t dxdiag.txt && type dxdiag.txt & del dxdiag.txt")
        return out

    if sysname == "linux":
        if which("nvidia-smi"):
            out["nvidia_smi"] = run_cmd(
                "nvidia-smi --query-gpu=name,driver_version,vbios_version --format=csv,noheader"
            )
        if which("glxinfo"):
            out["glxinfo_B"] = run_cmd("glxinfo -B")
        if which("lspci"):
            out["lspci_vga"] = run_cmd("lspci -nnk | grep -A3 -E 'VGA|3D|Display'")
        if os.path.exists("/proc/driver/nvidia/version"):
            try:
                with open("/proc/driver/nvidia/version", encoding="utf-8", errors="ignore") as f:
                    out["proc_driver_nvidia_version"] = f.read().strip()
            except Exception as e:
                out["proc_driver_nvidia_version"] = f"error: {e}"
        return out

    if sysname == "darwin":
        out["system_profiler_displays"] = run_cmd("system_profiler SPDisplaysDataType")
        return out

    return out


# -------------------- Aggregation --------------------


def aggregate(opts: dict[str, Any]) -> dict[str, Any]:
    """Run the collectors enabled in ``opts`` and return the assembled report."""
    data: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "tool_version": get_version(),
        "basic": basic_info(),
    }

    if opts["cpu"]:
        data["cpu"] = cpu_info()
    if opts["memory"]:
        data["memory"] = memory_info()
    if opts["disks"]:
        data["disks"] = disks_info()
    if opts["network"]:
        data["network"] = network_info()
    if opts["listening_ports"]:
        data["listening_ports"] = listening_ports()
    if opts["processes"]:
        data["processes_top"] = processes_info(limit=30)

    if opts["firewall"]:
        distro_info = data["basic"].get("distro")
        data["firewall"] = firewall_rules(
            firewall_prefer=opts["firewall_prefer"], distro_info=distro_info
        )

    if opts["runtimes"]:
        data["runtimes"] = runtimes_info()
    if opts["gpu"]:
        data["gpu"] = gpu_info()

    if opts["packages"]:
        data["packages"] = collect_packages(opts["packages_mode"])
        data["user_packages"] = collect_user_packages()
        data["user_rubygems"] = collect_user_rubygems()
        if opts["brew_taps"]:
            data["brew_tap_formulas"] = brew_formulas_for_taps(opts["brew_taps"])

    if opts.get("services"):
        data["services"] = services_and_startup()
    if opts.get("hosts_dns"):
        data["hosts_dns"] = hosts_and_dns()
    if opts.get("logs"):
        data["logs"] = logs_overview()
    if opts.get("storage"):
        data["storage"] = storage_and_mounts()
    if opts.get("hardware_extra"):
        data["hardware_extra"] = hardware_extra()
    if opts.get("pkg_layout"):
        data["package_managers_layout"] = package_managers_layout()
    if opts.get("env"):
        data["env"] = env_and_misc()

    return data
