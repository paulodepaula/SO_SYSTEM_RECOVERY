# RedeTI — Relatório WG-8: validação de backup e preparação final TLS

- Etapa: `WG-8 — validar backup e preparar ativação TLS`
- Gerado em UTC: `2026-10-29T00:08:00Z`
- Projeto: `SO_SYSTEM_RECOVERY`
- Alvo: MikroTik Cidade Verde — `RB3011UiAS`, RouterOS `7.20.8`
- Endpoint: `164.163.166.19:8729`
- Estado: `BLOCKED_BACKUPS_NOT_AVAILABLE`
- `READY_FOR_TLS_CHANGE`: **não declarado**

## Resultado da verificação local

Diretório autorizado:

`/home/paulo/.local/share/redeti/routeros-backups`

Verificação realizada:

- permissão: `0700`;
- proprietário: usuário local Hermes;
- arquivos encontrados: `0`;
- backup binário: não disponível;
- export `.rsc`: não disponível;
- tamanhos: não calculados;
- SHA-256: não calculado;
- cópia no GitHub: não realizada.

Nenhum arquivo foi procurado fora desse diretório, nenhum backup foi inventado e nenhuma operação remota foi repetida por canal inseguro.

## Gate de validação quando os arquivos forem disponibilizados

Após o operador copiar os dois arquivos para o diretório protegido, executar somente localmente:

```bash
D=/home/paulo/.local/share/redeti/routeros-backups
find "$D" -maxdepth 1 -type f -printf '%f\n'
stat -c '%A %a %U:%G %s %n' "$D"/*
sha256sum "$D"/*
```

Critérios:

- exatamente um `.backup` binário e um export `.rsc` esperado;
- tamanho maior que zero;
- modo recomendado `0600` nos arquivos;
- proprietário local correto;
- nenhum symlink inesperado;
- SHA-256 registrado somente como metadado sanitizado;
- arquivos fora do repositório Git e fora do GitHub.

Não publicar conteúdo, hash de segredo, export integral ou backup binário no relatório. O hash SHA-256 do arquivo, isoladamente, pode ser registrado como metadado quando os arquivos existirem.

## Comandos de backup de origem — já preparados, não executados pelo Hermes

Na sessão WinBox autorizada do operador:

```routeros
/system identity print
/system resource print
/system routerboard print

/system backup save name=pre-wg8-apissl-<YYYYMMDD-HHMMSS>
/export terse hide-sensitive file=pre-wg8-apissl-<YYYYMMDD-HHMMSS>
/file print detail where name~"pre-wg8-apissl-"
```

O operador deve transferir os arquivos por canal administrativo protegido para o diretório acima. Não usar:

```routeros
/export show-sensitive
```

Não transferir chaves privadas, senhas, tokens, PSKs ou certificados privados.

## Sequência final de ativação TLS — preparada, não executar nesta etapa

### 1. Pré-leitura

```routeros
/system identity print
/system resource print
/system routerboard print
/ip service print detail where name=api-ssl
/certificate print detail
/ip firewall filter print detail stats where chain=input
/ip firewall nat print detail
```

Confirmar novamente identidade, RouterOS 7.20.8, porta 8729, origem administrativa e ausência de alteração concorrente.

### 2. Criar CA interna

```routeros
/certificate add name=redeti-ca-cidade-verde \
    common-name=REDETI-CA-CIDADE-VERDE \
    key-usage=key-cert-sign,crl-sign \
    days-valid=3650
/certificate sign redeti-ca-cidade-verde \
    name=redeti-ca-cidade-verde
```

### 3. Criar e assinar certificado do servidor

```routeros
/certificate add name=redeti-api-cidade-verde \
    common-name=164.163.166.19 \
    subject-alt-name=IP:164.163.166.19 \
    key-usage=tls-server \
    days-valid=825
/certificate sign redeti-api-cidade-verde \
    ca=redeti-ca-cidade-verde \
    name=redeti-api-cidade-verde-signed
```

A sintaxe deve ser confirmada no terminal RouterOS 7.20.8 com tab-completion antes de executar. Se a versão exigir formato diferente para `subject-alt-name`, interromper; não substituir por validação somente de `common-name`.

### 4. Validar certificado antes de atribuir

```routeros
/certificate print detail where name~"redeti-(ca|api)-cidade-verde"
```

Obrigatório:

- certificado de CA válido;
- certificado de servidor assinado pela CA correta;
- SAN `IP:164.163.166.19`;
- `key-usage=tls-server`;
- chave privada correspondente presente no RouterOS;
- validade vigente.

### 5. Exportar somente a CA pública

```routeros
/certificate export-certificate redeti-ca-cidade-verde \
    type=pem file=redeti-ca-cidade-verde
```

Transferir somente o PEM público. A chave privada da CA e a chave privada do servidor nunca devem ser publicadas ou transferidas ao GitHub/chat.

### 6. Atribuir ao API-SSL

```routeros
/ip service set [find name=api-ssl] \
    disabled=no \
    port=8729 \
    certificate=redeti-api-cidade-verde-signed
```

A restrição de origem deve ser uma etapa separada, depois de confirmar a origem do MCP e manter uma sessão administrativa alternativa:

```routeros
/ip service set [find name=api-ssl] \
    address=<CIDRS_ADMINISTRATIVOS_CONFIRMADOS>
```

Não usar `0.0.0.0/0` como origem administrativa.

## Teste externo TLS

Após a atribuição autorizada:

```bash
openssl s_client \
  -connect 164.163.166.19:8729 \
  -CAfile <CA_PUBLICA_PROTEGIDA.pem> \
  -verify_return_error \
  -verify_hostname 164.163.166.19 \
  -tls1_2
```

Critérios:

- certificado apresentado;
- cadeia válida;
- SAN IP validado;
- hostname validado;
- nenhuma cifra `ADH-*`;
- falha com CA incorreta;
- falha com hostname incorreto.

Testar TLS 1.3 separadamente se suportado pelo serviço. Não usar `-k`.

## Configuração MCP preparada

A configuração final deve ser equivalente a:

```text
use_ssl=true
ssl_verify=true
ssl_verify_hostname=true
ca_file=<CAMINHO_DA_CA_PUBLICA_PROTEGIDA>
```

Antes da alteração do MCP de produção:

1. confirmar suporte da biblioteca `routeros_api` a CA customizada;
2. usar `cafile` ou `SSLContext` verificado;
3. testar em ambiente controlado;
4. confirmar rejeição de CA/hostname incorretos;
5. alterar o perfil somente após o teste;
6. repetir inventário RouterOS estritamente read-only.

A configuração atual do MCP não foi alterada nesta etapa.

## Rollback preparado

Registrar os valores anteriores antes da atribuição. Se a validação falhar:

```routeros
/ip service set [find name=api-ssl] \
    certificate=<CERTIFICADO_ANTERIOR> \
    port=<PORTA_ANTERIOR> \
    address=<ADDRESS_ANTERIOR> \
    disabled=<ESTADO_ANTERIOR>
```

Se necessário, restaurar o backup binário através de procedimento WinBox/console aprovado. Remover somente objetos criados com os nomes WG-6/WG-8 confirmados; não executar remoções amplas.

Rollback deve preservar WireGuard existente, L2TP, rotas, NAT, firewall não relacionado e demais serviços.

## Não executado

- certificados: não criados;
- API-SSL: não alterada;
- MCP: não alterado;
- firewall/NAT: não alterados;
- rotas/VPNs: não alteradas;
- WireGuard: não executado;
- Recovery OS: não modificado;
- backup/export: não disponíveis localmente.

## Resultado

`BLOCKED_BACKUPS_NOT_AVAILABLE`

O relatório final de ativação está preparado, mas o gate de backup não foi satisfeito: o diretório protegido está vazio. Após a disponibilização dos arquivos, será possível validar existência, tamanho, permissões e SHA-256 sem publicar os artefatos. Somente depois do backup validado, CA pública instalada e suporte de CA customizada confirmado no MCP poderá ser solicitada a autorização para ativação TLS.
