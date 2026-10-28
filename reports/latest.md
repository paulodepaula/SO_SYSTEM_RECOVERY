# RedeTI Recovery OS — Relatório VPN-3F

- Etapa: `VPN-3F — compilação da ISO com diagnóstico VPN seguro`
- Gerado em UTC: `2026-10-28T17:02:05Z`
- Projeto: `SO_SYSTEM_RECOVERY`
- Branch: `main`
- Commit-fonte: `dcaefc45bc2892d33d9e7f967b34e62144550526`
- Estado: `READY_FOR_PHYSICAL_TEST`

## Compilação

- Resultado: `PASS`
- Interface nativa: LVGL v9.6 direct DRM/KMS
- Versão exibida: `v0.6.0`
- Build tag: `b261028-165935`
- ELF: `/home/paulo/RecoveryOS/native-build/out/redeti-ui`
- ELF SHA-256: `a5e2fa3c4a79b6c16299c8643f94808b5bd38a74ab62ee37affa8de5fa4e810c`
- Testes CTest nativos: `3/3 PASS`

## ISO gerada

- Caminho: `/home/paulo/RecoveryOS/out/RedeTI-Recovery-OS-appliance-dcaefc45-20261028T165954Z.iso`
- ISO SHA-256: `3ee8e5e679caae1af1288277257628a37ffc8a89e88f9115f213bd6bab42c392`
- Sidecar: `/home/paulo/RecoveryOS/out/RedeTI-Recovery-OS-appliance-dcaefc45-20261028T165954Z.iso.sha256`
- Verificação do sidecar: `PASS`
- Manifesto: `/home/paulo/RecoveryOS/out/RedeTI-Recovery-OS-appliance-dcaefc45-20261028T165954Z.iso.buildinfo`
- Proveniência código/ELF/manifesto: `PASS`

## Conteúdo e boot

- `/usr/local/bin/redeti-status` presente no `customize.srm`: `PASS`
- Permissão empacotada: `0755`: `PASS`
- `customize.srm` identificado como SquashFS válido: `PASS`
- Entrada BIOS El Torito: `PASS`
- Entrada UEFI El Torito: `PASS`
- Estrutura SystemRescue e `/sysrescue.d`: `PASS`
- ISO anterior preservada: `PASS`

## Segurança

- `/run/redeti`: protegido com modo `0700`: `PASS`
- Socket administrativo `tailscaled.sock`: não exposto pela saída pública: `PASS`
- Status público separado em `/run/redeti-status`: `PASS`
- Campos do `redeti-status` allowlisted e somente leitura: `PASS`
- Credenciais, tokens e chaves privadas na ISO: `NÃO ENCONTRADOS`
- Dados de clientes na ISO/relatório: `NÃO ENCONTRADOS`
- Firewall, Tailscale e serviços de produção: não alterados
- Discos de clientes: não acessados

## Validações não executadas

- QEMU: `NOT_RUN` por restrição explícita
- Inicialização da ISO no Hermes: `NOT_RUN`
- Boot físico BIOS/Legacy: `NOT_RUN`
- Boot físico UEFI: `NOT_RUN`
- Validação visual DRM/KMS em hardware real: `NOT_RUN`

## Publicação

- ISO não publicada automaticamente.
- Este relatório, `reports/latest.json` e o histórico sanitizado serão publicados no GitHub conforme autorização.
- Nenhum código-fonte adicional foi alterado nesta etapa.

## Resultado final

`READY_FOR_PHYSICAL_TEST`

A ISO está compilada, identificada pelo commit correto, com SHA-256 e sidecar verificados. A próxima etapa é a homologação física autorizada; não foi executada no Hermes.
