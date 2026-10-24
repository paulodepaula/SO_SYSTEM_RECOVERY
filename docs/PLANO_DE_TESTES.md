# Plano de testes — RedeTI Recovery OS

## Camada 1 — v0.1, simulação
Requisitos: Python >=3.10, pytest opcional. Executar no diretório raiz:
```bash
python3 -m pytest -q
python3 -m recovery --fixture fixtures/bcd-corrupt.json
python3 -m recovery --fixture fixtures/failing-disk.json
python3 -m recovery --fixture fixtures/bitlocker-locked.json
```

| Caso | Evidência | Resultado esperado |
|---|---|---|
| BCD inválido | `bcd_valid=false` | BCD_INVALID; plano apenas simulado |
| SMART crítico + erros | `smart_health=critical; read_errors=18` | PHYSICAL_RISK; BLOCKED |
| BitLocker bloqueado | `bitlocker=locked` | BITLOCKER_HOLD; BLOCKED |
| Discos/Windows ausentes | listas vazias | DISK_MISSING; WINDOWS_NOT_FOUND |
| Entrada sem `kind` | JSON não marcado | CLI rejeita |
| Plano de reparo | ações propostas | Nunca executáveis na v0.1 |

## Camada 2 — coletores somente leitura (planejada)
- VM UEFI/GPT Windows saudável, Windows sem BCD válido, GPT com EFI ausente.
- VM BIOS/MBR, duas instalações Windows e boot dual.
- Volumes BitLocker desbloqueados/bloqueados; credenciais nunca capturadas.
- SMART/NVMe saudável, indisponível e crítico; discos virtuais com erros de leitura simulados.
- Garantir que todos os dispositivos permaneçam sem escrita pelo coletor.

## Camada 3 — reparos supervisionados (planejada)
- Usar somente imagens e VMs descartáveis com snapshots verificados.
- Inspecionar comando e alvo antes da autorização.
- Abortos para risco físico, destino incorreto, criptografia e backup ausente.
- Confirmar log, idempotência onde cabível, reversão quando possível.
- Verificar boot real posterior e preservar evidência de sucesso/falha.

## Camada 4 — ISO híbrida (planejada)
- Boot UEFI e Legacy nos perfis compatíveis.
- Testar menu de escolha Linux/WinPE e armazenamento USB.
- Confirmar licenciamento e direitos de redistribuição de componentes Microsoft.
- Testar memória limitada, tela de alta DPI, teclado ABNT2 e ausência de rede.

## Regras de homologação
Não executar comandos destrutivos em hardware de cliente. Qualquer piloto com disco físico exige autorização separada, plano de backup e validação de riscos.
