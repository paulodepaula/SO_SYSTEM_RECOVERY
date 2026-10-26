# RedeTI Recovery OS — provisionamento VPN de campo sem intervenção no Tailscale

**Status:** arquitetura proposta, sem implementação ou homologação.
**Contexto:** SystemRescue invisível, LVGL 9.6 / DRM / EVDEV, Ventoy, diagnóstico
somente leitura, SSH LAN com chave Ed25519; Tailscale temporário em RAM.
**Objetivo:** em qualquer computador de cliente, o técnico liga o pendrive e
conecta o equipamento remoto à tailnet sem abrir o painel administrativo do
Tailscale, copiar tokens, editar arquivos ou gravar discos de clientes.

## Decisão arquitetural

Separar as funções em **Recovery Agent** (na ISO) e **Enrollment Broker**
(central Hermes). O broker consulta a API oficial do Tailscale; o Recovery
Agent nunca recebe a credencial OAuth administrativa. A partir de uma
solicitação aprovada por técnico autenticado, o broker emite uma chave
Tailscale **single-use, ephemeral, tag: redeti-recovery, TTL mínimo
praticável** para a sessão. O dispositivo a usa uma única vez e mantém
`tailscaled --state=mem:`, sem gravar identidade em disco.

A UI do Recovery OS continua **nativa**, sem XFCE, Firefox, X11 ou webapp. O
painel de aprovação pertence à **infraestrutura RedeTI** (Hermes/Service Desk),
não à ISO. O técnico pode usá-lo em celular ou Windows. Na primeira versão,
a aprovação é explícita, uma ação por sessão; nenhuma intervenção no painel
administrativo Tailscale durante o trabalho de campo.

**Não existe autenticação segura e completamente autônoma para um computador
arbitrário sem qualquer identidade pré-confiável.** Não emitir tokens com base
somente em um IP, hostname ou UUID autodeterminado. Para zero interação humana
seria necessária uma credencial de hardware protegida e provisionada antes do
atendimento (por exemplo, identidade do pendrive em um dispositivo seguro),
com política própria; isso não integra o primeiro MVP.

## Fluxo de uso no campo

1. Técnico inicia Ventoy > RedeTI Recovery OS; o dashboard mostra estado
   LAN, horário confiável, conectividade HTTPS e estado de provisionamento.
2. Agent gera em RAM par de chaves efêmeras para autenticar a sessão de
   bootstrap, identificador aleatório e código de pareamento de curta duração
   ou QR. Não reutiliza uma identidade em outro cliente.
3. Agent abre exclusivamente conexão **HTTPS de saída** com o endpoint de
   bootstrap da RedeTI e registra pedido pendente, sem upload de serial de
   disco, dados pessoais, arquivos ou diagnóstico de clientes.
4. Técnico autenticado no Service Desk/portal da RedeTI vê código, endpoint
   de sessão, tempo para expirar e confirma que o código corresponde ao
   mostrado fisicamente no equipamento. Autoriza uma vez.
5. Broker aplica limites de frequência, permissões do técnico, vínculo com
   atendimento e estado da sessão; cria via API oficial Tailscale uma única
   auth key com tag autorizada, uso único, ephemeral, expiry curta.
6. Broker entrega credencial apenas ao Agent que prove posse da chave efêmera
   que iniciou o pedido, com HTTPS de validação estrita e resposta vinculada
   à sessão. O conteúdo secreto jamais aparece na UI, navegador, URL, log,
   push, Git, Service Desk ou observabilidade.
7. Agent inicia Tailscale com SSH gerenciado **somente após o controle SSH e
   firewall ser homologado**. Até lá, usar somente OpenSSH Ed25519 na tailnet,
   sem fingir que login remoto está concluído.
8. Agent mostra IP privado `100.x.y.z`, modo SSH, resultado da conexão,
   tempo desde última autorização; Hermes registra sessão e oferece ao
   técnico atalho para conectar a partir da sua tailnet.
9. Encerrar sessão: desconectar Tailscale, limpar estado em RAM, invalidar
   solicitações ainda pendentes e, quando permitido por escopo separado,
   remover o nó efêmero do tailnet. Expirar automaticamente caso técnico não
   autorize ou abandone a sessão.

## Responsabilidades e superfícies de ataque

### Broker no Hermes (componente novo)

- Armazenar credenciais OAuth Tailscale **somente em gerenciador de segredos
  local/serviço protegido**, não em repositório, docker image, ISO, build args,
  arquivos estáticos, stdout, commits ou pendrive.
- Criar cliente OAuth restrito ao escopo de **criação de auth keys** (conforme
  nomenclatura atual da API) e à **tag: `tag:redeti-recovery`**. Não usar
  escopo administrativo universal. Se remoção de dispositivos for necessária,
  isolar essa capacidade em credencial/serviço distinto.
- Trocar OAuth client credentials por access token de curta duração no
  servidor e invocar `POST /api/v2/tailnet/:tailnet/keys`, conforme
  documentação Tailscale. Nenhum segredo OAuth alcança o dispositivo.
- Criar contas/roles de técnico, autenticação forte (preferencialmente MFA),
  vínculo de OS, rate limit por origem e técnico, timeouts e trilha de auditoria.
- Proteger portal técnico com login existente e preferencialmente Cloudflare
  Access; endpoint de bootstrap para máquinas externas é **separado** e
  estritamente limitado, sem endpoint que emita token sem aprovação.
- Tokens: só em memória, curta duração, sem retries de emissão não
  idempotentes, entrega única ao Agent autorizado. Usar cache de idempotência
  para evitar criação duplicada.
- Alertas de uso excessivo, chaves não consumidas, tentativas de pareamento,
  sessão expirada e indisponibilidade do broker.
- Política de autorização e ACL no Tailscale **não** são reescritas por sessão:
  configurar uma vez e auditar periodicamente.

### Agent na ISO

- Apenas HTTPS de saída ao broker da RedeTI e rede Tailscale após pareamento.
- Certificado TLS validado e relógio confiável. Jamais usar verificação TLS
  desabilitada, identidade SSH não verificada ou token permanente na ISO.
- Gerar prova de posse da sessão em RAM; não expor segredo em parâmetros de
  processos, imagens do dashboard, exceções, relatórios ou arquivos.
- Tempo máximo para pareamento; caso Hermes esteja indisponível:
  **diagnóstico local e SSH LAN continuam funcionando**, sem modo inseguro.
- Garantir nenhuma gravação em discos de cliente (nem cache de Tailscale).
- Checar software Tailscale, interfaces e política do firewall antes de marcar
  VPN como pronta; `connected` não equivale a SSH autenticado.

## Mensagens do dashboard

- Sem internet / TLS indisponível
- Aguardando autorização do técnico: código + validade (nunca token)
- Autorização recusada/expirada
- VPN conectando / conectada
- IP tailnet + SSH (gerenciado ACL / Ed25519)
- Falha SSH (banner / ACL / chave / rota) **diferente** de falha VPN
- Botão "Cancelar sessão" e indicação de que todo o tráfego remoto é
  uma conexão privada; nenhuma porta pública de cliente é aberta

## Controles Tailscale

- `tag:redeti-recovery`, somente técnicos autorizados -> TCP/22;
  nenhuma permissão de saída para outras máquinas; sem `* -> *`.
- SSH gerenciado: origem técnicos, destino tag, login `paulo`, `check`
  padrão (12h no plano Free), sem root, sem outros usuários.
- Não tornar o Recovery exit node ou subnet router, nem habilitar
  Funnel/Serve de forma pública.
- Verificar também regras locais iptables/nftables e a porta 22. A falha
  já observada `Connection timed out during banner exchange` com TCP
  estabelecido deve ser solucionada separadamente antes do lançamento.

## Não fazer

- Não colocar auth key Tailscale **reutilizável** no Ventoy. Mesmo uma chave
  reusable+ephemeral é um segredo portátil que dá entrada à tailnet.
- Não colocar OAuth client secret nem API token administrativo no pendrive,
  GitHub Actions, ISO, QR ou no dispositivo temporário.
- Não liberar acesso automático com base em um código informado apenas pelo
  Agent, sem operador autenticado ou identidade de hardware confiável.
- Não usar `StrictHostKeyChecking=no`, SSH root, senha de usuário,
  `iptables -F INPUT` ou porta pública no roteador do cliente.
- Não chamar VNC de implementado: ainda depende de captura LVGL, entrada
  remota autorizada e tunelamento seguro.

## Plano incremental

**Fase A: contratos e testes (sem ISO)** — OpenAPI versionado do broker,
estados de pareamento, teste de expiração, rate limit e negação de acesso,
modelo de auditoria sem dados de clientes. Mock da API Tailscale.
**Fase B: broker Hermes** — serviço backend isolado com OAuth mínimo,
validação de operador/OS e emissão de chave efêmera depois do aceite.
Testar sem token real em CI e com token real somente em ambiente controlado.
**Fase C: agent + LVGL** — registro HTTPS, código QR, polling de autorização,
entrega segura, expiração e fallback LAN sem quebrar o boot.
**Fase D: SSH e firewall** — investigar e corrigir timeout do banner SSH
na tailnet. Testes TCP, banner, autorização, negação e redes externas.
**Fase E: ISO / piloto** — compilar Hermes, checksum, QEMU sem discos de
clientes, hardware descartável, hotspot externo, simular Hermes offline,
revogar usuário, 3 computadores com mesma ISO e sem reconfiguração manual.

## Critérios de aceite de produção

1. 3 computadores distintos e 2 reinicializações em cada um: nenhum
   token Tailscale digitado ou salvo no Ventoy; nenhuma alteração manual
   no painel Tailscale depois da configuração inicial do broker.
2. Técnico autoriza no portal; tempos e erros são exibidos e auditados;
   outra pessoa não consegue aprovar sessão, nem sequestrar seu código.
3. Nenhuma credencial permanente fora do Hermes; tokens não aparecem em
   logs, traces, crash reports, QR, ISO, GitHub ou UI.
4. Acesso SSH funcional pela LAN e por outra conexão de internet usando
   a tailnet, com identidade do host verificada e sem root.
5. Offline/sem Hermes ou sem Tailscale: Recovery OS inicia normalmente,
   mantém diagnóstico somente leitura e SSH local quando autorizado.
6. VPN limitada a TCP/22 da origem autorizada; sem serviço público, sem
   escrita em disco de cliente e sem acesso de saída à rede da RedeTI.
7. No encerramento, estado e segredos em RAM são descartados e dispositivos
   efêmeros expiram; operador consegue revogar um atendimento.
8. Build identificável no dashboard por versão + tag + SHA do commit;
   homologação documentada separada do estado de implementação.

## Fontes oficiais (consulta outubro de 2026)

- https://tailscale.com/docs/features/oauth-clients
- https://tailscale.com/docs/reference/trust-credentials
- https://tailscale.com/docs/features/access-control/auth-keys
- https://tailscale.com/docs/features/ephemeral-nodes
- https://tailscale.com/docs/features/tailscale-ssh
- https://tailscale.com/docs/reference/tailscale-api
