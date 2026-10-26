# Hermes Broker — Homologação fechada (sem emissão Tailscale)

**Estado em 26/10/2026:** código disponível para teste; não instalado em
`systemd`, não exposto por Cloudflare, não integrado ao Service Desk.
Não instalar em produção nem habilitar a unidade até aceite explícito de
infraestrutura, RBAC e Service Desk.

## O que o modo fechado demonstra

`closed_service.py` reúne as interfaces do Hermes existentes, mas mantém
a emissão **bloqueada no runtime e também no emissor**:

- Agente: `127.0.0.1:39081` (no serviço de staging); HTTP SEM TLS, portanto
  **não** deve receber clientes remotos nem ser publicado por proxy/tunnel.
- Aprovação: socket UNIX `/run/redeti-recovery/approval.sock`, dentro
  de diretório privado pertencente ao usuário do serviço e modo `0700`;
  o arquivo de socket tem modo `0600`.
- MAC de aprovação: chave aleatória gerada na RAM **em cada inicialização**;
  não está integrada ao Service Desk e não tem persistência.
- Emissão: `enable_key_issuance=False`, emissor local deliberadamente
  incapaz de gerar qualquer auth key. Nem o Client ID nem o Client Secret
  Tailscale são lidos e não existe autenticação Tailscale neste estágio.
- Memória: as sessões são efêmeras; restart as invalida. Não escreve no
  disco de cliente e não altera a ISO.

## Teste local seguro (SEM instalação do serviço)

No checkout atualizado/revisado do GitHub, em Hermes:

```bash
cd ~/RecoveryOS/SO_SYSTEM_RECOVERY
git status --short
git pull --ff-only origin main
python3 -m services.recovery_enrollment.closed_service --self-test
python3 -m services.recovery_enrollment.smoke_local
```

Não faça `git pull` com mudanças locais desconhecidas: apenas reporte o
estado. A primeira linha deve mostrar `PASS: closed_mode_no_key_issuance`,
a segunda `PASS: local_enrollment_integration (emissor simulado; sem tokens reais)`.
O primeiro **prova bloqueio**; o segundo prova o fluxo com *fake issuer*.

## Unidade systemd: somente artefato de revisão

Arquivo:
`services/recovery_enrollment/systemd/redeti-recovery-closed.service`.

Foi projetado para um checkout revisado e instalado em
`/opt/redeti-recovery`, que **não** é o repositório em `~/RecoveryOS`.
A unidade NÃO possui seção `[Install]`, portanto não pode ser habilitada
diretamente por `systemctl enable`. Recursos previstos:

- `DynamicUser=yes`, `RuntimeDirectory` privado e `UMask=0077`;
- `ProtectSystem=strict`, `ProtectHome=yes`, sem capacidades;
- `IPAddressDeny=any` + `IPAddressAllow=localhost`;
- aceita apenas `AF_UNIX` e `AF_INET`;
- comando fixo `--serve-closed`, sem `--enable` ou segredos.

**Não copie/instale/inicie a unidade agora**: a montagem do pacote,
a política de contas, acesso do Service Desk ao socket, isolamento do
host Hermes, auditoria e aceitação do proprietário ainda estão pendentes.
A implantação precisa de plano de rollback com `systemctl stop`,
remoção da unidade revisada e inspeção de portas/ownership.

## Gates antes do modo real

1. Issue #45 do ProjVsCode liberar a posse e iniciar uma nova issue
   vinculada de autenticação no limite WIP; nenhum arquivo do Service Desk
   foi modificado nesta entrega.
2. Service Desk NestJS reconhecer sessão HTTP real, validar usuário ativo,
   perfil e **permissão explícita** `RECOVERY_VPN_APPROVE`, autorizar a
   O.S. solicitada, proteger CSRF/MFA, gerar nonce e assinar no **backend**.
3. Canal privado de chamada ao Hermes, com proprietário/grupo/montagem do
   socket restritos; não encaminhar a rota de operador em proxy público.
4. Secret manager, rotação de MAC e OAuth com proteção de memória, e trilha
   de auditoria sem tokens. Testar recuperação após restart.
5. Ingress HTTPS com autenticação do agente e limites por IP real, revisão
   da privacidade dos logs e teste de múltiplos equipamentos/boot.
6. Confirmar revogação da auth key Tailscale (falha HTTP anterior de
   revogação permanece sem causa determinada); não repetir smoke de emissão
   só para revalidar enquanto não houver plano.
7. Corrigir timeout de banner SSH pela VPN. Banner visual nativo separado
   já foi empacotado para ISO futura, mas não corrige o timeout.

**Nenhum PASS de CI ou do teste fechado equivale a deploy/homologação
de campo.**
