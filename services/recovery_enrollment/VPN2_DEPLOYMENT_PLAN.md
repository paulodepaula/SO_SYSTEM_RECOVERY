# RedeTI Recovery OS — VPN-2: plano de implantação controlada

Status: PREPARADO, NÃO ATIVADO.

Este documento descreve a preparação do Enrollment Broker no Hermes. Nenhum
serviço foi instalado/habilitado, nenhuma porta foi aberta, nenhum firewall,
Cloudflare ou Tailscale foi alterado e nenhuma auth key real foi emitida.

## Inventário observado antes da preparação

- O host possui listeners existentes em 80/81/443, 22, 8644, 8790/8791,
  3101/3102/3103, 4000, 5678, 8080 e outras portas de aplicações.
- Docker possui stacks RedeTI dev/UAT, Forgejo, observabilidade, GLPI,
  Nginx Proxy Manager, n8n e outros serviços ativos.
- Não existe unidade instalada/enabled do Enrollment Broker.
- `/etc/redeti-recovery` existe como diretório `0700 root:root`; a inspeção de
  metadados não encontrou arquivos de credencial. Conteúdo de credenciais não
  foi lido.
- O broker fechado permanece somente no checkout; não há endpoint público.

## Componentes preparados

- `systemd/redeti-recovery-broker-staging.service`: unidade explícita de
  staging, com usuário/grupo dedicado, `DynamicUser=no`, runtime privado,
  `UMask=0077`, `ProtectSystem=strict`, `ProtectHome=yes`, sem capabilities,
  `PrivateDevices=yes`, `NoNewPrivileges=yes`, `IPAddressDeny=any` e somente
  `localhost` permitido. Executa `closed_service` com emissão desabilitada.
- `openapi.yaml`: contrato HTTPS de bootstrap/status/claim e separação da rota
  administrativa. Continua sendo contrato, não endpoint publicado.
- `SERVICE_DESK_APPROVAL_CONTRACT.md`: contrato da afirmação assinada,
  permissão `RECOVERY_VPN_APPROVE`, nonce, O.S. e socket AF_UNIX.
- `CLOSED_HERMES_RUNBOOK.md`: ativação fechada, rollback e gates para produção.
- `check_oauth.py`: verificação read-only de permissões e escopo OAuth; não cria
  chaves e não imprime tokens.

## HTTPS preparado, não publicado

- O broker deve escutar somente loopback no Hermes.
- A publicação externa, se autorizada, deverá usar hostname dedicado, TLS
  válido, proxy autenticado e upstream loopback explicitamente allowlisted.
- Não reutilizar cegamente as portas 80/443 existentes; elas já possuem
  serviços ativos.
- A rota `/v1/operator` nunca deve ser publicada pelo proxy HTTPS.
- Exigir rate limit por origem/global, limites de corpo, `no-store`, timeout,
  WAF/controle equivalente e logs sem corpos ou segredos.

## Service Desk preparado, não habilitado

Antes da aprovação real, o Service Desk deve fornecer:

1. Sessão autenticada e MFA.
2. RBAC com `RECOVERY_VPN_APPROVE`.
3. Técnico ativo e autorizado à O.S.
4. Confirmação do código físico de pareamento.
5. CSRF, nonce e expiração curta.
6. Assinatura HMAC no backend, nunca no navegador.
7. Comunicação apenas pelo socket privado autorizado.
8. Auditoria sem segredo, token, código completo ou conteúdo de payload sensível.

## OAuth preparado, não validado em produção

Pré-requisitos para ativação:

- OAuth client criado no Hermes com escopo mínimo `auth_keys`.
- Restrição à tag `tag:redeti-recovery`.
- Secret manager protegido; nunca Git, ISO, Ventoy, `.env` versionado,
  argumentos, logs ou relatórios.
- Diretório de credenciais `0700 root:root`.
- Arquivos `0600 root:root`, regulares, não symlinks e tamanho limitado.
- Primeiro teste: somente troca de token e verificação de escopo.
- Emissão real somente em janela aprovada e após o teste simulado.
- Revogação deve ser confirmada; resultado incerto bloqueia nova emissão.

## Ativação futura — requer autorização explícita

1. Aprovar issue/janela e o commit exato.
2. Criar usuário/grupo dedicado `redeti-recovery`.
3. Instalar checkout revisado em `/opt/redeti-recovery`.
4. Criar `/etc/redeti-recovery` com ownership/modos exigidos.
5. Instalar a unidade em `/etc/systemd/system`.
6. Executar `systemd-analyze verify`.
7. Fazer `daemon-reload` somente na janela autorizada.
8. Iniciar em modo fechado, sem emissão, e validar socket/listeners.
9. Integrar Service Desk e HTTPS somente após os gates anteriores.
10. Habilitar emissão real apenas por alteração explícita revisada.

## Rollback futuro — requer autorização de mudança

1. Bloquear novas sessões no ingress.
2. Parar o serviço dedicado.
3. Confirmar ausência de listeners e socket residual.
4. Remover/arquivar somente a unidade e configuração do broker.
5. Remover credenciais do runtime conforme procedimento do secret manager.
6. Restaurar proxy/Service Desk para o snapshot anterior.
7. Confirmar que serviços Docker, Hermes, firewall, Cloudflare e Tailscale
   permanecem com os IDs/configuração anteriores.
8. Auditar sessões pendentes e revogar qualquer credencial criada na janela.

Nenhum passo de ativação ou rollback foi executado nesta preparação.
