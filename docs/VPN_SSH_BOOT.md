# RedeTI Recovery OS — Acesso remoto SSH por VPN

**Status:** proposta de arquitetura para v0.5; ainda nao implementada na ISO alpha.

## Objetivo operacional

1. O tecnico seleciona `RedeTI-Recovery-OS.iso` no Ventoy.
2. O Linux inicia, abre automaticamente a central grafica e tenta obter acesso de rede por Ethernet/DHCP.
3. O agente VPN inicia automaticamente. O painel apresenta o estado `Sem rede`, `Aguardando autorizacao`, `Conectado` ou `Falha`.
4. A maquina recebe uma identidade temporaria, criada para esta sessao. O acesso SSH so e habilitado depois de uma autorizacao valida.
5. Tecnico autorizado conecta-se pelo Tailscale SSH, exclusivamente pela rede VPN.
6. Ao desligar o ambiente Live, a identidade de sessao e descartada; qualquer acesso remoto termina.

## Tecnologia recomendada

Tailscale sobre WireGuard, com Tailscale SSH e politica de acesso restritiva. Alternativa futura: WireGuard com um gateway de provisionamento privado da RedeTI.

Referencias oficiais:
- https://tailscale.com/docs/features/ephemeral-nodes
- https://tailscale.com/docs/features/tailscale-ssh
- https://tailscale.com/docs/features/access-control/auth-keys
- https://tailscale.com/docs/install/linux

## Requisitos obrigatorios de seguranca

- NUNCA incluir auth keys, OAuth secrets, senhas ou chaves WireGuard permanentes em Git, GitHub Actions logs ou ISO distribuida.
- Registro sem intervencao so e viavel quando existe um fluxo de provisionamento autorizado com credencial efemera, entregue separadamente da ISO. Sem credencial, iniciar agente VPN mas ficar em `Aguardando autorizacao`.
- Usar tags separadas (`tag:redeti-recovery`) e controle de acesso com politica default-deny. Limitar origem a tecnicos autorizados e destino ao SSH desta maquina, sem acesso indiscriminado a outras redes.
- Exigir reautenticacao/checagem de identidade para SSH de privilegio elevado, quando suportado pelas regras de Tailscale SSH.
- Nao anunciar rotas ou configurar exit node. Desabilitar conexao por SSH fora da VPN; nenhum encaminhamento de porta no roteador.
- IP e nome do no podem mudar a cada boot, pois o dispositivo deve ser efemero. Mostrar o identificador da sessao, conectividade e nome na interface local.
- Nao assumir que o computador do cliente tem conectividade, DHCP, DNS ou drivers de rede disponiveis. Se offline, a interface de diagnostico deve continuar funcionando.
- Separar acesso remoto de permissao para reparos: conectar por SSH nao autoriza escrita. Nesta fase, reparos continuam bloqueados.
- Registrar data/hora, tecnico autorizado, inicio e encerramento de sessao; nao enviar dados de clientes sem consentimento e necessidade operacional.
- Certificar-se de consentimento do responsavel pelo computador e desabilitar o agente quando o atendimento for encerrado.
- Evitar SSH root irrestrito. Preferir identidade de manutencao com comandos permitidos e autorizacao local para acoes sensiveis.

## Planos de provisionamento

### Piloto de laboratorio

Parear manualmente o dispositivo em Tailscale com autorizacao do operador, sem credencial embutida na ISO. Pode-se iniciar com login interativo e verificar ACL antes de testar SSH. Modo efemero em memoria (`tailscaled --state=mem:`), se suportado pelo pacote utilizado.

### Operacao de campo

Usar servidor de provisionamento autenticado que emite credencial temporaria e restrita por sessao apos aprovacao (ou um fluxo de login/pareamento verificado). Sem emissao segura, nao prometer VPN totalmente automatica. Nunca embutir token reutilizavel em pendrive ou ISO compartilhada.

## Proposta de interface no cabecalho

`Rede: Ethernet conectada | VPN: Aguardando autorizacao | SSH: Bloqueado`

Depois da autorizacao:

`Rede: Conectada | VPN: Conectada | Identidade: recovery-<sessao> | SSH: Permitido para equipe autorizada`

O status deve vir do agente real, nunca de estado demonstrativo ou de um valor ficticio.

## Criterios de homologacao

- Boot no QEMU/VM com rede isolada sem credenciais: agente pronto, SSH inacessivel.
- Rede indisponivel: UI abre normalmente e exibe VPN offline.
- Pareamento autorizado em VM: acesso SSH apenas do operador permitido pela ACL.
- Operador nao autorizado: acesso bloqueado.
- Reinicio: identidade temporaria anterior invalida.
- Desligamento: tunel encerrado e sessao revogada ou expirada.
- Nenhuma dependencia de disco de cliente para instalacao, persistencia de tokens ou logs.
- A configuracao de rede nao altera o disco interno em nenhuma circunstancia.

**Observacao:** a primeira ISO gerada (alpha v0.4) nao implementa VPN/SSH. Uma nova ISO so devera ser liberada apos compilacao, validacao de interface e testes de seguranca.
