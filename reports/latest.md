# RedeTI Recovery OS — Relatório de etapa

- Etapa: `VPN-3`
- Gerado em UTC: `2026-10-27T11:59:52Z`
- Commit: `7043c220fd0a1002da0cdd0c21bb55e5fa1c99e4`
- Branch: `main`
- Estado do repositório no momento do relatório: `dirty`

## Alterações realizadas

- `reports/history/20261027T113713Z-vpn-2-a06a73e9.json`
- `reports/latest.json`
- `reports/latest.md`

## Testes

- Conectividade Hermes para 192.168.200.119: ICMP PASS; TCP/22 PASS
- Fingerprint ED25519 coletado sem aceitar ou gravar em known_hosts: PASS; confirmação confiável pendente
- 69 testes VPN/enrollment/SSH/segurança: PASS
- DNS/TLS Hermes para api.tailscale.com: PASS; resposta HTTP 401 sem credenciais
- Relógio/NTP Hermes: PASS; NTPSynchronized=yes
- Varredura read-only de chaves e mídias: chave Recovery ausente; nenhuma mídia provisionadora montada
- Nenhuma alteração no Recovery OS, Hermes, firewall, Tailscale, Cloudflare, ACL ou ISO: PASS

## Compilação

- Resultado: `NOT_RUN`

## ISO

- Caminho: `N/A`
- SHA256: `N/A`
- Sidecar verificado: `False`

## Falhas

- Sessão SSH não estabelecida: chave privada correspondente não disponível no Hermes
- Fingerprint do host não confirmado por canal confiável; known_hosts não alterado
- Estado de redeti-remote, redeti-tailscaled, Tailscale, firewall e /run/redeti do Recovery OS: NOT_OBSERVED
- Causa da mensagem Falha no registro permanece não comprovada entre provisionamento, autenticação, conectividade, autorização e daemon

## Pendências

- Disponibilizar a chave privada correspondente por canal local protegido, sem colar conteúdo no chat/Git
- Confirmar por canal confiável o fingerprint ED25519 do host 192.168.200.119
- Após confirmação, autorizar somente os comandos SSH read-only especificados: status JSON, systemctl status, ss e ssh-diagnose.py --read-only
- Se a evidência confirmar chave/tag/ACL inválida, autorizar separadamente a correção; não gerar, renovar, revogar ou reutilizar chave automaticamente
- Se necessário, autorizar separadamente alteração de OAuth/ACL/broker ou nova ISO

## Publicação e segurança

- Relatório registrado somente localmente.
- Publicação no GitHub requer autorização explícita.
- Nenhuma ISO é publicada automaticamente.
- O relatório não contém credenciais, tokens ou dados de clientes.
