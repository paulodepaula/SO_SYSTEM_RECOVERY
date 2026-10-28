# RedeTI — Relatório WG-6: preparação do certificado API-SSL

- Etapa: `WG-6 — preparação e validação da correção TLS`
- Gerado em UTC: `2026-10-28T22:55:00Z`
- Projeto: `SO_SYSTEM_RECOVERY`
- Alvo: MikroTik Cidade Verde — `RB3011UiAS`, RouterOS `7.20.8`
- Endpoint MCP: `164.163.166.19:8729`
- Estado: `BLOCKED_PENDING_AUTHORIZED_TLS_CHANGE`
- `READY_FOR_TLS_CHANGE`: **não declarado**

## Motivo do bloqueio

Os pré-requisitos de execução ainda não estão satisfeitos:

- o `api-ssl` continua com `certificate=none`;
- não há certificado cadastrado no RouterOS;
- o MCP ainda usa validação TLS/hostname desabilitada;
- a CA pública ainda não foi instalada no ambiente MCP;
- o backup binário e o export ainda não foram criados no MikroTik.

Criar backup/export no RouterOS grava arquivos no equipamento. Como esta etapa proíbe alterações no MikroTik e no MCP de produção, os comandos foram somente preparados.

## Evidências utilizadas

- Modelo: `RB3011UiAS`.
- RouterOS: `7.20.8`.
- API-SSL: TCP/8729, `certificate=none`.
- Nenhum certificado cadastrado.
- NAT TCP/8729 não identificado.
- IP público fixo: `164.163.166.19`.
- WireGuard existente e demais serviços devem permanecer intocados.

A evidência WG-2 mostrou TCP acessível e TLS normal falhando, com negociação somente através de `ADH-AES256-SHA256` sem certificado de peer.

## Desenho de PKI

CA interna exclusiva:

- nome RouterOS: `redeti-ca-cidade-verde`;
- finalidade: assinar exclusivamente o certificado API-SSL do Cidade Verde;
- validade sugerida: 10 anos, sujeita à política interna;
- chave privada: nunca publicar, nunca colocar no Git, nunca enviar ao Hermes;
- certificado público da CA: único material que será transferido ao Hermes.

Certificado de servidor:

- nome RouterOS: `redeti-api-cidade-verde`;
- SAN obrigatório: `IP:164.163.166.19`;
- SAN DNS adicional, somente se existir DNS administrativo real: `DNS:<API_SSL_DNS>`;
- key usage: `tls-server`;
- validade sugerida: 825 dias, sujeita à política de rotação;
- uso exclusivo no serviço API-SSL TCP/8729.

A configuração deve usar o mesmo IP/DNS presente no SAN. Não confiar somente em `common-name`.

## Gate 1 — backup futuro, antes de escrita

Executar somente em janela autorizada e em sessão RouterOS protegida:

```routeros
# ESCRITA NO EQUIPAMENTO — NÃO EXECUTAR NESTA ETAPA
/system backup save name=pre-wg6-apissl-<YYYYMMDD-HHMMSS>
/export terse hide-sensitive file=pre-wg6-apissl-<YYYYMMDD-HHMMSS>
```

Requisitos:

- confirmar que o backup binário foi criado;
- guardar o `.backup` em armazenamento protegido;
- revisar o export sem segredos antes de qualquer publicação;
- não usar `show-sensitive`;
- não colocar `.backup` ou chaves no Git.

## Gate 2 — inspeção read-only imediatamente antes da aplicação

```routeros
/system identity print
/system resource print
/ip service print detail where name=api-ssl
/ip firewall filter print detail stats where chain=input
/ip firewall nat print detail
/certificate print detail
/ip address print detail
/ip route print detail
```

Confirmar novamente:

- serviço `api-ssl` ainda na porta 8729;
- nenhuma atribuição de certificado concorrente;
- origem administrativa que deve ser preservada;
- ausência de NAT TCP/8729 inesperado;
- regra input que pode bloquear o teste;
- rota de retorno ao Hermes.

## Gate 3 — emissão proposta no RouterOS

Os comandos abaixo são exatos para a preparação, mas continuam **não executados**. Antes de usar, confirmar a sintaxe de `subject-alt-name` no RouterOS 7.20.8 e garantir que não exista uma CA/certificado válido com o mesmo nome.

```routeros
# ESCRITA — NÃO EXECUTAR NESTA ETAPA
/certificate add name=redeti-ca-cidade-verde \
    common-name=REDETI-CA-CIDADE-VERDE \
    key-usage=key-cert-sign,crl-sign \
    days-valid=3650
/certificate sign redeti-ca-cidade-verde \
    name=redeti-ca-cidade-verde

/certificate add name=redeti-api-cidade-verde \
    common-name=164.163.166.19 \
    subject-alt-name=IP:164.163.166.19 \
    key-usage=tls-server \
    days-valid=825
/certificate sign redeti-api-cidade-verde \
    ca=redeti-ca-cidade-verde \
    name=redeti-api-cidade-verde-signed
```

Se houver DNS administrativo real, substituir o certificado por uma identidade com SAN combinado, por exemplo:

```routeros
# Exemplo parametrizado — NÃO EXECUTAR
/certificate add name=redeti-api-cidade-verde \
    common-name=<API_SSL_DNS> \
    subject-alt-name=DNS:<API_SSL_DNS>,IP:164.163.166.19 \
    key-usage=tls-server \
    days-valid=825
```

Não criar duas CAs. Se a CA for gerada fora do RouterOS, importar somente o certificado/chave do servidor conforme procedimento aprovado e manter a chave privada da CA fora do MikroTik.

## Gate 4 — validação do material no RouterOS

```routeros
# SOMENTE LEITURA
/certificate print detail where name~"redeti-(ca|api)-cidade-verde"
```

Critérios:

- CA marcada como autoridade de certificação;
- certificado de servidor assinado pela CA correta;
- key usage contém `tls-server`;
- chave privada correspondente presente no RouterOS;
- certificado não expirado;
- SAN contém `IP:164.163.166.19`;
- cadeia não está revogada ou inválida.

## Gate 5 — atribuição ao API-SSL

```routeros
# ESCRITA — NÃO EXECUTAR NESTA ETAPA
/ip service set [find name=api-ssl] \
    disabled=no \
    port=8729 \
    certificate=redeti-api-cidade-verde-signed
```

Não alterar `address=` nesta mesma operação sem primeiro registrar o valor atual e confirmar as origens administrativas. A proteção de origem deve ser aplicada em etapa separada para manter rollback claro.

## Gate 6 — restrição de origem sem bloquear administração

Primeiro, identificar a origem real do MCP/operador e manter uma sessão administrativa alternativa aberta. Não presumir que o IP público do MikroTik é o IP de origem do Hermes.

Consulta:

```routeros
/ip service print detail where name=api-ssl
/ip firewall filter print detail stats where chain=input
/ip firewall address-list print detail
```

Proposta parametrizada:

```routeros
# ESCRITA — placeholders; somente após confirmar origens e ordem do firewall
/ip service set [find name=api-ssl] \
    address=<CIDRS_ADMINISTRATIVOS_API_SSL>

/ip firewall address-list add list=REDETI-API-SSL-ADMIN \
    address=<ORIGEM_MCP_OU_ADMIN_AUTORIZADA> \
    comment="REDETI approved API-SSL source"

/ip firewall filter add chain=input action=accept \
    protocol=tcp dst-port=8729 \
    src-address-list=REDETI-API-SSL-ADMIN \
    connection-state=new \
    comment="REDETI allow API-SSL approved source"

/ip firewall filter add chain=input action=drop \
    protocol=tcp dst-port=8729 \
    connection-state=new \
    comment="REDETI deny API-SSL other sources"
```

A regra accept deve ficar antes do drop correspondente e antes de qualquer drop amplo que impeça a origem autorizada. Não abrir `0.0.0.0/0`, não criar NAT TCP/8729 e não alterar regras de VPN.

## Gate 7 — transferência somente da CA pública

No RouterOS, exportar somente o certificado público da CA:

```routeros
# ESCRITA DE ARTEFATO PÚBLICO — NÃO EXECUTAR NESTA ETAPA
/certificate export-certificate redeti-ca-cidade-verde \
    type=pem file=redeti-ca-cidade-verde
```

Transferir somente o PEM público por canal administrativo protegido. Não transferir:

- chave privada da CA;
- private key do servidor;
- backup binário;
- export completo;
- senha ou passphrase.

O arquivo público deve ser instalado no trust store dedicado do MCP com proprietário root e permissões restritas. O caminho real ainda precisa ser definido pelo administrador do ambiente MCP.

## Gate 8 — MCP com validação estrita

O conector atual usa `ssl_verify=false` e `ssl_verify_hostname=false` e não possui no código analisado um caminho explícito para CA customizada. Antes de mudar a produção:

1. confirmar a versão real de `routeros_api` no venv do servidor MCP;
2. validar suporte a `cafile` ou `SSLContext`;
3. se necessário, preparar extensão mínima do conector com parâmetro não secreto `ca_file`;
4. restringir esse caminho ao trust store aprovado;
5. ativar:

```text
use_ssl=true
ssl_verify=true
ssl_verify_hostname=true
ca_file=<CAMINHO_CA_PUBLICA_PROTEGIDA>
```

6. rejeitar CA ausente, SAN divergente, certificado expirado e cadeia inválida;
7. testar o conector em ambiente controlado antes de alterar o perfil de produção.

Não usar `verify=false`, `curl -k`, cifra `ADH` ou API sem TLS.

## Gate 9 — teste externo sem autenticação

Depois de atribuir o certificado e antes do login MCP:

```bash
openssl s_client \
    -connect 164.163.166.19:8729 \
    -verify_return_error \
    -verify_hostname 164.163.166.19 \
    -CAfile <CA_PUBLICA_PROTEGIDA.pem> \
    -tls1_2
```

Critérios:

- certificado apresentado;
- cadeia validada;
- SAN IP validado;
- nenhuma cifra `ADH-*`;
- TLS 1.2 aprovado;
- TLS 1.3 aprovado se suportado pelo serviço;
- falha esperada com hostname incorreto ou CA errada.

Depois, repetir pelo MCP somente em paths read-only:

```text
/system/identity
/system/resource
/system/routerboard
/interface
/ip/address
/ip/route
/ip/firewall/filter
/ip/firewall/nat
```

## Rollback

Se o TLS, MCP ou acesso administrativo falhar:

```routeros
# EXEMPLO PARAMETRIZADO — somente após consultar o baseline
/ip service set [find name=api-ssl] \
    certificate=<CERTIFICADO_ANTERIOR> \
    address=<ADDRESS_ANTERIOR> \
    port=<PORTA_ANTERIOR> \
    disabled=<ESTADO_ANTERIOR>
```

Se regras novas foram criadas, removê-las somente por comentário/ID confirmado. Não usar remoção ampla. Se necessário, restaurar o backup binário em procedimento local aprovado.

O rollback não deve alterar:

- `wg-escritorio` UDP 13231;
- L2TP;
- rotas existentes;
- NAT existente;
- demais serviços.

## Autorizações necessárias

Antes da aplicação, autorizar separadamente:

- criação do backup/export no MikroTik;
- criação/importação da CA e certificado;
- atribuição do certificado ao API-SSL;
- restrição de origem do TCP/8729;
- instalação da CA pública no Hermes;
- alteração do conector MCP para validação estrita;
- teste externo TLS e inventário read-only posterior.

Não autoriza nesta etapa:

- criação de WireGuard;
- peers WireGuard;
- rotas novas;
- NAT novo;
- alteração de VPNs existentes;
- modificação do Recovery OS.

## Resultado

`BLOCKED_PENDING_AUTHORIZED_TLS_CHANGE`

Os comandos, testes e rollback estão preparados, mas backup, CA, certificado, atribuição ao API-SSL, trust store e alteração do MCP ainda não foram executados. Portanto, os pré-requisitos não estão satisfeitos e `READY_FOR_TLS_CHANGE` não deve ser declarado.
