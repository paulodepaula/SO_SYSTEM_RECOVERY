# RedeTI Recovery OS — Relatório VPN-3D

- Etapa: `VPN-3D — saída pública para diagnóstico SSH`
- Gerado em UTC: `2026-10-27T23:19:01Z`
- Projeto: `SO_SYSTEM_RECOVERY`
- Branch: `main`
- Commit de referência: `40087f3`
- Estado: `IMPLEMENTADO_LOCALMENTE_AGUARDANDO_REVISAO`
- Publicação Git: `NÃO REALIZADA — autorização de push não fornecida`

## Resultado

Foi implementada uma saída separada e sanitizada para o operador `paulo`.

- `/run/redeti` continua privado, `root:root`, modo `0700`.
- O socket `/run/redeti/tailscaled.sock` não é exposto.
- Nova árvore pública: `/run/redeti-status`, criada como `root:root`, modo `0755`.
- Arquivos públicos são temporários, escritos atomicamente e modo `0644`.
- `redeti-status` lê somente `vpn-status.json` e imprime campos allowlisted:
  `vpn_state`, `connectivity`, `failure_code`, `registration_stage`,
  `vpn_ssh_mode` e `diagnostic_complete=read_only`.
- Não são publicados IPs, tokens, auth keys, OAuth, URLs secretas, logs ou estado integral da tailnet.
- `ssh-diagnose.py` passou a ler as saídas públicas sanitizadas de VPN e SSH, sem acessar os JSONs privados.
- Falhas de provisionamento, tag, autenticação e conectividade possuem códigos distintos quando comprovadas pela evidência local; caso contrário, o estado é genérico.
- A lógica de diagnóstico não executa `tailscale up`, não altera firewall e não consulta o socket administrativo.

## Independência do early splash

- `redeti-early-splash.service` não é requisito do processo privilegiado de VPN.
- O teste confirmou que a publicação de status não depende do splash.
- A sequência existente do `launch.sh`, incluindo parada do splash antes do dashboard nativo e fallback sem framebuffer, permaneceu coberta pelos testes.
- Não houve boot físico nem teste em ISO nesta etapa.

## Testes executados

Comando:

```text
python3 -m unittest discover -s appliance/tests -v
```

Resultado: **165 testes aprovados**.

Validações adicionais:

```text
bash -n appliance/remote/start.sh appliance/remote/lan-start.sh appliance/build/compose-appliance.sh
python3 -m py_compile appliance/remote/ssh-diagnose.py appliance/remote/redeti-status
git diff --check
```

Todos concluídos com sucesso.

## Arquivos alterados

- `appliance/remote/start.sh`
- `appliance/remote/lan-start.sh`
- `appliance/remote/ssh-diagnose.py`
- `appliance/remote/redeti-status`
- `appliance/build/compose-appliance.sh`
- `appliance/remote/SSH_DIAGNOSTICS.md`
- `appliance/tests/test_redeti_status.py`

## Segurança e escopo

- Nenhum `chmod 777` foi usado.
- Nenhuma ACL foi criada ou alterada.
- Nenhum OAuth, token ou auth key foi modificado.
- Nenhum arquivo do Recovery OS físico foi alterado.
- Nenhum serviço físico foi reiniciado.
- Nenhuma ISO foi gerada ou publicada.
- Nenhum segredo apareceu nos relatórios ou nos testes.

## Próxima etapa

Uma nova ISO é necessária para levar a implementação ao Recovery OS físico. Antes disso, revisar o diff e autorizar separadamente a geração/teste da ISO. O push Git também permanece pendente de autorização explícita.
