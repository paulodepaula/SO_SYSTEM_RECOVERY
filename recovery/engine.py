"""Pure diagnostic rule engine: reads only a supplied JSON fixture."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class Finding:
    id: str
    severity: str
    title: str
    evidence: str
    recommendation: str

@dataclass(frozen=True)
class ProposedAction:
    id: str
    title: str
    risk: str
    requires_backup: bool
    status: str = "SIMULATION_ONLY_NOT_EXECUTABLE"


def analyze(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Produce an explainable report without operating-system commands."""
    findings: list[Finding] = []
    actions: list[ProposedAction] = []
    disks = snapshot.get("disks", [])
    windows = snapshot.get("windows_installations", [])
    if not disks:
        findings.append(Finding("DISK_MISSING", "critical", "Nenhum disco detectado", "disks=[]", "Inspecionar firmware, controladora, cabos e alimentacao."))
    physical_risk = False
    for disk in disks:
        disk_id = str(disk.get("id", "unknown"))
        smart = disk.get("smart_health", "unknown")
        errors = int(disk.get("read_errors", 0))
        if smart in ("failed", "critical") or errors > 0:
            physical_risk = True
            findings.append(Finding("PHYSICAL_RISK", "critical", f"Risco de falha fisica: {disk_id}", f"SMART={smart}; erros_leitura={errors}", "Nao executar reparos no disco original; considerar imagem com ferramenta apropriada."))
        elif smart == "unknown":
            findings.append(Finding("SMART_UNAVAILABLE", "warning", f"Saude desconhecida: {disk_id}", "SMART indisponivel", "Obter diagnostico de saude antes de autorizar escrita."))
    if not windows:
        findings.append(Finding("WINDOWS_NOT_FOUND", "warning", "Instalacao Windows nao identificada", "windows_installations=[]", "Verificar particoes, criptografia e metadados do sistema."))
    for os_entry in windows:
        if os_entry.get("bitlocker") in ("locked", "unknown"):
            findings.append(Finding("BITLOCKER_HOLD", "critical", "Volume BitLocker bloqueado ou indeterminado", f"Estado: {os_entry.get('bitlocker')}", "Exigir chave de recuperacao autorizada; nao tentar contornar criptografia."))
        if os_entry.get("boot_mode") == "uefi" and os_entry.get("efi_present") is False:
            findings.append(Finding("EFI_MISSING", "high", "Particao EFI nao identificada", "UEFI=true; efi_present=false", "Validar tabela de particoes e backup antes de qualquer reconstrucao."))
            actions.append(ProposedAction("REVIEW_EFI", "Avaliar recuperacao da estrutura EFI", "high", True))
        if os_entry.get("bcd_valid") is False:
            findings.append(Finding("BCD_INVALID", "high", "BCD aparentemente inconsistente", "bcd_valid=false (fixture)", "Inspecionar entradas BCD e configuracao firmware antes de reconstruir."))
            actions.append(ProposedAction("REVIEW_BCD", "Avaliar reconstrucao supervisionada do BCD", "high", True))
        if os_entry.get("offline_system_integrity") == "corrupt":
            findings.append(Finding("SYSTEM_CORRUPT", "high", "Arquivos do Windows com inconsistencia", "offline_system_integrity=corrupt (fixture)", "Planejar SFC/DISM offline apos avaliar a integridade do disco."))
            actions.append(ProposedAction("REVIEW_SYSTEM_REPAIR", "Avaliar reparo offline de arquivos", "medium", True))
    gated = physical_risk or any(f.id == "BITLOCKER_HOLD" for f in findings) or any(f.id == "SMART_UNAVAILABLE" for f in findings)
    return {
        "schema": "redeti.recovery.report.v1",
        "source": "user_supplied_fixture_only",
        "real_hardware_access": False,
        "write_operations_enabled": False,
        "repair_gate": "BLOCKED" if gated else "MANUAL_REVIEW_REQUIRED",
        "findings": [asdict(x) for x in findings],
        "proposed_actions": [asdict(x) for x in actions],
        "disclaimer": "Indicadores derivados somente do fixture; nao comprovam falhas em hardware real. Nenhuma acao de reparo e executavel nesta versao."
    }
