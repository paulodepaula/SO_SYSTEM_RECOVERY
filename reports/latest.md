# RedeTI Recovery OS — Relatório de etapa

- Etapa: `VPN-3B`
- Gerado em UTC: `2026-10-27T17:58:47Z`
- Commit: `0360fea637b64797faf68989fe65b507aafa5053`
- Branch: `main`
- Estado do repositório no momento do relatório: `clean`

## Alterações realizadas

- `reports/latest.json`
- `reports/latest.md`

## Testes

- Par Ed25519 do Hermes-Agent presente, fingerprint local calculado sem expor privada: PASS
- Permissão da chave privada 0600: PASS
- Mídia Ventoy/REDETI e arquivo de provisionamento: NOT_OBSERVED; nenhum mount removível presente
- Fingerprint ED25519 da rede coletado sem aceitar/gravar host key: PASS; confirmação presencial pendente
- Conexão SSH, ssh-diagnose.py e consultas /run/redeti: NOT_RUN por bloqueio de identidade/provisionamento
- Nenhuma alteração em ACL, OAuth, firewall, serviço de produção ou ISO: PASS

## Compilação

- Resultado: `NOT_RUN`

## ISO

- Caminho: `N/A`
- SHA256: `N/A`
- Sidecar verificado: `False`

## Falhas

- Provisionamento da chave pública não confirmado: Ventoy não está montado e arquivo autorizado não foi localizado
- Fingerprint do host não confirmado por canal confiável; known_hosts permanece sem entrada
- Estado de redeti-remote, redeti-tailscaled, SSH local, Tailscale e /run/redeti permanece NOT_OBSERVED
- Causa específica da falha de registro Tailscale permanece não comprovada

## Pendências

- Montar ou disponibilizar o Ventoy por canal local autorizado e confirmar a linha pública sem alterar outras entradas
- Confirmar presencialmente o fingerprint ED25519 atual de 192.168.200.119
- Após ambas as confirmações, autorizar conexão SSH read-only com a chave exclusiva e executar apenas os comandos VPN-3
- Não executar tailscale up, alterar firewall/ACL/OAuth, emitir chaves ou gerar ISO nesta etapa

## Publicação e segurança

- Relatório registrado somente localmente.
- Publicação no GitHub requer autorização explícita.
- Nenhuma ISO é publicada automaticamente.
- O relatório não contém credenciais, tokens ou dados de clientes.
