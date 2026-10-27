#!/usr/bin/env python3
"""Generate sanitized local RedeTI Recovery OS stage reports."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Iterable

SCHEMA = "redeti.recovery.build-report.v1"
SENSITIVE = re.compile(
    r"(?:authorized_keys|ts-authkey|tailscaled?\.state|\.env(?:\.|$)|"
    r"customer|client-disks|\.p12$|\.pfx$|\.ppk$|private.?key|token)",
    re.IGNORECASE,
)
SAFE_MANIFEST_KEYS = {"app_version", "build_tag", "source_commit", "elf_sha256", "iso_sha256", "iso_filename"}


def run_git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def safe_files(root: Path, commit: str, since: str | None) -> list[str]:
    if since:
        command = ["diff", "--name-only", f"{since}..{commit}"]
    else:
        command = ["show", "--format=", "--name-only", commit]
    raw = run_git(root, *command)
    result = []
    for item in raw.splitlines():
        item = item.strip()
        if item and not SENSITIVE.search(item) and item not in result:
            result.append(item)
    return result


def parse_manifest(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(errors="replace").splitlines():
        key, separator, value = line.partition("=")
        if separator and key in SAFE_MANIFEST_KEYS:
            values[key] = value.strip()
    return values


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clean_values(values: Iterable[str]) -> list[str]:
    return [value for value in values if value and not SENSITIVE.search(value)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--stage", default="BOOT")
    parser.add_argument("--commit", required=True)
    parser.add_argument("--since")
    parser.add_argument("--iso", type=Path)
    parser.add_argument("--compile-result", default="NOT_RUN")
    parser.add_argument("--test", action="append", default=[])
    parser.add_argument("--failure", action="append", default=[])
    parser.add_argument("--pending", action="append", default=[])
    parser.add_argument("--report-root", type=Path)
    args = parser.parse_args()

    root = args.repo_root.resolve()
    report_root = (args.report_root or root / "reports").resolve()
    history = report_root / "history"
    report_root.mkdir(parents=True, exist_ok=True)
    history.mkdir(parents=True, exist_ok=True)

    commit = run_git(root, "rev-parse", "--verify", args.commit)
    branch = run_git(root, "branch", "--show-current") or "DETACHED"
    status = "clean" if not run_git(root, "status", "--porcelain") else "dirty"
    generated = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    iso = args.iso.resolve() if args.iso else None
    manifest = parse_manifest(Path(f"{iso}.buildinfo")) if iso else {}
    iso_hash = sha256(iso) if iso else None
    changed = safe_files(root, commit, args.since)
    tests = clean_values(args.test)
    failures = clean_values(args.failure)
    pending = clean_values(args.pending)

    record = {
        "schema": SCHEMA,
        "generated_at_utc": generated,
        "stage": args.stage,
        "commit": commit,
        "branch": branch,
        "repository_status": status,
        "changes": changed,
        "tests": tests,
        "compilation": {"result": args.compile_result, "manifest": manifest},
        "iso": {
            "path": str(iso) if iso else None,
            "sha256": iso_hash or manifest.get("iso_sha256"),
            "sidecar_verified": bool(iso and Path(f"{iso}.sha256").is_file()),
        },
        "failures": failures,
        "pending": pending,
        "publication": "LOCAL_ONLY_AUTHORIZATION_REQUIRED",
        "safety": {
            "credentials_included": False,
            "customer_data_included": False,
            "iso_published_automatically": False,
        },
    }

    short = commit[:8]
    history_path = history / f"{generated.replace(':', '').replace('-', '')}-{args.stage.lower()}-{short}.json"
    latest_json = report_root / "latest.json"
    latest_md = report_root / "latest.md"
    encoded = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    history_path.write_text(encoded)
    latest_json.write_text(encoded)

    iso_text = record["iso"]["path"] or "N/A"
    iso_sha = record["iso"]["sha256"] or "N/A"
    lines = [
        "# RedeTI Recovery OS — Relatório de etapa",
        "",
        f"- Etapa: `{args.stage}`",
        f"- Gerado em UTC: `{generated}`",
        f"- Commit: `{commit}`",
        f"- Branch: `{branch}`",
        f"- Estado do repositório no momento do relatório: `{status}`",
        "",
        "## Alterações realizadas",
        "",
    ]
    lines += [f"- `{item}`" for item in changed] or ["- Nenhuma alteração de código registrada para este commit."]
    lines += ["", "## Testes", ""]
    lines += [f"- {item}" for item in tests] or ["- Não informado nesta execução."]
    lines += ["", "## Compilação", "", f"- Resultado: `{args.compile_result}`"]
    if manifest:
        lines += [f"- Manifesto: `{json.dumps(manifest, ensure_ascii=False, sort_keys=True)}`"]
    lines += ["", "## ISO", "", f"- Caminho: `{iso_text}`", f"- SHA256: `{iso_sha}`", f"- Sidecar verificado: `{record['iso']['sidecar_verified']}`"]
    lines += ["", "## Falhas", ""]
    lines += [f"- {item}" for item in failures] or ["- Nenhuma falha registrada."]
    lines += ["", "## Pendências", ""]
    lines += [f"- {item}" for item in pending] or ["- Nenhuma pendência registrada."]
    lines += ["", "## Publicação e segurança", "", "- Relatório registrado somente localmente.", "- Publicação no GitHub requer autorização explícita.", "- Nenhuma ISO é publicada automaticamente.", "- O relatório não contém credenciais, tokens ou dados de clientes.", ""]
    latest_md.write_text("\n".join(lines))
    print(f"Report: {latest_md}")
    print(f"History: {history_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
