# RedeTI Recovery OS — Relatório VPN-3A

- Etapa: `VPN-3A`
- Gerado em UTC: `2026-10-27T17:47:13Z`
- Projeto validado: `SO_SYSTEM_RECOVERY`
- Branch: `main`
- Commit de referência: `0f563af29b13e6ea37e1f1eb944c8ae404fbf425`
- Escopo: preparação de credencial e diagnóstico remoto somente após gates de segurança.

## Credencial SSH

- Chave dedicada Ed25519 do Hermes-Agent: já existente; não foi sobrescrita.
- Fingerprint público: `SHA256:X0aMPVMJg8KQ23FTkpIINTbPwTVIDPo6G+AOiMLBpn0`.
- Permissão da chave privada: `0600`.
- A chave privada não foi exibida, copiada para o repositório, incluída em relatório ou enviada ao Recovery OS.
- A linha pública foi exibida apenas ao operador para provisionamento manual no Ventoy.

## Identidade do host

- Host `192.168.200.119`: TCP/22 alcançável.
- Fingerprint ED25519 observado novamente por `ssh-keyscan`, sem aceitar ou gravar em `known_hosts`: `SHA256:KFDorjY+RQyd1ji2Iudu+Nw6u/COVOAdkMaqDTvpxQw`.
- O valor coincide com a observação anterior, mas permanece **NÃO CONFIRMADO** até comparação presencial no próprio Recovery OS.
- Nenhum `StrictHostKeyChecking=no` foi usado.
- Nenhuma conexão SSH autenticada foi iniciada.

## Provisionamento

- Ventoy não foi montado pelo Hermes.
- `REDETI/authorized_keys` não foi alterado pelo Hermes.
- Chaves existentes e limite de quatro entradas não foram modificados.
- Pendência: operador deve inserir manualmente somente a linha pública fornecida, sem opções SSH adicionais.

## Diagnóstico remoto

- Autenticação SSH: `NOT_RUN`.
- Estado real do daemon Tailscale: `NOT_OBSERVED`.
- Estado real do registro VPN: `NOT_OBSERVED`.
- Arquivos `/run/redeti/remote-status.json` e `/run/redeti/lan-ssh-status.json`: `NOT_READ`.
- `systemctl`, `ss` e `ssh-diagnose.py --read-only` no Recovery OS: `NOT_RUN`.
- `tailscale up`, alteração de firewall e emissão/renovação/revogação de chaves: não executados.

## Resultado

- Estado VPN-3A: `BLOCKED_AGUARDANDO_CONFIRMACAO_E_PROVISIONAMENTO`.
- Não há causa comprovada para a falha de registro Tailscale nesta etapa.
- A conectividade TCP/22 não é considerada sucesso de SSH.

## Próximo passo obrigatório

1. Confirmar presencialmente que o fingerprint exibido no Recovery OS é exatamente o fingerprint observado nesta execução.
2. Inserir manualmente a linha pública dedicada no arquivo `REDETI/authorized_keys`, preservando as entradas existentes e o limite de quatro chaves.
3. Informar a conclusão desses dois gates.
4. Só então executar SSH com verificação normal de host e os comandos read-only da VPN-3.

## Segurança e publicação

- Nenhuma chave privada, token, auth key, credencial ou log bruto foi armazenado neste relatório.
- Nenhum arquivo do Ventoy, firewall, Tailscale ou serviço foi alterado.
- Resultado destinado à publicação no Git conforme autorização do operador.
