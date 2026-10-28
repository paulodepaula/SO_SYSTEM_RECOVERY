# RedeTI — Relatório WG-4: planejamento da correção API-SSL

- Etapa: `WG-4 — planejamento da correção API-SSL`
- Gerado em UTC: `2026-10-28T22:41:19Z`
- Projeto: `SO_SYSTEM_RECOVERY`
- Alvo: MikroTik Cidade Verde
- Estado: `READY_FOR_AUTHORIZED_TLS_CHANGE`
- Execução de mudanças: `NOT_RUN`

## Evidências confirmadas pelo operador

- Modelo: `RB3011UiAS`.
- RouterOS: `7.20.8`.
- API-SSL: TCP/8729.
- `certificate=none`.
- Nenhum certificado cadastrado.
- Nenhum NAT TCP/8729 identificado.
- IP público fixo disponível.

Essas evidências confirmam a causa do WG-2: o serviço API-SSL não possui certificado de servidor e o endpoint acabou oferecendo somente negociação anônima/incompatível com clientes TLS normais.

## Escopo preservado

A correção planejada não cria nem altera:

- interfaces WireGuard;
- peers WireGuard;
- VPNs existentes;
- rotas existentes;
- NAT existente;
- serviços que não sejam o `api-ssl`;
- regras de firewall fora do escopo estrito de proteção do TCP/8729.

Nenhuma mudança foi executada no MikroTik.

## Dados que ainda precisam ser confirmados antes da escrita

Mesmo com o modelo e versão confirmados, a sessão de implantação deve coletar novamente, sem escrita:

```routeros
/system identity print
/system resource print
/ip service print detail where name=api-ssl
/ip firewall filter print detail stats where chain=input
/ip firewall nat print detail
/ip address print detail
/ip route print detail
/certificate print detail
```

A coleta deve registrar somente:

- identidade, versão e uptime;
- endereço/porta do `api-ssl`;
- posição e contadores das regras input relacionadas a 8729;
- confirmação de ausência de NAT 8729;
- estado dos certificados, validade, SAN, key-usage e chave correspondente;
- redes administrativas autorizadas.

Não exportar senhas, private keys, PSKs, tokens ou configuração sensível completa.

## Identidade do certificado

Como o IP público exato e o DNS administrativo não foram incluídos nesta solicitação, os comandos usam placeholders.

Preferência:

1. Usar um DNS administrativo estável, por exemplo `<API_SSL_DNS>`.
2. Incluir SAN DNS e SAN IP do endpoint efetivamente usado pelo MCP.
3. Fazer o MCP conectar pelo mesmo DNS presente no SAN.
4. Se o acesso depender exclusivamente de IP fixo, incluir `IP:<IP_PUBLICO_FIXO>` no SAN.

Não confiar apenas em `common-name`; a validação deve usar SAN.

## Opção de PKI recomendada

A melhor separação é manter a CA interna protegida no Hermes/PKI e instalar no RB3011 somente o certificado de servidor e sua chave privada. A CA privada não deve ser criada ou exportada pelo MikroTik para o Hermes.

Fluxo futuro:

1. Gerar CA interna em ambiente protegido do Hermes.
2. Gerar CSR/chave do servidor fora do RouterOS ou conforme procedimento aprovado.
3. Assinar certificado com SAN DNS/IP.
4. Importar no RB3011 somente os artefatos necessários ao servidor.
5. Instalar a CA pública no trust store do MCP.
6. Ativar validação de cadeia e hostname.

Se a política operacional exigir CA criada no próprio RouterOS, a alternativa abaixo é possível, mas deixa a CA privada no equipamento e exige controle rigoroso de backup/export.

## Comandos RouterOS propostos — NÃO EXECUTAR nesta etapa

### Inspeção inicial

```routeros
# SOMENTE LEITURA
/system identity print
/system resource print
/ip service print detail where name=api-ssl
/ip firewall filter print detail stats where chain=input
/ip firewall nat print detail
/ip address print detail
/ip route print detail
/certificate print detail
```

### Backup futuro, antes de qualquer escrita

Os nomes devem receber timestamp real no momento da janela autorizada:

```routeros
# ESCRITA — somente após autorização explícita
/system backup save name=pre-wg4-apissl-<YYYYMMDD-HHMMSS>
/export terse hide-sensitive file=pre-wg4-apissl-<YYYYMMDD-HHMMSS>
```

O `.backup` deve permanecer em armazenamento protegido. O export sanitizado não deve conter private keys, senhas, PSKs ou tokens e só poderá ir para Git após revisão.

### Alternativa RouterOS para CA local

Somente se a opção de PKI externa for rejeitada e após revisar a versão 7.20.8:

```routeros
# ESCRITA — NÃO EXECUTAR nesta etapa
/certificate add name=redeti-ca \
    common-name=REDETI-CA \
    key-usage=key-cert-sign,crl-sign \
    days-valid=3650
/certificate sign redeti-ca name=redeti-ca

/certificate add name=redeti-api \
    common-name=<API_SSL_DNS> \
    subject-alt-name=DNS:<API_SSL_DNS>,IP:<IP_PUBLICO_FIXO> \
    key-usage=tls-server \
    days-valid=825
/certificate sign redeti-api ca=redeti-ca name=redeti-api-signed
```

Não executar se já existir uma CA/certificado válido. Confirmar previamente a sintaxe e o suporte a `subject-alt-name` no RouterOS 7.20.8.

### Atribuição ao API-SSL

Depois de confirmar que `redeti-api-signed` possui chave privada, validade, SAN e `tls-server`:

```routeros
# ESCRITA — somente após revisão do estado atual
/ip service set [find name=api-ssl] \
    disabled=no \
    port=8729 \
    certificate=redeti-api-signed \
    address=<CIDRS_ADMINISTRATIVOS_AUTORIZADOS>
```

Não substituir `address=` sem preservar o valor atual e sem confirmar as origens administrativas autorizadas.

## Firewall input

A propriedade `address=` do serviço deve ser usada como primeira restrição. O firewall deve ser revisado antes de inserir qualquer regra.

Leitura obrigatória:

```routeros
/ip firewall filter print detail stats where chain=input
```

Se não existir uma regra equivalente e houver autorização específica, a forma planejada é:

```routeros
# ESCRITA — placeholders; posição deve ser revisada contra o firewall real
/ip firewall filter add chain=input action=accept \
    protocol=tcp dst-port=8729 \
    src-address-list=REDETI-API-SSL-ADMIN \
    connection-state=new \
    comment="REDETI allow API-SSL from approved administrators"

/ip firewall filter add chain=input action=drop \
    protocol=tcp dst-port=8729 \
    connection-state=new \
    comment="REDETI deny API-SSL other sources"
```

A origem administrativa deve ser uma allowlist controlada, não `0.0.0.0/0`. A regra de accept precisa ficar antes do drop correspondente e antes de qualquer drop amplo que impeça a administração autorizada.

Não criar NAT para TCP/8729. O operador confirmou que não há redirecionamento identificado; isso deve permanecer assim se o próprio RB3011 for o endpoint público.

## Distribuição da CA no Hermes

Se for utilizada CA interna:

1. Exportar somente o certificado público da CA.
2. Transferir por canal administrativo protegido.
3. Instalar em trust store dedicado e root-owned no ambiente MCP.
4. Nunca transferir a chave privada da CA.
5. Fazer o conector usar `ssl_verify=true` e `ssl_verify_hostname=true`.
6. Usar o mesmo DNS/IP do SAN.
7. Testar cadeia, hostname e expiração antes do login RouterOS.

O conector atual usa somente flags booleanas e não possui no código analisado um parâmetro explícito de CA customizada. Antes de habilitar uma CA interna, deve-se confirmar a versão do `routeros_api` no venv real do MCP e preparar extensão testada para `cafile`/`SSLContext`, se necessário.

Não alterar `verify=false` para mascarar certificado ausente.

## Testes pós-implantação

Sem autenticar inicialmente:

```bash
openssl s_client \
  -connect <API_SSL_DNS>:8729 \
  -servername <API_SSL_DNS> \
  -verify_hostname <API_SSL_DNS> \
  -CAfile <CA_PUBLICA.pem> \
  -tls1_2
```

Critérios:

- certificado apresentado;
- cadeia validada;
- SAN compatível;
- nenhuma cifra `ADH-*` necessária;
- TLS 1.2 aprovado;
- TLS 1.3 aprovado se suportado pelo serviço;
- falha quando o hostname está errado;
- falha quando a CA não é confiável.

Depois:

1. Executar `mikrotik_health` pelo MCP.
2. Repetir inventário read-only completo.
3. Validar `/interface`, `/ip/address`, `/ip/route`, `/ip/firewall/filter`, `/ip/firewall/nat`.
4. Confirmar que não foram criadas interfaces WireGuard.
5. Confirmar que VPNs e rotas existentes não mudaram.
6. Confirmar contadores das regras input.

Só depois do inventário validado poderá ser iniciado o WG-5 de planejamento/implantação WireGuard.

## Rollback

Se TLS, hostname, API ou administração falharem:

```routeros
# EXEMPLOS PARAMETRIZADOS — somente após identificar valores do baseline
/ip service set [find name=api-ssl] \
    certificate=<CERTIFICADO_ANTERIOR> \
    address=<ADDRESS_ANTERIOR> \
    port=<PORTA_ANTERIOR> \
    disabled=<ESTADO_ANTERIOR>
```

Se alguma regra nova de firewall tiver sido criada, removê-la pelo comentário exato, após confirmação do ID e leitura posterior. Não usar `remove [find]` amplo.

Se o baseline não puder ser restaurado com segurança, interromper e usar o backup binário em procedimento local autorizado. Não reiniciar como primeira ação.

## Autorização necessária

Antes da aplicação, é necessária autorização explícita para:

- criar/importar CA/certificado;
- atribuir certificado ao `api-ssl`;
- alterar `address=` do serviço;
- inserir regras input específicas para TCP/8729;
- criar backup/export no MikroTik;
- instalar CA pública no Hermes;
- alterar o conector MCP para validação estrita ou CA customizada.

A autorização não inclui criação de WireGuard, peers, rotas, NAT ou alteração das VPNs existentes.

## Resultado

`READY_FOR_AUTHORIZED_TLS_CHANGE`

A correção está planejada e parametrizada, mas não executada. O inventário read-only WG-1 será repetido somente após o operador aplicar e validar a correção TLS em janela autorizada. Nenhuma interface WireGuard será criada nesta etapa.
