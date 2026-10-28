# RedeTI Recovery OS — Relatório SSH-5

- Etapa: `SSH-5 — consolidação SSH-4 e build da ISO`
- Gerado em UTC: `2026-10-28T21:12:52Z`
- Projeto: `SO_SYSTEM_RECOVERY`
- Branch: `main`
- Commit publicado: `df3cabd7941f5f49be3f438e539239f23ef6406e`
- Estado: `READY_FOR_PHYSICAL_TEST`

## Integração publicada

- `appliance/remote/lan-start.sh`
  - `systemd-run` usa `--no-block`, permitindo que o provisionamento USB de `authorized_keys` seja executado.
- `appliance/tests/test_lan_ssh.py`
  - Regressão para execução não bloqueante.
  - Teste de duas chaves Ed25519 distintas.
- VPN-3D preservada:
  - `redeti-status` continua incluído no compositor da ISO.
  - Destino: `/usr/local/bin/redeti-status`.

## Testes e segurança

- Suíte completa: **167 testes aprovados, 0 falhas**.
- CTest nativo LVGL: `3/3 PASS`.
- Sintaxe shell: `PASS`.
- `git diff --check`: `PASS`.
- Simulação de duas chaves públicas: `PASS`.
- Scan de segredos em código e pacote: `PASS`.
- Nenhuma credencial, token, chave privada ou dado de cliente incluído.

## Compilação

- Resultado: `PASS`.
- Versão: `v0.6.0`.
- Build tag: `b261028-211103`.
- ELF SHA-256: `ca74b3e84856ff514ccfff3016e4a1c299935ab192f51f846870e7d312efd4d3`.
- Commit do ELF/manifesto/ISO: `df3cabd7941f5f49be3f438e539239f23ef6406e`.

## ISO

- Caminho:
  `/home/paulo/RecoveryOS/out/RedeTI-Recovery-OS-appliance-df3cabd7-20261028T211115Z.iso`
- SHA-256:
  `31c77c7da645b2623a12f2de675c1f327d7ad9be41a96380276fe805519020bc`
- Sidecar verificado: `PASS`.
- Manifesto verificado: `PASS`.
- BIOS El Torito: `PASS`.
- UEFI El Torito: `PASS`.
- Estrutura SystemRescue: `PASS`.
- `customize.srm` SquashFS: `PASS`.
- `/usr/local/bin/redeti-status` presente: `PASS`.
- Permissão empacotada do `redeti-status`: `0755`.
- Correção `--no-block` presente na ISO: `PASS`.
- Versão/build/revisão presentes no ELF: `PASS`.
- ISOs anteriores preservadas: `PASS`.

## Restrições respeitadas

- QEMU: `NOT_RUN`.
- Inicialização da ISO no Hermes: `NOT_RUN`.
- Boot físico: `NOT_RUN`.
- Ventoy: não alterado automaticamente.
- Firewall, Tailscale e serviços de produção: não alterados.
- Discos de clientes: não acessados.
- ISO: não publicada no GitHub.

## Resultado final

`READY_FOR_PHYSICAL_TEST`

A ISO está pronta para homologação física autorizada. A homologação BIOS/Legacy, UEFI e a validação visual DRM/KMS ainda não foram executadas no Hermes.
