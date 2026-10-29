# RedeTI — Relatório WG-7: backup e preparação final TLS

- Etapa: `WG-7 — backup e preparação final TLS`
- Gerado em UTC: `2026-10-28T23:02:00Z`
- Projeto: `SO_SYSTEM_RECOVERY`
- Alvo: MikroTik Cidade Verde — `RB3011UiAS`, RouterOS `7.20.8`
- Estado: `BLOCKED_SECURE_ROUTEROS_ACCESS`
- `READY_FOR_TLS_CHANGE`: **não declarado**

## Resultado executivo

A autorização para criar backup foi recebida, mas a operação exige uma sessão administrativa RouterOS segura e o acesso MCP continua falhando antes da autenticação:

`SSLV3_ALERT_HANDSHAKE_FAILURE`

Não foi usado API sem TLS, `verify=false`, cifra anônima, SSH alternativo ou qualquer contorno. Portanto:

- backup binário remoto: `NOT_RUN`;
- export remoto: `NOT_RUN`;
- identidade via sessão MCP: `BLOCKED_TLS`;
- configuração do MikroTik: não alterada;
- API-SSL, firewall, NAT, rotas e VPNs: não alterados.

## Ambiente local Hermes

- Espaço livre em `/home/paulo`: aproximadamente `106 GB`.
- Espaço livre em `/tmp`: aproximadamente `106 GB`.
- Diretório protegido preparado:

`/home/paulo/.local/share/redeti/routeros-backups`

Permissões:

- proprietário: usuário Hermes local;
- modo: `0700`;
- conteúdo: vazio; nenhum backup fictício criado.

A pasta anterior `/home/paulo/REDETI-Network/routeros-backups` estava em modo `775` e não foi usada para armazenar artefatos sensíveis.

## Comandos de backup preparados — não executados

Em uma sessão RouterOS autenticada e protegida, após confirmar identidade e versão:

```routeros
/system identity print
/system resource print
/system routerboard print

/system backup save name=pre-wg7-apissl-<YYYYMMDD-HHMMSS>
/export terse hide-sensitive file=pre-wg7-apissl-<YYYYMMDD-HHMMSS>
/file print detail where name~"pre-wg7-apissl-"
```

Requisitos para considerar o backup válido:

- nome identificável e timestamp real;
- arquivo `.backup` presente;
- export `.rsc` presente;
- tamanho não zero;
- origem confirmada no RB3011 correto;
- cópia transferida ao diretório local `0700`;
- hash SHA-256 calculado localmente;
- comparação de tamanho/hash após cópia;
- nenhum arquivo publicado no GitHub.

O export deve permanecer com `hide-sensitive`; não usar `show-sensitive`.

## Procedimento de transferência protegido

Somente após obter os arquivos em canal administrativo autorizado:

1. manter o backup binário e o export fora do Git;
2. copiar para `/home/paulo/.local/share/redeti/routeros-backups/`;
3. aplicar modo `0600` aos arquivos;
4. calcular SHA-256 local;
5. confirmar que os arquivos pertencem ao operador local e não são symlinks;
6. preservar uma cópia protegida;
7. nunca enviar o `.backup`, export completo ou chave privada para GitHub/chat.

Exemplo local, somente após os arquivos existirem e a origem ser confirmada:

```bash
install -m 0600 <BACKUP_RECEBIDO> \
  /home/paulo/.local/share/redeti/routeros-backups/
sha256sum /home/paulo/.local/share/redeti/routeros-backups/<ARQUIVO>
stat -c '%A %a %U:%G %s %n' \
  /home/paulo/.local/share/redeti/routeros-backups/<ARQUIVO>
```

Nenhum desses comandos de cópia foi executado porque os arquivos remotos não existem.

## CA e certificado preparados, não criados

CA interna planejada:

- nome: `redeti-ca-cidade-verde`;
- chave privada: armazenamento protegido, nunca publicada;
- certificado público: único artefato a ser transferido ao Hermes.

Certificado do servidor:

- nome: `redeti-api-cidade-verde`;
- SAN obrigatório: `IP:164.163.166.19`;
- uso: `tls-server`;
- API-SSL: TCP/8729.

Comandos RouterOS revisados e preparados, mas não executados:

```routeros
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

/ip service set [find name=api-ssl] \
    disabled=no port=8729 \
    certificate=redeti-api-cidade-verde-signed
```

Antes da execução, confirmar que não existem objetos com esses nomes e validar a sintaxe `subject-alt-name` específica do RouterOS 7.20.8.

## CA pública e MCP

O MCP atual mantém:

- `use_ssl=true`;
- `ssl_verify=false`;
- `ssl_verify_hostname=false`.

Isso não foi alterado. A correção planejada exige:

```text
use_ssl=true
ssl_verify=true
ssl_verify_hostname=true
ca_file=<CA_PUBLICA_PROTEGIDA>
```

O código do conector não possui ainda um parâmetro explícito de CA customizada. Antes de alterar o MCP de produção, é necessário:

1. confirmar a versão real de `routeros_api` no venv do servidor MCP;
2. validar suporte a `cafile` ou `SSLContext`;
3. preparar e testar extensão mínima do conector, se necessário;
4. instalar somente o certificado público da CA em trust store protegido;
5. testar cadeia e hostname fora do MCP;
6. somente então habilitar validação estrita no perfil.

Não serão usadas cifras `ADH`, `curl -k`, API sem TLS ou `verify=false`.

## Teste TLS após aplicação autorizada

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
- cadeia válida;
- SAN IP validado;
- TLS 1.2 aprovado;
- TLS 1.3 aprovado se suportado;
- nenhuma cifra anônima necessária;
- hostname incorreto rejeitado;
- CA incorreta rejeitada.

Depois do TLS, repetir o inventário read-only MCP e confirmar identidade RB3011/RouterOS 7.20.8 antes de qualquer WireGuard.

## Recuperação e rollback

Se a aplicação futura falhar:

```routeros
# Valores devem vir do baseline real; não executar com placeholders
/ip service set [find name=api-ssl] \
    certificate=<CERTIFICADO_ANTERIOR> \
    port=<PORTA_ANTERIOR> \
    address=<ADDRESS_ANTERIOR> \
    disabled=<ESTADO_ANTERIOR>
```

Se necessário, restaurar o `.backup` em procedimento local autorizado. Não remover objetos por padrões amplos. Não reiniciar como primeira tentativa.

O rollback deve preservar:

- WireGuard existente;
- L2TP;
- rotas;
- NAT;
- firewall não relacionado;
- WinBox e demais serviços.

## Critérios ainda pendentes

- confirmação independente do responsável pelo equipamento para a sessão administrativa;
- correção do handshake TLS/API-SSL;
- criação real do backup remoto;
- criação real do export remoto;
- integridade e hash dos arquivos transferidos;
- validação da CA/certificado;
- instalação da CA pública no Hermes;
- suporte efetivo a CA customizada no conector MCP;
- TLS estrito validado;
- inventário read-only pós-correção.

## Resultado

`BLOCKED_SECURE_ROUTEROS_ACCESS`

O armazenamento local está preparado e os comandos de backup, CA, certificado, MCP, testes e rollback estão documentados. Nenhum backup remoto foi criado porque o acesso seguro ao RouterOS ainda está bloqueado pelo TLS. Não é possível declarar `READY_FOR_TLS_CHANGE` nesta etapa.
