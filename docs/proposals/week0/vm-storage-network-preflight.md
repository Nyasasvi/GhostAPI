# 16–17. VM / storage preflight plan and network-isolation comparison

**Status:** plan only. Nothing here has been executed:

- Tart is **not** installed; no VM exists; no image has been downloaded;
- no host storage, TCC, sudoers, SUID, firewall, or routing changes were made.

Certainty labels: **verified-source** means checked today against Tart's current source or official docs (commands not run locally). **estimate** means an assumption to be replaced by measurement. **unverified** means it must be tested in the preflight.

---

## 1. Host facts (probed 2026-09-29)

| Item | Value |
|---|---|
| Machine | Mac15,12, Apple M3 (8 cores), 16 GB RAM |
| macOS | 14.6 (23G80) |
| Free disk on `/` | about 24–25 GiB of 228 GiB |
| Toolchain | Swift 6.0.2 via Command Line Tools only (no Xcode); Python 3.12 + uv; Homebrew; git 2.39.5 |
| Missing | tart, swiftlint, gitleaks, ruff, mypy |

## 2. Verified Tart facts

| Fact | Source | Status |
|---|---|---|
| Tart now lives at `github.com/openai/tart` (the old `cirruslabs/tart` redirects) | HTTP 301 check | verified-source |
| Install: `brew install openai/tools/tart` | `openai/tart` `docs/quick-start.md` | verified-source |
| License: FSL-1.1-ALv2 (Tart and Softnet) | `LICENSE` files | verified-source |
| `tart create --from-ipsw <path|URL|latest>`; `--disk-size` default **50** GB | `Commands/Create.swift` | verified-source |
| `tart set <vm> --cpu N --memory MB --display WxH` | `Commands/Set.swift` | verified-source |
| `tart clone` uses APFS copy-on-write: "a cloned VM won't actually claim all the space right away" | `Commands/Clone.swift` | verified-source |
| `tart ip <vm> --wait <s>`; `tart stop <vm> --timeout <s>` (default 30); `tart delete <vm>` | `IP.swift`, `Stop.swift`, `Delete.swift` | verified-source |
| `tart run` flags `--no-graphics`, `--no-audio`, `--no-clipboard`, `--dir`, `--suspendable`, `--net-softnet`, `--net-softnet-allow/-block/-expose`, `--net-bridged`, `--net-host` | `Commands/Run.swift` | verified-source |
| USB flag defined as `noUSBAccessories`; the command-line spelling is probably `--no-usb-accessories` | `Run.swift` | **unverified**: confirm with `tart run --help` |
| `--net-host` throws **"requires macOS 26 (Tahoe) or newer"**; its vmnet host mode needs root or the `com.apple.vm.networking` entitlement | `Run.swift`, `Network/NetworkHost.swift` | verified-source, **unavailable on this host** |
| Softnet needs a **SUID bit or passwordless sudo** ("effectively gives the binary root privileges") | `openai/softnet` README | verified-source |
| `--suspendable` disables the entropy device; `--stacked` clones require a *remote* image | `Run.swift`, `Clone.swift` | verified-source; neither is used |
| Cirrus base-image template runs `scripts/update-tcc-database.sh` | `cirruslabs/macos-image-templates/templates/base.pkr.hcl` | verified-source; convenience images rejected |
| `tart exec` needs the Tart Guest Agent (bundled in non-vanilla Cirrus images) | `Commands/Exec.swift` | verified-source; not planned |

## 3. Lifecycle: `generic base -> sealed base -> app seed -> disposable trial clone`

| Stage | Name pattern | Booted? | Contents | Who |
|---|---|---|---|---|
| generic base (build VM) | `ghost-base-build` | yes, during build only | vanilla macOS from pinned IPSW; Setup Assistant done with no Apple ID; admin `ghostadmin` + standard GUI user `ghost` (auto-login); SSH key-only; sleep/screensaver/lock/updates/notifications/Spotlight off; guest packet filter (§6); stable-signed bridge app + LaunchAgent; Accessibility + Screen Recording granted to the bridge | you do the GUI steps; scripts do the rest over SSH |
| sealed base | `ghost-base-vNN` | **never** | `tart clone` of the stopped build VM; the VM adapter refuses to `run` any `ghost-base-v*` | adapter |
| app seed | `ghost-seed-<alias>-vNN` (+ `-s3`, `-s4` variants) | during seed prep only | sealed base + one app copied in over SSH (offline), first-run state, dummy data; variants for strata S3/S4 | you (holdouts are private) |
| trial clone | `ghost-t-<run>-<slot>-<attempt>` | yes | clone of a frozen seed; deleted after artifacts are committed; quarantined on extraction failure | adapter |

Reset = delete + reclone. No suspend/resume, no in-app cleanup, no learned `delete`/`undo`.

## 4. Exact commands (checked against source; **not executed; run only after approval**)

```bash
# Install and record versions/help verbatim into the preflight transcript
brew install openai/tools/tart
tart --version
tart run --help > preflight/tart-run-help.txt
tart create --help > preflight/tart-create-help.txt

# Generic base from a pinned IPSW (you download it from Apple's servers; record URL + SHA-256)
shasum -a 256 /ABS/PATH/<macOS-14.x-restore>.ipsw
tart create --from-ipsw=/ABS/PATH/<macOS-14.x-restore>.ipsw --disk-size 60 ghost-base-build
tart set ghost-base-build --cpu 4 --memory 6144 --display 1280x800
tart run ghost-base-build                  # GUI window: you complete Setup Assistant, enable Remote Login, grant permissions
tart ip ghost-base-build --wait 120

# Seal (never boot the sealed base)
tart stop ghost-base-build --timeout 60
tart clone ghost-base-build ghost-base-v01

# App seed (offline; app copied in over SSH)
tart clone ghost-base-v01 ghost-seed-<alias>-v01
tart run ghost-seed-<alias>-v01            # prepare seed, then stop it
tart stop ghost-seed-<alias>-v01 --timeout 60

# Disposable trial clone (the adapter runs `tart run` as a supervised background process)
tart clone ghost-seed-<alias>-v01 ghost-t-<run>-<slot>-<attempt>
tart run --no-audio --no-clipboard --no-usb-accessories ghost-t-<run>-<slot>-<attempt>   # add --no-graphics only after headless AX/capture is proven
tart ip ghost-t-<run>-<slot>-<attempt> --wait 120
ssh -N -o StrictHostKeyChecking=yes -o UserKnownHostsFile=<pinned> \
    -L 127.0.0.1:<host_port>:127.0.0.1:<guest_port> ghost@<ip>
tart stop ghost-t-<run>-<slot>-<attempt> --timeout 30
tart delete ghost-t-<run>-<slot>-<attempt> # only after artifact hashes are committed
```

`TART_HOME` (default `~/.tart`) must be one APFS volume holding the base, seeds, and clones. Tart's automatic pruning applies to its OCI cache, which this plan does not use. `TART_NO_AUTO_PRUNE=1` is set anyway to prevent surprise deletions.

## 5. Storage estimate

| Item | Size | Status |
|---|---|---|
| IPSW (macOS 14.x) | about 13–16 GB (can be archived off-disk after the base build; keep the hash) | estimate |
| Base VM disk (60 GB sparse logical) after install + provisioning | about 20–30 GB physical | estimate (Tart docs cite about 25 GB for its images) |
| Sealed base clone | about 0 GB at creation (copy-on-write) and stays near 0 if never booted | verified-source (CoW); growth unverified |
| App seeds (fixture, 2 dev apps, pilot, 3 finals) + S3/S4 variants | about 0.5–3 GB each, 5–20 GB total | estimate |
| Active trial clone growth (boot, logs, caches, swap) | about 1–5 GB transient, freed on delete | **unverified: measure** |
| Artifacts (raw AX, screenshots, logs, baseline screenshots) | about 3–5 GB per held-out app; about 10–15 GB development; **about 30–40 GB total** | estimate |
| Repo + SQLite | < 2 GB | estimate |
| Free-space margin for macOS/APFS health and swap | ≥ 20 GB | policy |

- **Realistic minimum free space to start Week 1:** about **90 GB** (IPSW + base + development seeds + one clone + development artifacts + margin).
- **Recommended for the full program:** **≥ 150 GB free.**
- **Now:** about 25 GiB. The host is **not VM-ready**.

**External APFS SSD:** reasonable if it is formatted APFS (encrypted preferred), NVMe-class over USB 3.2 Gen 2 or Thunderbolt, and holds the *entire* `TART_HOME` (copy-on-write only works within one volume). It must stay connected during runs; the sandbox guard checks the path, and a disconnect becomes `INVALID_INFRA` `HOST_IO_ERROR`. Expect slower boots than the internal disk. Artifacts can stay on the internal disk or move to a configured artifact root on the SSD.

## 6. Memory and CPU

- Host 16 GB: **one VM at a time** by default. Proposed allocation: **4 vCPU / 6 GB RAM**, 1280×800 display (the same display for all baseline arms).
- Host keeps about 10 GB for macOS, Python, and tools.
- A second concurrent VM (at 4 GB each) is tested only after single-VM measurements. It could roughly halve Week 6 wall-clock time.
- Apple's license allows at most 2 macOS VMs per Mac (§8).

## 7. Network-isolation comparison (for this macOS 14.6 host)

| Option | Guest internet isolation | Host → guest SSH/RPC | Host privileges | Install complexity | Security trade-offs | Reproducibility |
|---|---|---|---|---|---|---|
| A. Default NAT, nothing else | **none** | yes | none | none | unacceptable | high: **rejected** |
| **B. NAT + guest default-deny packet filter** (in the sealed base) + non-admin GUI user + per-trial probes | yes, while the guest filter is intact (enforced inside the guest) | yes (allow inbound TCP 22 from the NAT gateway; replies kept by state) | **none on host** | moderate: pf anchor + LaunchDaemon in the base; probe script | a process with guest root could disable it; mitigated by non-admin user, SIP on, and a fail-closed probe per attempt | high: baked into the sealed base; probe logged per attempt |
| C. Softnet `--net-softnet --net-softnet-block=0.0.0.0/0` (+ allow rules if needed) | yes, enforced **on the host**, outside the guest | **unverified** under block-all; must be tested live | **SUID root or passwordless sudo** for the softnet binary | brew install + privilege setup | strongest isolation; adds a root-equivalent helper on your laptop | high |
| D. `--net-host` | host-only | yes | root or entitlement | needs a **macOS 26 host** | not available on 14.6 without upgrading the host OS | n/a |
| E. Host firewall rules on the VM bridge interface | yes (host-enforced) | yes | root; changes host firewall | moderate | modifies host security configuration | medium |
| F. Bridged | none | yes | none | low | worse than NAT | **rejected** |

**Recommendation:** **B now** (no host privilege escalation), with the fail-closed per-attempt probe. **C as an optional upgrade**, only with your explicit approval of the SUID/sudo change. A defense-in-depth combination (B + C) is best if you approve C.

**Draft guest packet-filter rules for option B (gateway IP determined at provisioning; unverified):**

```text
set skip on lo0
block drop all
pass out quick inet proto udp from any port 68 to any port 67 keep state   # DHCP (needed for the guest IP and `tart ip`)
pass in  quick inet proto tcp from <nat_gateway> to any port 22 flags S/SA keep state
block drop quick inet6 all
```

DHCP remains an allowed path to the NAT gateway only. The probes below confirm that nothing else leaves the guest.

The rules are loaded at boot by a LaunchDaemon (`pfctl -E -f /etc/pf.ghost.conf`) in the sealed base.

**Acceptance probes (every attempt, before any action; fail closed):**

1. host → guest SSH works and the tunnel `/v1/health` returns 200;
2. guest DNS lookup of a public name fails or times out;
3. guest direct-IP TCP to two public IPs on 443 and 80 fails;
4. guest TCP to a canary listener the host opens for the probe (on the gateway address) fails;
5. results are written to the attempt log. Any failure gives `ISOLATION_PROBE_FAILED`, and the attempt is aborted.

## 8. Licensing considerations

- **Tart and Softnet (FSL-1.1-ALv2).** Permitted purposes explicitly include internal use and non-commercial research. A "Competing Use" (substituting for the software or for the licensor's products that use it) is excluded. Each release converts to Apache-2.0 two years after it is made available. **Research use: permitted.** Before any commercial GhostAPI offering, get legal review of whether hosting or bundling Tart is a competing use. GhostAPI should never vendor Tart source.
- **Apple macOS license (Sonoma SLA, §2B(iii), text checked today).** It allows up to two additional macOS instances in virtual machines on each Apple-branded computer you own or control, for software development, testing during development, macOS Server, or personal non-commercial use. Virtualized copies may not be used for service-bureau, time-sharing, or similar services. **One-laptop research fits.** A future hosted "learn your app in our Mac VMs" service needs legal review against the service-bureau restriction.
- **Target apps.** Check each app's license for restrictions on automated use or benchmarking as part of eligibility screening (you do this privately for holdouts).
- **LLM provider.** Aliased evidence packets and baseline screenshots of dummy data are sent to the provider under its API terms.

## 9. Preflight measurement plan (after storage is freed and Tart installation is approved)

Record everything into `experiments/preflight-<date>/` with a manifest:

1. host facts, `tart --version`, and verbatim `--help` outputs;
2. base build time; physical size of base, sealed base, and a seed (`du -sh` and APFS usage);
3. **20 cycles** of clone → boot → bridge-ready → app launch → stop → delete: **median and p95** per phase, and disk delta per cycle;
4. AX and capture health with and without `--no-graphics`;
5. network option B acceptance probes (and option C, only if approved);
6. permission persistence across clones, and across a bridge rebuild signed with the same stable identity;
7. memory pressure with 1 VM and, if safe, with 2 VMs.

The feasibility estimate is then recomputed from the measured medians and p95s.
