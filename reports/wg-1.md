# RedeTI — Relatório WG-1: estudo de implantação WireGuard

- Etapa: `WG-1 — viabilidade e planejamento`
- Gerado em UTC: `2026-10-28T21:24:00Z`
- Projeto: `SO_SYSTEM_RECOVERY`
- Escopo: análise somente leitura; nenhuma alteração executada
- Estado: `BLOCKED_INVENTORY_TLS`

## Resumo executivo

A implantação é tecnicamente viável se o MikroTik alvo estiver em RouterOS 7.x e tiver capacidade de manter uma interface WireGuard e dois peers: Hermes e Recovery OS.

A coleta real do equipamento não foi concluída. O perfil read-only `cidade-verde`, associado ao MikroTik com IP público fixo do cliente, falhou antes da autenticação RouterOS com:

`SSLV3_ALERT_HANDSHAKE_FAILURE`

Por isso, modelo, versão efetiva, interfaces, rotas, firewall, NAT e conflitos de endereçamento permanecem `NOT_OBSERVED`. Não serão tratados como fatos os metadados antigos do cofre.

## Inventário e acesso

Perfil consultado: `cidade-verde`.

Metadados não secretos disponíveis no cofre:

- tipo: MikroTik;
- RouterOS declarado: v7;
- API-SSL declarada: porta 8729;
- certificado configurado no perfil: `rest-api`;
- grupo declarado no perfil: `full`, embora o adaptador MCP exponha somente operações read-only.

Resultado da tentativa read-only:

- identidade: `NOT_OBSERVED`;
- modelo/board: `NOT_OBSERVED`;
- versão efetiva: `NOT_OBSERVED`;
- interfaces: `NOT_OBSERVED`;
- endereços: `NOT_OBSERVED`;
- rotas: `NOT_OBSERVED`;
- firewall: `NOT_OBSERVED`;
- NAT: `NOT_OBSERVED`;
- logs: `NOT_OBSERVED`.

O MCP confirmou que os paths read-only disponíveis incluem `/interface`, `/ip/address`, `/ip/route`, `/ip/firewall/filter`, `/ip/firewall/nat`, `/system/identity`, `/system/resource` e `/system/routerboard`, mas todos os acessos ao alvo falharam no handshake TLS.

Nenhum comando administrativo ou de escrita foi executado.

## Compatibilidade WireGuard

RouterOS 7 possui suporte nativo a WireGuard. A compatibilidade do alvo é `CONDITIONAL` até confirmar a versão efetiva e os recursos do equipamento.

Pré-requisitos técnicos:

- RouterOS 7.x com `/interface/wireguard` disponível;
- CPU/memória suficientes para o túnel;
- UDP público encaminhado diretamente ao MikroTik;
- porta UDP dedicada e não usada por VPN existente;
- relógio/NTP funcional;
- capacidade de configurar peers sem tocar nas VPNs existentes;
- acesso administrativo alternativo para rollback.

Não foi consultada a existência atual de interfaces WireGuard nem a porta UDP disponível.

## Arquitetura proposta

Interface exclusiva:

`wg-redeti-recovery`

Topologia hub isolada no MikroTik:

```text
Hermes WireGuard peer  <---- WG ---->  MikroTik wg-redeti-recovery  <---- WG ---->  Recovery OS
                                       somente túnel privado
```

O MikroTik não deve ser usado como gateway do Recovery para a LAN do cliente. O túnel deve transportar apenas o fluxo Hermes ↔ Recovery OS.

Peers propostos:

- Hermes: endereço privado do túnel `10.255.254.2/32`;
- Recovery OS: endereço privado do túnel `10.255.254.3/32`;
- MikroTik: interface `10.255.254.1/29`;
- rede candidata: `10.255.254.0/29`.

A rede é apenas uma candidata. Ela só poderá ser escolhida após leitura real de `/ip/address`, `/ip/route` e inventário das VPNs existentes. Se houver conflito, selecionar outra sub-rede RFC1918 dedicada, sem alterar redes atuais.

Não devem ser criadas rotas para:

- LAN do cliente;
- redes de administração do MikroTik;
- outras VPNs;
- redes Docker/virtualização do Hermes.

## Política de acesso proposta

Permitido:

1. UDP da Internet para a porta WireGuard dedicada, com origem restrita ao Hermes quando o endereço de origem for estável.
2. Para Recovery atrás de NAT, aceitar o handshake UDP somente na porta dedicada, com rate-limit e sem expor outros serviços.
3. Forward Hermes `10.255.254.2/32` → Recovery `10.255.254.3/32` somente TCP/22, caso SSH seja o único serviço necessário.
4. Retorno do fluxo estabelecido/relacionado.

Bloqueado:

- input do `wg-redeti-recovery` para administração do MikroTik;
- Winbox, SSH, API, API-SSL, DNS, WebFig e SNMP pela nova interface;
- forward `wg-redeti-recovery` → LAN do cliente;
- forward `wg-redeti-recovery` → outras VPNs;
- forward Recovery → Hermes, exceto portas explicitamente necessárias;
- NAT/masquerade entre os peers do túnel;
- acesso do Recovery ao próprio MikroTik, salvo uma janela administrativa explicitamente aprovada, que não faz parte deste WG-1.

A ordem das regras deverá ser planejada após coletar o firewall atual. Não é seguro presumir posições ou comentários existentes.

## WireGuard e ciclo de vida de chaves

Não foram geradas chaves nesta fase.

Modelo recomendado:

- par exclusivo Hermes por sessão;
- par exclusivo Recovery por sessão, gerado em RAM no Recovery OS;
- chave pública do Recovery entregue ao operador/broker por canal autenticado;
- chave privada nunca na ISO, Ventoy, Git, relatório ou chat;
- peer criado no MikroTik somente durante a janela aprovada;
- `allowed-address` limitado ao `/32` do peer;
- `persistent-keepalive=25s` somente para o peer atrás de NAT, após confirmar a necessidade;
- remoção do peer e descarte das chaves no encerramento;
- rotação obrigatória por sessão ou incidente;
- nenhuma reutilização de chave entre clientes/equipamentos.

O MikroTik não deve receber uma chave privada. Ele armazena apenas a chave pública dos peers.

## Provisionamento temporário sem chave privada na ISO

Fluxo recomendado:

1. Recovery OS gera a chave privada WireGuard em tmpfs durante o boot.
2. A chave privada permanece somente em RAM com modo `0600`.
3. Recovery envia apenas a chave pública e um identificador de sessão por um Enrollment Broker HTTPS autenticado, ou exibe a chave pública na console local para inserção manual.
4. Operador aprova a sessão e instala o peer público no MikroTik.
5. Broker/operador entrega ao Recovery somente a configuração pública necessária e o endpoint UDP.
6. Recovery conecta ao MikroTik.
7. Hermes usa sua chave de sessão para alcançar apenas o endereço `/32` do Recovery.
8. Ao finalizar, remover o peer do MikroTik e destruir o material de sessão em ambos os lados.

Alternativa manual controlada: o operador pode entregar ao Recovery um arquivo temporário em mídia confiável contendo a configuração, mas a chave privada deve ser criada no próprio Recovery ou transferida somente por canal protegido e nunca ser incorporada à ISO.

Não usar chave permanente embutida na imagem.

## Comandos RouterOS propostos — não executar nesta fase

Os comandos abaixo são somente um rascunho parametrizado. Não contêm chaves reais, não definem porta final e não devem ser colados antes da coleta de inventário e aprovação da janela.

```routeros
# NÃO EXECUTAR — WG-1 apenas
# Substituir <UDP_PORT>, <HERMES_PUBLIC_KEY>, <RECOVERY_PUBLIC_KEY>
# e <HERMES_PUBLIC_IP> somente após revisão.

/interface wireguard add \
    name=wg-redeti-recovery \
    listen-port=<UDP_PORT> \
    mtu=1420 \
    comment="REDETI Recovery temporary isolated VPN"

/ip address add \
    address=10.255.254.1/29 \
    interface=wg-redeti-recovery \
    comment="REDETI Recovery temporary tunnel"

/interface wireguard peers add \
    interface=wg-redeti-recovery \
    public-key="<HERMES_PUBLIC_KEY>" \
    allowed-address=10.255.254.2/32 \
    comment="REDETI Hermes session peer"

/interface wireguard peers add \
    interface=wg-redeti-recovery \
    public-key="<RECOVERY_PUBLIC_KEY>" \
    allowed-address=10.255.254.3/32 \
    persistent-keepalive=25s \
    comment="REDETI Recovery session peer"

# WAN handshake: restringir a Hermes se Recovery não estiver atrás de NAT.
/ip firewall filter add chain=input action=accept \
    protocol=udp dst-port=<UDP_PORT> \
    src-address=<HERMES_PUBLIC_IP>/32 \
    comment="REDETI WG handshake Hermes only"

# Para Recovery atrás de NAT, usar regra UDP dedicada com rate-limit
# somente após revisão do firewall e do modelo de exposição.

# Nunca permitir administração do MikroTik pela interface WG.
/ip firewall filter add chain=input action=drop \
    in-interface=wg-redeti-recovery \
    comment="REDETI WG block MikroTik administration"

# Permitir somente Hermes -> Recovery TCP/22.
/ip firewall filter add chain=forward action=accept \
    in-interface=wg-redeti-recovery \
    src-address=10.255.254.2/32 \
    dst-address=10.255.254.3/32 \
    protocol=tcp dst-port=22 \
    comment="REDETI WG Hermes to Recovery SSH"

/ip firewall filter add chain=forward action=accept \
    connection-state=established,related \
    src-address=10.255.254.3/32 \
    dst-address=10.255.254.2/32 \
    comment="REDETI WG Recovery return traffic"

# Bloqueio explícito contra LAN e demais destinos.
/ip firewall filter add chain=forward action=drop \
    in-interface=wg-redeti-recovery \
    comment="REDETI WG block client LAN and other networks"
```

Observações sobre o rascunho:

- A posição das regras precisa ser calculada a partir do firewall real.
- A regra de handshake para Recovery atrás de NAT não pode depender de um IP público fixo do Recovery.
- O filtro final não deve ser inserido antes de regras `established,related` existentes sem revisão.
- Não adicionar NAT para o tráfego entre peers.
- Não anunciar rotas LAN.
- Não alterar VPNs atuais.

## Plano seguro de implantação futura

### Gate 0 — pré-requisitos

- Resolver o handshake TLS/API-SSL do perfil `cidade-verde`.
- Confirmar identidade, modelo, RouterOS efetivo e acesso read-only.
- Coletar interfaces, endereços, rotas, firewall, NAT, logs e VPNs atuais.
- Confirmar que a porta UDP escolhida está livre.
- Escolher uma sub-rede sem conflito.
- Confirmar operador, janela e canal de rollback.

### Gate 1 — backup e baseline

Antes de qualquer escrita, obter backup binário e export sanitizado por canal autorizado. O backup deve permanecer protegido; o export para auditoria deve remover chaves, PSKs, senhas, tokens e segredos.

Registrar contadores e posição das regras sem alterar nada.

### Gate 2 — staging isolado

- Criar interface e IP privados.
- Adicionar peers com chaves de sessão.
- Adicionar somente regras novas, comentadas e desabilitadas quando possível.
- Não alterar interface WAN, VPN existente, rota LAN ou NAT existente.
- Fazer leitura posterior de cada objeto.

### Gate 3 — teste funcional controlado

- Confirmar handshake WireGuard recente.
- Confirmar RX/TX em duas amostras.
- Testar Hermes → Recovery no único serviço permitido.
- Testar que Hermes não acessa RouterOS pela WG.
- Testar que Recovery não alcança a LAN do cliente.
- Testar que outras portas são bloqueadas.
- Verificar que VPNs existentes permanecem inalteradas.

### Gate 4 — encerramento

- Remover peers temporários.
- Remover endereço/interface temporários, se a sessão terminou.
- Revalidar firewall, NAT, rotas e VPNs existentes.
- Confirmar que não restaram chaves de sessão.
- Registrar evidência sanitizada.

## Rollback

Se qualquer teste falhar:

1. Parar novos testes.
2. Desabilitar/remover somente os objetos criados para `wg-redeti-recovery`, na ordem documentada.
3. Restaurar o snapshot/export aprovado se houver divergência.
4. Revalidar rotas, firewall, NAT, interfaces e VPNs preexistentes.
5. Confirmar conectividade do cliente.
6. Registrar o rollback sem segredos.

O rollback não deve reiniciar o equipamento nem tocar nas VPNs preexistentes salvo se o backup demonstrar uma alteração acidental.

## Riscos e bloqueios

- Handshake TLS do API-SSL atualmente impede inventário real.
- Perfil do cofre está marcado como `full`; é necessário confirmar que a execução continua limitada a leitura e preferir credencial RouterOS `read` dedicada.
- Modelo e capacidade do MikroTik não confirmados.
- Porta UDP não confirmada.
- Conflito de sub-rede não verificado.
- Firewall/NAT atuais não conhecidos.
- Política de origem da tailnet Hermes não conhecida.
- Possível exposição UDP se Recovery estiver atrás de NAT.
- Tailscale/WireGuard existentes podem usar endereços ou portas conflitantes.
- Chaves por sessão exigem fluxo operacional de criação, entrega, remoção e auditoria.

## Resultado

`VIABLE_WITH_PREREQUISITES`

A arquitetura WireGuard isolada é viável em princípio para RouterOS 7, mas a implantação está bloqueada até resolver o acesso read-only TLS e concluir o inventário real. Nenhum comando RouterOS foi executado, nenhuma chave foi gerada e nenhum equipamento, VPN, firewall, NAT ou rota foi alterado.
