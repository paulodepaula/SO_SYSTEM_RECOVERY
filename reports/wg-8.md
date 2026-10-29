# RedeTI — WG-8: validação dos backups recebidos

- Etapa: `WG-8 — validar backups recebidos`
- Validado em UTC: `2026-10-29T02:49:48Z`
- Alvo declarado: MikroTik Cidade Verde — `RB3011UiAS`, RouterOS `7.20.8`
- Estado: `BACKUP_VALIDATED`

## Resultado

Os dois arquivos esperados estão presentes no diretório protegido:

`/home/paulo/.local/share/redeti/routeros-backups`

- Diretório: modo `0700`.
- Arquivos: regulares.
- Links simbólicos: nenhum.
- Permissões corrigidas/verificadas: `0600`.
- Conteúdo: não exibido.
- Publicação no GitHub: não realizada.

## Metadados e SHA-256

| Arquivo | Tamanho | Modo | SHA-256 |
|---|---:|---:|---|
| `pre-wg8-apissl.backup` | `49544` bytes | `0600` | `e3d229e48e429047c90a83cb866257b68de263d138725d80cbc831de586809c1` |
| `pre-wg8-apissl.rsc` | `6265` bytes | `0600` | `d4c74903c29681e9ed87c97ff9fa43deb588ce866b66ac22a8e08dd4a7768d98` |

Os hashes foram calculados localmente sem imprimir o conteúdo. A alteração realizada nesta etapa foi somente a correção das permissões locais de `0664` para `0600`.

## Identidade de origem

A identidade foi corroborada por inspeção interna do export `.rsc`, sem emitir conteúdo:

- marcador de modelo `RB3011UiAS`: presente;
- marcador de RouterOS `7.20.8`: presente;
- método: varredura interna de marcadores do export, sem exposição de conteúdo.

O arquivo `.backup` é binário/opaco; sua origem é vinculada ao export correspondente, nome do procedimento e cadeia de transferência fornecida pelo operador. A validação não abriu nem publicou o conteúdo binário.

## Verificações realizadas

- presença de exatamente um `.backup` e um `.rsc` esperado;
- tamanho maior que zero;
- tipo regular;
- ausência de symlink;
- modo `0600` em ambos;
- hash SHA-256 calculado;
- diretório protegido em modo `0700`;
- arquivos fora do repositório e não publicados no GitHub.

## Próxima etapa TLS — preparada, não executada

### Backup preservado

Não mover, editar ou versionar os arquivos. Manter ambos no diretório protegido para rollback.

### Criação da CA interna

```routeros
/certificate add name=redeti-ca-cidade-verde \
    common-name=REDETI-CA-CIDADE-VERDE \
    key-usage=key-cert-sign,crl-sign \
    days-valid=3650
/certificate sign redeti-ca-cidade-verde \
    name=redeti-ca-cidade-verde
```

### Certificado do servidor

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

### Validação antes da atribuição

```routeros
/certificate print detail where name~"redeti-(ca|api)-cidade-verde"
```

Confirmar CA válida, SAN IP correto, `tls-server`, validade e chave privada correspondente.

### Exportar somente a CA pública

```routeros
/certificate export-certificate redeti-ca-cidade-verde \
    type=pem file=redeti-ca-cidade-verde
```

Não transferir a chave privada da CA, a chave privada do servidor, o `.backup` ou o export completo ao Hermes/GitHub/chat.

### Atribuir o certificado ao API-SSL

```routeros
/ip service set [find name=api-ssl] \
    disabled=no port=8729 \
    certificate=redeti-api-cidade-verde-signed
```

A restrição de origem permanece uma etapa separada, após confirmar a origem real do MCP e manter uma sessão administrativa alternativa:

```routeros
/ip service set [find name=api-ssl] \
    address=<CIDRS_ADMINISTRATIVOS_CONFIRMADOS>
```

## Validação TLS externa

```bash
openssl s_client \
  -connect 164.163.166.19:8729 \
  -CAfile <CA_PUBLICA_PROTEGIDA.pem> \
  -verify_return_error \
  -verify_hostname 164.163.166.19 \
  -tls1_2
```

Aprovar somente se a cadeia, SAN e hostname forem válidos e nenhuma cifra `ADH-*` for necessária. Testar TLS 1.3 separadamente quando suportado. Não usar `-k`.

## MCP estrito

Configuração alvo:

```text
use_ssl=true
ssl_verify=true
ssl_verify_hostname=true
ca_file=<CAMINHO_DA_CA_PUBLICA_PROTEGIDA>
```

Antes de alterar o MCP de produção:

1. confirmar suporte real da biblioteca a `cafile`/`SSLContext`;
2. testar CA e hostname corretos;
3. confirmar rejeição de CA/hostname incorretos;
4. habilitar validação estrita;
5. repetir inventário somente leitura.

## Rollback preparado

Registrar o baseline do serviço antes da alteração. Se falhar:

```routeros
/ip service set [find name=api-ssl] \
    certificate=<CERTIFICADO_ANTERIOR> \
    port=<PORTA_ANTERIOR> \
    address=<ADDRESS_ANTERIOR> \
    disabled=<ESTADO_ANTERIOR>
```

Se necessário, restaurar o `.backup` pela sessão WinBox/console autorizada. Não executar remoção ampla nem alterar WireGuard, L2TP, rotas, NAT ou firewall não relacionado.

## Não executado

- CA: não criada.
- Certificado: não criado.
- API-SSL: não alterada.
- MCP: não alterado.
- Firewall/NAT/rotas/VPNs: não alterados.
- WireGuard: não iniciado.
- Recovery OS: não modificado.

## Resultado final

`BACKUP_VALIDATED`

Os backups recebidos foram validados por presença, tamanho, permissões, tipo, ausência de links simbólicos, SHA-256 e marcadores de identidade no export. A próxima etapa está preparada, mas qualquer ativação TLS exige autorização separada e não foi executada nesta etapa.
