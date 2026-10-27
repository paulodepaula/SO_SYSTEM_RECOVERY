# RedeTI Recovery OS — Relatório de etapa

- Etapa: `VPN-1-FINAL`
- Gerado em UTC: `2026-10-27T03:00:04Z`
- Commit: `e8950d562e455f1945249f435b1ca133901641de`
- Branch: `main`
- Estado do repositório no momento do relatório: `clean`

## Alterações realizadas

- `appliance/README.md`
- `appliance/boot/launch.sh`
- `appliance/build/compose-appliance.sh`
- `appliance/remote/enrollment-agent.py`
- `appliance/remote/enrollment_client.py`
- `appliance/remote/start.sh`
- `appliance/tests/test_enrollment_client.py`
- `appliance/tests/test_remote.py`
- `services/recovery_enrollment/README.md`

## Testes

- 157 testes unittest: PASS (resultado previamente validado)
- Pareamento, aprovação/negação, expiração, replay e falha fail-closed: PASS (simulação previamente validada)
- Regressão SSH local, firewall, boot e splash: PASS (resultado previamente validado)
- CTest nativo DRM/KMS: 3/3 PASS (resultado previamente validado)
- SHA256, ISO bootável, BIOS/UEFI e conteúdo SRM: PASS (resultado previamente validado)

## Compilação

- Resultado: `PASS`
- Manifesto: `{"app_version": "v0.6.0", "build_tag": "b261027-024649", "elf_sha256": "d886dcebe40a2c292ec14c851f71fd95d6f78b9b6e34211772737f4585193a65", "iso_filename": "RedeTI-Recovery-OS-appliance-e8950d56-20261027T024658Z.iso", "iso_sha256": "913a2ffe71aedcb4d160f2b7ab484925323f121b92d1382cc472c30bba4e7552", "source_commit": "e8950d562e455f1945249f435b1ca133901641de"}`

## ISO

- Caminho: `/home/paulo/RecoveryOS/out/RedeTI-Recovery-OS-appliance-e8950d56-20261027T024658Z.iso`
- SHA256: `913a2ffe71aedcb4d160f2b7ab484925323f121b92d1382cc472c30bba4e7552`
- Sidecar verificado: `True`

## Falhas

- Enrollment Broker ainda não está implantado como serviço de produção
- OAuth Tailscale real e emissão/revogação de auth key não foram executados
- SSH remoto pela VPN permanece não homologado; timeout de banner anterior sem validação física

## Pendências

- Autorização específica para integrar Service Desk autenticado, MFA/RBAC/CSRF e ingress HTTPS
- Autorização específica para usar credencial OAuth restrita auth_keys/tag:redeti-recovery em ambiente controlado
- Homologação física do pareamento, Tailscale, TCP/22, banner SSH, comando remoto e encerramento
- Publicação no GitHub, se desejada, depende de autorização separada

## Publicação e segurança

- Relatório registrado somente localmente.
- Publicação no GitHub requer autorização explícita.
- Nenhuma ISO é publicada automaticamente.
- O relatório não contém credenciais, tokens ou dados de clientes.
