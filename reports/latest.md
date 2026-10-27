# RedeTI Recovery OS — Relatório de etapa

- Etapa: `BOOT-2`
- Gerado em UTC: `2026-10-27T02:14:22Z`
- Commit: `14982b3d299ddbcc10ab280775c687337131681a`
- Branch: `main`
- Estado do repositório no momento do relatório: `dirty`

## Alterações realizadas

- `appliance/README.md`
- `appliance/boot/launch.sh`
- `appliance/boot/redeti-early-splash.service`
- `appliance/build/build-local.sh`
- `appliance/build/compose-appliance.sh`
- `appliance/tests/test_build_recipe.py`
- `appliance/tests/test_splash.py`
- `reports/README.md`
- `reports/history/20261027T021228Z-boot-2-74d0386e.json`
- `reports/latest.json`
- `reports/latest.md`
- `scripts/generate-recovery-report.py`

## Testes

- 150 testes unittest aprovados
- Sintaxe shell/Python e systemd-analyze verify aprovados
- CTest nativo 3/3 aprovado
- SHA256 da ISO e sidecar verificados
- Conteúdo SRM e registros BIOS/UEFI inspecionados

## Compilação

- Resultado: `PASS`
- Manifesto: `{"app_version": "v0.6.0", "build_tag": "b261027-021342", "elf_sha256": "fb37b88b58bcd93a654cab06c0def8283b836caa71ae9ceeaf47b572e6449d4c", "iso_filename": "RedeTI-Recovery-OS-appliance-14982b3d-20261027T021352Z.iso", "iso_sha256": "2872e77a0aceebf54237abf8785b24c38eabbedc2f885b62284735a4a6e17be9", "source_commit": "14982b3d299ddbcc10ab280775c687337131681a"}`

## ISO

- Caminho: `/home/paulo/RecoveryOS/out/RedeTI-Recovery-OS-appliance-14982b3d-20261027T021352Z.iso`
- SHA256: `2872e77a0aceebf54237abf8785b24c38eabbedc2f885b62284735a4a6e17be9`
- Sidecar verificado: `True`

## Falhas

- Nenhuma falha registrada.

## Pendências

- Homologação física BIOS/Legacy e UEFI
- Validação visual DRM/KMS em hardware real

## Publicação e segurança

- Relatório registrado somente localmente.
- Publicação no GitHub requer autorização explícita.
- Nenhuma ISO é publicada automaticamente.
- O relatório não contém credenciais, tokens ou dados de clientes.
