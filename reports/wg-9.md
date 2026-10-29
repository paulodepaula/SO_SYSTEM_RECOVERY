# RedeTI — WG-9: criação controlada de certificados

- Etapa: `WG-9 — criação controlada de certificados`
- Validado em UTC: `2026-10-29T03:02:00Z`
- Alvo: MikroTik Cidade Verde — `RB3011UiAS`, RouterOS `7.20.8`
- Endpoint: `164.163.166.19:8729`
- Estado: `READY_FOR_OPERATOR_CERTIFICATE_CREATION_GATE`
- Criação executada: `NÃO`
- Atribuição ao API-SSL executada: `NÃO`

## 1. Backups protegidos

Os backups do WG-8 continuam disponíveis e íntegros em:

`/home/paulo/.local/share/redeti/routeros-backups`

| Arquivo | Tamanho | Modo | Symlink | SHA-256 | Resultado |
|---|---:|---:|---|---|---|
| `pre-wg8-apissl.backup` | `49544` bytes | `0600` | não | `e3d229e48e429047c90a83cb866257b68de263d138725d80cbc831de586809c1` | PASS |
| `pre-wg8-apissl.rsc` | `6265` bytes | `0600` | não | `d4c74903c29681e9ed87c97ff9fa43deb588ce866b66ac22a8e08dd4a7768d98` | PASS |

Diretório: `0700`. O conteúdo dos arquivos não foi exibido nem publicado.

## 2. Estado dos certificados

O export baseline contém os marcadores de modelo `RB3011UiAS` e RouterOS `7.20.8`. No export não foram encontrados:

- `redeti-ca-cidade-verde`;
- `redeti-api-cidade-verde`;
- SAN `164.163.166.19` associado aos nomes planejados.

Isso confirma que os objetos não existiam no backup de WG-8. A existência atual no equipamento permanece `NOT_VERIFIED_LIVE`, porque o acesso API-SSL ainda não foi restaurado. Não será feita tentativa por API sem TLS.

## 3. Sintaxe e limitações de validação

A documentação oficial `help.mikrotik.com/docs/display/ROS/Certificate` não ficou acessível nesta execução. Os comandos abaixo seguem a sintaxe RouterOS 7 usada no plano e devem passar por tab-completion/validação na console WinBox do RouterOS 7.20.8 antes do Enter.

A verificação local de sintaxe não substitui a validação do terminal RouterOS. Se qualquer propriedade não for aceita, interromper sem adaptação especulativa.

## 4. Comandos finais preparados

### 4.1 Pré-leitura na sessão WinBox autorizada

```routeros
/system identity print
/system resource print
/system routerboard print
/certificate print detail
/ip service print detail where name=api-ssl
```

Confirmar novamente identidade, versão e que os nomes não foram criados por outro operador.

### 4.2 Criar CA interna

```routeros
/certificate add name=redeti-ca-cidade-verde \
    common-name=REDETI-CA-CIDADE-VERDE \
    key-usage=key-cert-sign,crl-sign \
    days-valid=3650
/certificate sign redeti-ca-cidade-verde \
    name=redeti-ca-cidade-verde
```

A chave privada da CA deve permanecer protegida no equipamento/armazenamento administrativo aprovado. Não publicar nem transferir a chave privada.

### 4.3 Criar certificado do servidor

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

Requisitos do certificado:

- SAN exato: `IP:164.163.166.19`;
- uso: `tls-server`;
- assinatura pela CA `redeti-ca-cidade-verde`;
- validade vigente;
- chave privada correspondente presente no RouterOS.

Não adicionar DNS inexistente ao SAN. Se um DNS administrativo for definido posteriormente, ele deve ser incluído em um certificado separado/renovado com SAN DNS e IP.

## 5. Validação da cadeia e chave

```routeros
/certificate print detail where name~"redeti-(ca|api)-cidade-verde"
```

Aprovar somente se:

- a CA estiver marcada como CA;
- o certificado do servidor estiver assinado pela CA correta;
- SAN contiver `IP:164.163.166.19`;
- key usage contiver `tls-server`;
- certificado não estiver expirado;
- a chave privada correspondente estiver presente;
- não houver erro de assinatura/cadeia.

Não atribuir ao `api-ssl` antes desta leitura.

## 6. Exportar somente o certificado público da CA

```routeros
/certificate export-certificate redeti-ca-cidade-verde \
    type=pem file=redeti-ca-cidade-verde
```

Transferir somente o PEM público para o trust store protegido do Hermes. Não transferir:

- chave privada da CA;
- chave privada do servidor;
- `.backup`;
- export completo;
- senha/passphrase.

Validar que o arquivo exportado é o certificado público da CA antes de instalar no Hermes.

## 7. Atribuição futura ao API-SSL — fora desta etapa

Somente com autorização administrativa específica após a validação acima:

```routeros
/ip service set [find name=api-ssl] \
    disabled=no \
    port=8729 \
    certificate=redeti-api-cidade-verde-signed
```

WG-9 não executa esse comando. Firewall, origem administrativa, NAT e demais serviços permanecem inalterados.

## 8. MCP futuro — fora desta etapa

Configuração alvo, não aplicada:

```text
use_ssl=true
ssl_verify=true
ssl_verify_hostname=true
ca_file=<CAMINHO_DA_CA_PUBLICA_PROTEGIDA>
```

Antes de alterar o MCP:

1. confirmar suporte da biblioteca a `cafile`/`SSLContext`;
2. instalar somente a CA pública;
3. testar cadeia e hostname corretos;
4. confirmar rejeição de CA/hostname incorretos;
5. habilitar validação estrita;
6. repetir inventário somente leitura.

## 9. Rollback

Se a criação dos objetos for autorizada, mas a validação falhar antes da atribuição ao serviço, remover somente os objetos recém-criados após confirmação dos nomes:

```routeros
/certificate remove [find name=redeti-api-cidade-verde-signed]
/certificate remove [find name=redeti-api-cidade-verde]
/certificate remove [find name=redeti-ca-cidade-verde]
```

Não executar remoção ampla. Se a atribuição ao API-SSL ocorrer em etapa posterior e falhar, restaurar o baseline registrado:

```routeros
/ip service set [find name=api-ssl] \
    certificate=<CERTIFICADO_ANTERIOR> \
    port=<PORTA_ANTERIOR> \
    address=<ADDRESS_ANTERIOR> \
    disabled=<ESTADO_ANTERIOR>
```

O backup `pre-wg8-apissl.backup` permanece preservado para recuperação WinBox/console aprovada.

## 10. Não executado

- criação da CA: não executada;
- criação do certificado: não executada;
- export da CA pública: não executado;
- atribuição ao API-SSL: não executada;
- MCP: não alterado;
- firewall/NAT/rotas: não alterados;
- VPNs/WireGuard: não alterados;
- Recovery OS: não modificado.

## Resultado

`READY_FOR_OPERATOR_CERTIFICATE_CREATION_GATE`

Os backups estão validados e o procedimento está preparado para execução controlada pelo operador. Isso não autoriza a execução automática: a criação da CA/certificado ainda requer autorização administrativa específica e validação da sintaxe diretamente na console RouterOS 7.20.8.
