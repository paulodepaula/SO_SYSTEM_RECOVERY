# RedeTI Recovery OS — Relatório VPN-4

- Etapa: `VPN-4 — investigação de falha de autenticação Tailscale`
- Gerado em UTC: `2026-10-28T21:16:00Z`
- Projeto: `SO_SYSTEM_RECOVERY`
- Código-fonte consultado: `df3cabd7941f5f49be3f438e539239f23ef6406e`
- Estado: `BLOCKED_PHYSICAL_EVIDENCE_REQUIRED`

## Evidência física fornecida

```text
vpn_state=vpn_auth_failed
connectivity=failed
failure_code=authentication
registration_stage=registration
vpn_ssh_mode=managed
diagnostic_complete=read_only
```

Interpretação: o daemon chegou à etapa de registro, mas a autenticação Tailscale falhou. O estado é diferente de ausência de provisionamento, falha de daemon, firewall ou falta de IP.

## Mecanismo de registro identificado

Resultado: `Ventoy auth key path — comprovado pelo fluxo da ISO e pelo modo managed`.

Evidências:

1. A ISO padrão não configura `/etc/redeti/enrollment-url`; o Enrollment Broker é opt-in.
2. O agente central, quando habilitado, entrega uma chave em tmpfs, mas não ativa `vpn_ssh_mode=managed`.
3. O modo `managed` só é ativado em `remote/start.sh` após a leitura de uma partição USB aprovada e a detecção do marcador vazio:
   `REDETI/tailscale-ssh.enable`.
4. A mesma rota lê e valida:
   `REDETI/ts-authkey`.
5. A chamada usa a chave em RAM via `--auth-key=file:/run/redeti/ts-authkey` e anuncia:
   `tag:redeti-recovery`.

Conclusão: o estado físico observado confirma a rota Ventoy com Tailscale SSH gerenciado habilitado.

## Credencial de provisionamento

Contrato esperado, sem exibir valor:

- Arquivo: `REDETI/ts-authkey`.
- Uma única linha ASCII.
- Regex: `tskey-auth-[A-Za-z0-9_-]{10,240}`.
- Máximo de 300 bytes.
- Copiada para tmpfs com modo `0600`.
- Removida ao finalizar a tentativa.
- Não incluída na ISO, Git, relatórios ou logs públicos.

A presença, validade temporal, revogação e permissões reais da chave não podem ser confirmadas pelo Hermes sem leitura autorizada do estado físico/Tailscale. O script remove o arquivo temporário após a tentativa, portanto sua ausência posterior não prova ausência no Ventoy.

## Classificação da falha

Comprovado:

- Falha ocorreu durante registro/autenticação.
- O modo gerenciado estava explicitamente ativo.
- A ISO classificou o resultado como `authentication`.
- A ISO não classificou como `provisioning_missing`, `provisioning_invalid`, `connectivity_firewall`, `connectivity_daemon` ou `connectivity_no_ip`.

Ainda não comprovado:

- Auth key expirada.
- Auth key revogada ou já consumida.
- Tag `tag:redeti-recovery` não autorizada para a chave.
- Permissão OAuth de criação da tag ausente.
- ACL/grants da tailnet recusando o dispositivo ou o acesso gerenciado.
- Falha transitória de controle Tailscale.

A implementação atual agrupa padrões de `auth`, `unauthorized`, `expired` e `invalid key` em `vpn_auth_failed`; portanto o código não distingue sozinho expiração, revogação e tag/ACL.

## `vpn_ssh_mode=managed`

O modo corresponde à configuração autorizada somente se o operador autorizou o marcador físico `REDETI/tailscale-ssh.enable` e a tailnet possui política restritiva para:

- destino: `tag:redeti-recovery`;
- usuário: `paulo`;
- acesso: somente TCP/22;
- técnicos/grupo autorizado;
- default-deny para demais origens e destinos.

A presença do marcador foi evidenciada pelo estado `managed`; a autorização efetiva da ACL não foi comprovada neste diagnóstico.

## SSH LAN do Hermes

- TCP/22: `PASS`.
- Autenticação SSH: `NOT_RUN`.
- Host key apresentada: não coincide com a entrada confiável local.
- StrictHostKeyChecking: mantido.
- `known_hosts`: não alterado.

Assim, não foi executado `redeti-status` via SSH nem foram lidos logs privados do Recovery OS.

## Diagnósticos locais executados

- 54 testes offline de provisionamento, status, diagnóstico SSH, Enrollment Broker, cliente de enrollment, OAuth fake e Ventoy: `PASS`.
- Compilação Python dos módulos remotos: `PASS`.
- Shell syntax dos scripts relevantes: `PASS`.
- Nenhum `tailscale up` executado.
- Nenhuma auth key criada ou revogada.
- Nenhuma ACL, firewall, OAuth ou serviço alterado.
- Nenhum Ventoy ou disco físico modificado.

No Hermes:

- `/etc/redeti-recovery`: presente, `root:root`, modo `0700`.
- `oauth-client-id`: ausente.
- `oauth-client-secret`: ausente.
- Checker OAuth: `BLOCKED` por execução sem root; nenhuma credencial foi lida ou exibida.

## Correção mínima sem nova ISO

É possível corrigir somente pelo Ventoy, sem gerar outra ISO, se a causa for a auth key:

1. Confirmar na tailnet, por canal administrativo, que `tag:redeti-recovery` existe e que a política permite o registro.
2. Obter uma auth key curta, efêmera, de uso único, com a tag autorizada.
3. Substituir somente `REDETI/ts-authkey` no Ventoy por essa chave, preservando o marcador vazio `REDETI/tailscale-ssh.enable`.
4. Reiniciar o Recovery OS.
5. Repetir `redeti-status`.
6. Somente após confirmação independente da host key, testar SSH com StrictHostKeyChecking estrito.

Não executar `tailscale up` manualmente no Recovery OS e não reutilizar uma chave cuja validade ou revogação esteja incerta.

## Comandos read-only para a sessão física autorizada

Executar localmente no Recovery OS, sem imprimir chaves ou logs completos:

```bash
findmnt -n -o FSTYPE -T /run/redeti
stat -c '%A %a %U:%G %s %n' /run/redeti /run/redeti-status /run/redeti-status/vpn-status.json
systemctl status redeti-tailscaled --no-pager
journalctl -b -u redeti-tailscaled --no-pager | grep -Ei 'auth|unauthor|forbidden|expired|invalid|tag|register' | sed -E 's/tskey-auth-[A-Za-z0-9_-]+/[REDACTED]/g'
/opt/redeti-appliance/bin/tailscale --socket=/run/redeti/tailscaled.sock status --json | jq '{BackendState, Self: {HostName, TailscaleIPs, Tags}}'
/opt/redeti-appliance/bin/tailscale --socket=/run/redeti/tailscaled.sock ip -4
redeti-status
```

Esses comandos não criam, revogam ou alteram credenciais. O resultado sanitizado do `journalctl` deve permitir separar `expired/revoked` de `tag/ACL`.

## Resultado

`BLOCKED_PHYSICAL_EVIDENCE_REQUIRED`

A causa comprovada é rejeição durante autenticação Tailscale pela rota Ventoy, com modo gerenciado habilitado. A subcausa específica entre expiração/revogação e tag/ACL ainda depende do log sanitizado do daemon e/ou confirmação administrativa read-only da tailnet.
