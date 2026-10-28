# RedeTI — Relatório WG-5: segurança e preparação do WireGuard

- Etapa: `WG-5 — segurança administrativa e preparação WireGuard`
- Gerado em UTC: `2026-10-28T22:48:00Z`
- Projeto: `SO_SYSTEM_RECOVERY`
- Alvo: MikroTik Cidade Verde — `RB3011UiAS`, RouterOS `7.20.8`
- Estado: `READY_FOR_SEPARATE_AUTHORIZED_STAGING`
- Alterações executadas: `NONE`

## Dados confirmados pelo operador

- WAN: `PPPOE-CONECT`.
- WireGuard existente: `wg-escritorio`, UDP `13231`.
- API-SSL: TCP `8729`, `certificate=none`.
- WinBox: TCP `8899` habilitado.
- Saída IPv4 apresentada: sem regra drop explícita no final observado.
- Redes existentes: `192.168.0.0/24`, `192.168.38.0/24`, `192.168.200.0/24`, `10.210.210.0/30`, `10.1.5.0/24` e VPN L2TP.
- Candidata WG Recovery: `10.255.254.0/29`.

A sub-rede candidata não coincide com as redes informadas, mas ainda precisa ser comparada com rotas, pools, redes IPv6, address-lists, túneis e objetos não apresentados.

## Limitações da coleta atual

O MCP `cidade-verde` continua falhando antes do login com `SSLV3_ALERT_HANDSHAKE_FAILURE`. Portanto, permanecem `NOT_OBSERVED`:

- regras IPv6;
- interface lists e seus membros;
- firewall raw;
- firewall mangle;
- NAT completo e ordem das regras;
- rotas IPv4/IPv6 completas;
- address-lists;
- origem atual de WinBox/API-SSL;
- mecanismos adicionais de proteção ou exposição;
- estado/peers completos das VPNs.

Não vou declarar que o firewall está seguro apenas porque a saída IPv4 não mostrou um drop explícito.

## Consultas read-only obrigatórias antes da aplicação

Executar em sessão RouterOS autorizada e retornar somente dados sanitizados:

```routeros
/system identity print
/system resource print
/system routerboard print

/interface print detail
/interface list print detail
/interface list member print detail

/ip service print detail
/ip address print detail
/ip route print detail
/ip firewall filter print detail stats
/ip firewall nat print detail stats
/ip firewall raw print detail stats
/ip firewall mangle print detail stats
/ip firewall address-list print detail

/ipv6 address print detail
/ipv6 route print detail
/ipv6 firewall filter print detail stats
/ipv6 firewall raw print detail stats
/ipv6 firewall mangle print detail stats

/interface wireguard print detail
/interface wireguard peers print detail
/interface l2tp-server server print detail
/ppp active print detail
/log print where message~"winbox|api|wireguard|l2tp|firewall|drop"
```

Sanitizar chaves públicas quando necessário, mas preservar:

- nomes das interfaces;
- portas;
- estados;
- prefixos e rotas;
- comentários;
- contadores;
- origem/destino das regras;
- `last-handshake`, RX/TX e endpoint sem material privado.

## Identificação do acesso administrativo atual

Não foi possível concluir a origem atual do operador. Antes de restringir 8729/8899, confirmar:

- origem real do WinBox atual;
- origem real do MCP/API-SSL;
- redes administrativas locais autorizadas;
- eventual acesso por VPN existente;
- endereço público do Hermes, se houver;
- rota de retorno dessas origens;
- canal alternativo de administração local/console.

Não usar a suposição de que o IP público do MikroTik é a origem do Hermes.

## Proteção proposta para API-SSL e WinBox

A primeira camada deve ser o campo `address=` dos serviços, preservando as origens administrativas confirmadas:

```routeros
# PROPOSTA — NÃO EXECUTAR sem confirmar os CIDRs atuais
/ip service set [find name=api-ssl] \
    address=<CIDRS_ADMINISTRATIVOS_API_SSL>
/ip service set [find name=winbox] \
    address=<CIDRS_ADMINISTRATIVOS_WINBOX>
```

Como segunda camada, somente após revisar a ordem do firewall:

```routeros
# PROPOSTA — placeholders; inserir antes de drops amplos
/ip firewall address-list add list=REDETI-ADMIN-SOURCES \
    address=<ORIGEM_ADMIN_AUTORIZADA> \
    comment="REDETI approved administrative source"

/ip firewall filter add chain=input action=accept \
    protocol=tcp dst-port=8729 \
    src-address-list=REDETI-ADMIN-SOURCES \
    connection-state=new \
    comment="REDETI allow API-SSL approved sources"

/ip firewall filter add chain=input action=drop \
    protocol=tcp dst-port=8729 \
    connection-state=new \
    comment="REDETI deny API-SSL other sources"

/ip firewall filter add chain=input action=accept \
    protocol=tcp dst-port=8899 \
    src-address-list=REDETI-ADMIN-SOURCES \
    connection-state=new \
    comment="REDETI allow WinBox approved sources"

/ip firewall filter add chain=input action=drop \
    protocol=tcp dst-port=8899 \
    connection-state=new \
    comment="REDETI deny WinBox other sources"
```

Para IPv6, não assumir que IPv4 protege IPv6. Se os serviços estiverem ouvindo em IPv6, criar regras equivalentes usando `src-address-list` IPv6 e revisar interface lists:

```routeros
# PROPOSTA — somente se IPv6 estiver habilitado e os CIDRs forem confirmados
/ipv6 firewall filter add chain=input action=accept \
    protocol=tcp dst-port=8729 \
    src-address-list=REDETI-ADMIN-SOURCES-V6 \
    connection-state=new \
    comment="REDETI allow IPv6 API-SSL approved sources"

/ipv6 firewall filter add chain=input action=drop \
    protocol=tcp dst-port=8729 \
    connection-state=new \
    comment="REDETI deny IPv6 API-SSL other sources"

/ipv6 firewall filter add chain=input action=accept \
    protocol=tcp dst-port=8899 \
    src-address-list=REDETI-ADMIN-SOURCES-V6 \
    connection-state=new \
    comment="REDETI allow IPv6 WinBox approved sources"

/ipv6 firewall filter add chain=input action=drop \
    protocol=tcp dst-port=8899 \
    connection-state=new \
    comment="REDETI deny IPv6 WinBox other sources"
```

As regras não devem ser aplicadas até confirmar que o operador mantém uma sessão alternativa. Não alterar o `wg-escritorio`, UDP 13231, nem regras L2TP.

## Certificado API-SSL

O certificado continua sendo um gate independente do WireGuard. Planejamento:

1. Criar/importar certificado de servidor com `key-usage=tls-server`.
2. Incluir SAN DNS e/ou IP exatamente correspondente ao endpoint usado pelo MCP.
3. Atribuir ao `api-ssl` TCP/8729.
4. Manter API sem TLS desabilitada.
5. Instalar somente a CA pública no Hermes.
6. Configurar MCP com `ssl_verify=true` e `ssl_verify_hostname=true`.
7. Confirmar TLS normal antes de usar o MCP para inventário.

Não usar `verify=false`, `curl -k`, cifra `ADH` ou API sem TLS.

## WireGuard independente proposto

A interface `wg-redeti-recovery` deve ser separada de `wg-escritorio`.

Parâmetros candidatos:

- interface: `wg-redeti-recovery`;
- porta UDP candidata: `<UDP_PORTA_NOVA>` — deve ser confirmada livre;
- rede: `10.255.254.0/29`;
- MikroTik: `10.255.254.1/29`;
- Hermes: `10.255.254.2/32`;
- Recovery OS: `10.255.254.3/32`;
- nenhum anúncio de LAN;
- nenhum NAT entre peers;
- nenhum acesso dos peers ao próprio MikroTik.

Não escolher porta igual a UDP 13231. A porta nova deve ser confirmada contra `/interface wireguard print`, `/ip service`, NAT, raw, mangle e logs.

Comandos propostos — NÃO EXECUTAR nesta etapa:

```routeros
/interface wireguard add \
    name=wg-redeti-recovery \
    listen-port=<UDP_PORTA_NOVA> \
    mtu=1420 \
    comment="REDETI Recovery isolated session VPN"

/ip address add \
    address=10.255.254.1/29 \
    interface=wg-redeti-recovery \
    comment="REDETI Recovery isolated tunnel"

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
```

Nenhuma chave real deve ser gerada nesta fase.

## Firewall do WireGuard

Objetivo: somente Hermes → Recovery OS TCP/22.

Permitido:

- handshake UDP da porta nova, com origem restrita quando possível;
- forward `10.255.254.2/32` → `10.255.254.3/32`, TCP/22;
- retorno `established,related`.

Bloqueado:

- input da interface WG para administração do MikroTik;
- WG → `192.168.0.0/24`;
- WG → `192.168.38.0/24`;
- WG → `192.168.200.0/24`;
- WG → `10.210.210.0/30`;
- WG → `10.1.5.0/24`;
- WG → L2TP e `wg-escritorio`;
- qualquer serviço diferente de TCP/22 no Recovery.

Comandos propostos — posição depende do firewall real:

```routeros
# Handshake — fonte precisa ser definida após inventário
/ip firewall filter add chain=input action=accept \
    protocol=udp dst-port=<UDP_PORTA_NOVA> \
    src-address-list=REDETI-WG-PEER-SOURCES \
    connection-state=new \
    comment="REDETI allow isolated Recovery WG handshake"

# Nunca permitir gestão do MikroTik pela nova interface
/ip firewall filter add chain=input action=drop \
    in-interface=wg-redeti-recovery \
    comment="REDETI block MikroTik management from Recovery WG"

# Único fluxo de aplicação
/ip firewall filter add chain=forward action=accept \
    in-interface=wg-redeti-recovery \
    src-address=10.255.254.2/32 \
    dst-address=10.255.254.3/32 \
    protocol=tcp dst-port=22 \
    connection-state=new \
    comment="REDETI Hermes to Recovery SSH only"

/ip firewall filter add chain=forward action=accept \
    src-address=10.255.254.3/32 \
    dst-address=10.255.254.2/32 \
    connection-state=established,related \
    comment="REDETI Recovery return traffic"

# Bloqueio de demais destinos pela nova interface
/ip firewall filter add chain=forward action=drop \
    in-interface=wg-redeti-recovery \
    comment="REDETI block Recovery WG to client networks"
```

As regras IPv6 equivalentes devem existir se a interface/túnel tiver IPv6; caso contrário, garantir que IPv6 esteja explicitamente desabilitado ou bloqueado conforme a política vigente. Não inferir isso sem inventário.

## Backup, Safe Mode e aplicação futura

Gate de backup:

```routeros
/system backup save name=pre-wg5-security-<YYYYMMDD-HHMMSS>
/export terse hide-sensitive file=pre-wg5-security-<YYYYMMDD-HHMMSS>
```

Aplicação futura em etapas independentes:

### Etapa A — certificado API-SSL

- autorização separada;
- backup confirmado;
- aplicar certificado;
- testar TLS;
- habilitar validação estrita no MCP;
- repetir inventário read-only.

### Etapa B — proteção 8729/8899

- confirmar origem administrativa e canal alternativo;
- ajustar `address=` dos serviços;
- inserir regras específicas somente se necessárias;
- testar API-SSL e WinBox pelo caminho autorizado;
- validar IPv4 e IPv6.

### Etapa C — WireGuard isolado

- confirmar porta e sub-rede livres;
- entrar em Safe Mode por console/WinBox;
- criar interface/IP/peers;
- inserir regras específicas;
- testar handshake e contadores;
- testar Hermes → Recovery TCP/22;
- testar bloqueio para RouterOS e LAN;
- revalidar `wg-escritorio`, L2TP, rotas e NAT.

A sessão administrativa deve ser mantida aberta durante a aplicação. O operador deve ter console/WinBox local como fallback antes de inserir qualquer drop.

## Critérios de aprovação

Não avançar para WG-6 até todos passarem:

- certificado API-SSL válido e SAN correto;
- MCP validando cadeia e hostname;
- WinBox/API-SSL acessíveis somente das origens autorizadas;
- IPv4 e IPv6 sem exposição administrativa indevida;
- raw/mangle/interface lists revisados;
- `wg-escritorio` UDP 13231 inalterado;
- porta nova WireGuard livre;
- sub-rede sem conflito real;
- Hermes → Recovery TCP/22 funcionando;
- Recovery → LAN, Recovery → MikroTik e demais portas bloqueados;
- RX/TX e handshake WireGuard confirmados;
- backup e rollback verificáveis;
- working tree/relatório sem segredos.

## Rollback

- Remover somente peers/interface/IP/regras com comentários WG-5.
- Restaurar certificado/endereço do `api-ssl` ao baseline validado.
- Restaurar regras 8729/8899 ao baseline somente se a mudança causar bloqueio.
- Não tocar em `wg-escritorio`, L2TP, rotas ou NAT existentes.
- Revalidar acesso administrativo e conectividade do cliente.
- Usar backup binário apenas por procedimento aprovado.

## Resultado

`READY_FOR_SEPARATE_AUTHORIZED_STAGING`

WG-5 está preparado como plano, mas nenhuma alteração foi aplicada e nenhuma chave real foi gerada. O inventário de IPv6/raw/mangle/interface lists e a origem administrativa real continuam pendentes da correção TLS/MCP ou de outputs RouterOS read-only sanitizados.
