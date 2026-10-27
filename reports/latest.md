# RedeTI Recovery OS — Relatório de etapa

- Etapa: `BOOT-2`
- Gerado em UTC: `2026-10-27T02:12:28Z`
- Commit: `74d0386e1acb18ba5565710d308ecec307117e8d`
- Branch: `main`
- Estado do repositório no momento do relatório: `dirty`

## Alterações realizadas

- `appliance/README.md`
- `appliance/boot/launch.sh`
- `appliance/boot/redeti-early-splash.service`
- `appliance/build/compose-appliance.sh`
- `appliance/tests/test_build_recipe.py`
- `appliance/tests/test_splash.py`

## Testes

- 149 testes unittest aprovados
- Sintaxe shell/Python e systemd-analyze verify aprovados
- CTest nativo 3/3 aprovado
- SHA256 da ISO e sidecar verificados
- Conteúdo SRM e registros BIOS/UEFI inspecionados

## Compilação

- Resultado: `PASS`
- Manifesto: `{"app_version": "v0.6.0", "build_tag": "b261027-020117", "elf_sha256": "925a33973a5649616ab99ae54e3712a9fa7e2f17f9754c84a311f29de116fd0e", "iso_filename": "RedeTI-Recovery-OS-appliance-74d0386e-20261027T020126Z.iso", "iso_sha256": "c10467b53af65e346cf7ea433946cc3f8918c87a3757b24b19c21a5018caf25d", "source_commit": "74d0386e1acb18ba5565710d308ecec307117e8d"}`

## ISO

- Caminho: `/home/paulo/RecoveryOS/out/RedeTI-Recovery-OS-appliance-74d0386e-20261027T020126Z.iso`
- SHA256: `c10467b53af65e346cf7ea433946cc3f8918c87a3757b24b19c21a5018caf25d`
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
