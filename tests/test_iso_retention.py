"""ISO retention tests: tiny simulated files only, no real ISO or client disks."""
from pathlib import Path
import hashlib
import subprocess
import tempfile

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prune-recovery-isos.sh"


def create_iso(folder, name, contents=b"simulation"):
    file = folder / name
    file.write_bytes(contents)
    checksum = hashlib.sha256(contents).hexdigest()
    (folder / (name + ".sha256")).write_text(f"{checksum}  {name}\n")
    return file


def invoke(mode, output, keep):
    return subprocess.run(
        ["bash", str(SCRIPT), mode, str(output), str(keep)],
        capture_output=True, text=True, check=False,
    )


def test_dry_run_preserves_everything(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    old = create_iso(out, "RedeTI-Recovery-OS-alpha-20261024T110000Z.iso")
    new = create_iso(out, "RedeTI-Recovery-OS-alpha-20261024T120000Z.iso")
    result = invoke("--dry-run", out, new)
    assert result.returncode == 0, result.stderr
    assert "SERIA REMOVIDA" in result.stdout
    assert old.exists() and new.exists()


def test_apply_keeps_one_verified_iso_and_unrelated_files(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    old = create_iso(out, "RedeTI-Recovery-OS-alpha-20261024T110000Z.iso")
    historical = create_iso(out, "RedeTI-Recovery-OS-alpha.iso")
    new = create_iso(out, "RedeTI-Recovery-OS-appliance-20261024T120000Z.iso")
    other = create_iso(out, "outro-projeto.iso")
    unknown = create_iso(out, "RedeTI-Recovery-OS-custom-do-not-delete.iso")
    base = tmp_path / "base"
    base.mkdir()
    original = create_iso(base, "systemrescue-13.02-amd64.iso")
    result = invoke("--apply", out, new)
    assert result.returncode == 0, result.stderr
    assert not old.exists() and not (out / (old.name + ".sha256")).exists()
    assert not historical.exists()
    assert new.exists() and (out / (new.name + ".sha256")).exists()
    assert other.exists() and unknown.exists() and original.exists()


def test_failed_checksum_protects_existing_old_iso(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    old = create_iso(out, "RedeTI-Recovery-OS-alpha-20261024T110000Z.iso")
    new = create_iso(out, "RedeTI-Recovery-OS-alpha-20261024T120000Z.iso")
    new.write_bytes(b"not matching the checksum")
    result = invoke("--apply", out, new)
    assert result.returncode != 0
    assert old.exists() and new.exists()


def test_missing_checksum_protects_existing_old_iso(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    old = create_iso(out, "RedeTI-Recovery-OS-alpha-20261024T110000Z.iso")
    new = out / "RedeTI-Recovery-OS-alpha-20261024T120000Z.iso"
    new.write_bytes(b"build in progress")
    result = invoke("--apply", out, new)
    assert result.returncode != 0
    assert old.exists()


def test_base_directory_refused(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    keep = create_iso(base, "RedeTI-Recovery-OS-alpha-20261024T120000Z.iso")
    result = invoke("--apply", base, keep)
    assert result.returncode != 0 and keep.exists()


def test_keep_outside_output_directory_refused(tmp_path):
    a = tmp_path / "out"
    a.mkdir()
    b = tmp_path / "elsewhere"
    b.mkdir()
    old = create_iso(a, "RedeTI-Recovery-OS-alpha-20261024T110000Z.iso")
    keep = create_iso(b, "RedeTI-Recovery-OS-alpha-20261024T120000Z.iso")
    result = invoke("--apply", a, keep)
    assert result.returncode != 0
    assert old.exists() and keep.exists()
