# RedeTI — Relatório WG-2: diagnóstico TLS RouterOS

- Etapa: `WG-2 — diagnóstico TLS da API-SSL`
- Gerado em UTC: `2026-10-28T21:29:00Z`
- Projeto: `SO_SYSTEM_RECOVERY`
- Perfil: `cidade-verde`
- Estado: `BLOCKED_ROUTEROS_CERTIFICATE_FIX_REQUIRED`

## Resultado executivo

A conectividade TCP até o endpoint público `164.163.166.19:8729` está disponível, mas a negociação TLS normal falha antes de qualquer autenticação RouterOS.

A causa técnica comprovada é que o endpoint só aceita uma cifra TLS anônima quando o cliente relaxa deliberadamente a política local:

```text
Protocol version: TLSv1.2
Ciphersuite: ADH-AES256-SHA256
No peer certificate
Server Temp Key: DH, 2048 bits
```

Cifras `ADH` são anônimas e não fornecem certificado de servidor para autenticação da identidade. Não são uma solução aceitável.

## Configuração MCP inspecionada

O arquivo de configuração do Hermes contém somente a definição do servidor MCP; não contém a credencial `cidade-verde`.

Servidor:

- comando: `mikrotik_server.py`;
- credencial resolvida internamente pelo `credential_id`;
- nenhum segredo exposto.

Metadados do perfil `cidade-verde`:

- destino: `164.163.166.19`;
- porta: `8729`;
- `use_ssl=true`;
- `plaintext_login=true`;
- `ssl_verify=false`;
- `ssl_verify_hostname=false`.

`plaintext_login` só se aplica ao protocolo RouterOS depois de TLS; não causa nem corrige esta falha de handshake.

`ssl_verify=false` e `ssl_verify_hostname=false` são inadequados como configuração permanente, mas não explicam sozinhos o alerta: a sessão falha porque o servidor não oferece um certificado/cifra normal compatível.

## Testes sem autenticação

### TCP

- `164.163.166.19:8729`: `PASS`.

### TLS 1.2 com política padrão

- Resultado: `FAIL`.
- Alerta remoto: `sslv3 alert handshake failure`, número 40.
- Certificado apresentado: nenhum.

### TLS 1.3 com política padrão

- Resultado: `FAIL`.
- Alerta remoto: `sslv3 alert handshake failure`, número 40.
- Certificado apresentado: nenhum.

### TLS 1.2 com lista local deliberadamente relaxada

Com `openssl s_client -tls1_2 -cipher 'ALL:@SECLEVEL=0'`, somente para diagnóstico, o endpoint completou:

- protocolo: TLS 1.2;
- cifra: `ADH-AES256-SHA256`;
- certificado do peer: ausente;
- chave temporária: DH 2048 bits.

Isso confirma que a porta não está simplesmente fechada, mas a configuração TLS oferecida é insegura/incompatível com clientes modernos.

Nenhum login, senha, auth key ou comando RouterOS foi enviado.

## Causa e hipóteses

Comprovado:

- rede e porta TCP alcançáveis;
- falha ocorre antes da autenticação RouterOS;
- TLS 1.2/1.3 normal não completa;
- endpoint não apresenta certificado de servidor;
- apenas cifra anônima legada permitiu handshake.

Causa mais provável:

- serviço `/ip service api-ssl` sem certificado TLS de servidor válido/atribuído; ou
- certificado configurado inválido/indisponível; ou
- NAT/proxy intermediário terminando ou alterando TLS de forma incorreta.

Ainda não distinguido sem leitura local do equipamento:

- erro diretamente no API-SSL RouterOS;
- certificado ausente no serviço;
- intermediário público encaminhando para o serviço errado;
- NAT para uma porta que não é o API-SSL esperado.

A hipótese de credencial incorreta está descartada para este erro específico, pois nenhum handshake TLS normal foi concluído e nenhum login foi tentado.

## Correção segura proposta — não executada

Primeiro, em uma sessão RouterOS local/autorizada, fazer somente a inspeção:

```routeros
/ip service print detail where name=api-ssl
/certificate print detail
/ip firewall nat print detail
```

Confirmar:

- `api-ssl` habilitado na porta 8729;
- certificado de servidor atribuído;
- certificado possui uso `tls-server`;
- chave privada correspondente está presente;
- o certificado cobre o IP público ou DNS utilizado pelo MCP;
- o NAT público encaminha 8729 para o mesmo serviço;
- não existe intermediário TLS inesperado.

Se não houver certificado válido, o ajuste proposto — ainda sujeito a autorização e revisão do RouterOS — é criar uma CA interna protegida, emitir um certificado de servidor com SAN correspondente ao nome/IP administrativo e atribuí-lo ao API-SSL:

```routeros
# PROPOSTA — NÃO EXECUTAR NESTA FASE
/certificate add name=redeti-ca common-name=REDETI-CA \
    key-usage=key-cert-sign,crl-sign days-valid=3650
/certificate sign redeti-ca name=redeti-ca
/certificate add name=rest-api common-name=<API_SSL_DNS_OR_IP> \
    key-usage=tls-server days-valid=825
/certificate sign rest-api ca=redeti-ca name=rest-api-signed
/ip service set [find name=api-ssl] \
    disabled=no port=8729 certificate=rest-api-signed \
    address=<TRUSTED_MANAGEMENT_CIDRS>
```

Os comandos acima criam/modificam configuração e não foram executados. O nome, SAN, validade, CA e CIDRs precisam ser revisados conforme a política real e a versão RouterOS.

Depois da correção, o MCP deve ser ajustado para:

- `ssl_verify=true`;
- `ssl_verify_hostname=true`;
- confiar explicitamente na CA aprovada, se o certificado for interno;
- usar nome DNS/IP que corresponda ao SAN;
- manter `use_ssl=true` e porta 8729;
- não habilitar API sem TLS;
- não usar `curl -k`, `verify=false` ou cifras anônimas.

Se o certificado for público e validável pelo trust store do Hermes, não será necessário distribuir uma CA interna. Se for interno/self-signed, a CA pública deve ser instalada no trust store protegido do cliente MCP, nunca desabilitando a validação.

## Testes pós-correção

Somente após autorização do ajuste no MikroTik:

1. `openssl s_client -connect <host>:8729 -tls1_2` deve apresentar certificado e uma cifra autenticada.
2. TLS 1.3 deve completar se suportado pelo RouterOS/configuração.
3. Nenhuma cifra `ADH` deve ser necessária.
4. Validar cadeia, SAN e hostname com verificação habilitada.
5. Executar o health read-only MCP.
6. Repetir inventário:
   - `/system/identity`;
   - `/system/resource`;
   - `/system/routerboard`;
   - `/interface`;
   - `/ip/address`;
   - `/ip/route`;
   - `/ip/firewall/filter`;
   - `/ip/firewall/nat`.
7. Confirmar que nenhum objeto foi alterado além do certificado/API-SSL autorizado.

## Segurança e impacto

Nesta etapa:

- MikroTik não modificado;
- nenhuma VPN alterada;
- nenhuma rota, firewall ou NAT alterado;
- API sem TLS não habilitada;
- nenhuma autenticação realizada;
- nenhuma chave real criada ou utilizada;
- nenhum segredo exposto;
- nenhum inventário RouterOS declarado como concluído.

## Resultado

`BLOCKED_ROUTEROS_CERTIFICATE_FIX_REQUIRED`

Próximo passo mínimo: uma sessão RouterOS autorizada deve inspecionar o certificado atribuído ao `api-ssl` e o NAT público. Após a correção segura do certificado, o cliente MCP poderá voltar a validar TLS normalmente e o inventário WG-1 poderá ser repetido.
