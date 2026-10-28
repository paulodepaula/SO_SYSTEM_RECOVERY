# RedeTI — Relatório WG-3: preparação da correção TLS

- Etapa: `WG-3 — preparação da correção TLS da API-SSL`
- Gerado em UTC: `2026-10-28T21:33:00Z`
- Projeto: `SO_SYSTEM_RECOVERY`
- Perfil: `cidade-verde`
- Estado: `BLOCKED_PENDING_ROUTEROS_READONLY_OUTPUTS`

## Escopo executado

Somente análise e planejamento. Não houve alteração no MikroTik, no conector MCP, em VPNs, firewall, NAT, rotas ou serviços.

Os outputs read-only de:

```routeros
/ip service print detail where name=api-ssl
/certificate print detail
/ip firewall nat print detail
```

ainda não foram disponibilizados. Portanto, não é possível afirmar se o certificado está ausente, inválido, não atribuído ou se existe um intermediário/NAT apontando para outro serviço.

## Evidência WG-2 preservada

- TCP/8729 alcançável.
- TLS 1.2 normal falha com alerta remoto 40.
- TLS 1.3 falha.
- TLS só completou com `ADH-AES256-SHA256` usando política local deliberadamente insegura.
- Nenhum certificado de peer foi apresentado.
- Nenhuma autenticação RouterOS ocorreu.

A correção não deve aceitar cifras anônimas nem usar `verify=false` como solução.

## Inspeção read-only necessária

Executar em sessão RouterOS autorizada e retornar somente os campos sanitizados:

```routeros
/ip service print detail where name=api-ssl
/certificate print detail
/ip firewall nat print detail
```

Sanitizar:

- identidade e estado do serviço;
- porta e endereço permitido do `api-ssl`;
- nome do certificado atribuído;
- validade, `common-name`, SAN, key-usage e presença de chave privada;
- regra NAT correspondente, sem export completo;
- não retornar private-key, senha, PSK, tokens ou export sensível.

O objetivo é distinguir:

1. `api-ssl` sem certificado;
2. certificado sem `tls-server` ou expirado;
3. certificado atribuído sem chave correspondente;
4. NAT encaminhando para destino/porta errados;
5. outro equipamento terminando TLS;
6. certificado correto, mas incompatibilidade posterior do cliente MCP.

## Configuração MCP analisada

O conector `/home/paulo/hermes_mcp/mcp_tools/mikrotik_server.py`:

- resolve o perfil somente por `credential_id`;
- não imprime credenciais;
- usa `use_ssl` e porta do metadata;
- passa `ssl_verify` e `ssl_verify_hostname` como booleanos;
- usa `plaintext_login` somente no login RouterOS após TLS;
- não possui configuração de CA customizada no código atual.

O perfil atual tem `ssl_verify=false` e `ssl_verify_hostname=false`. Isso deve ser tratado como dívida de segurança, não como correção permanente.

O pacote `routeros_api` não está instalado no ambiente de shell deste checkout, portanto sua assinatura efetiva e suporte a `cafile`/`SSLContext` ainda precisam ser confirmados no ambiente do servidor MCP antes de qualquer patch.

## Correção de certificado proposta — não executar ainda

### Opção preferencial: certificado emitido por CA confiável

Usar certificado para o hostname DNS administrativo do MikroTik, com SAN compatível com o hostname usado pelo MCP. Essa opção evita instalar uma CA privada no Hermes, desde que a cadeia seja pública e adequada ao uso administrativo.

### Opção controlada: CA interna REDETI

Se for usada CA interna, a chave privada da CA deve permanecer protegida e fora do Git/chat. O RouterOS pode criar uma CA local e um certificado de servidor, conforme a versão e a política aprovadas:

```routeros
# PROPOSTA — NÃO EXECUTAR NESTA FASE
/certificate add name=redeti-ca common-name=REDETI-CA \
    key-usage=key-cert-sign,crl-sign days-valid=3650
/certificate sign redeti-ca name=redeti-ca
/certificate add name=rest-api common-name=<API_SSL_DNS> \
    subject-alt-name=DNS:<API_SSL_DNS>,IP:<API_SSL_IP> \
    key-usage=tls-server days-valid=825
/certificate sign rest-api ca=redeti-ca name=rest-api-signed
/ip service set [find name=api-ssl] \
    disabled=no port=8729 certificate=rest-api-signed \
    address=<AUTHORIZED_API_CIDRS>
```

Os comandos são apenas proposta. Não devem ser executados antes de confirmar o estado atual, evitar certificados duplicados e revisar a sintaxe/recursos da versão RouterOS efetiva.

Se já existir um certificado correto, o ajuste deve apenas atribuí-lo ao `api-ssl`, sem criar uma segunda CA.

## Distribuição segura da CA

Se a CA interna for escolhida:

1. Exportar somente o certificado público da CA, nunca a chave privada.
2. Transferir a CA por canal administrativo protegido.
3. Instalar a CA no trust store privado do ambiente MCP, com proprietário root e permissões restritas.
4. Configurar o conector para validação de cadeia e hostname.
5. Nunca usar `ssl_verify=false`, `ssl_verify_hostname=false`, `curl -k` ou ignorar erros de SAN.
6. Testar com `openssl s_client -CAfile <CA_PUBLICA>` antes do MCP.
7. Confirmar que o hostname utilizado corresponde ao SAN, não somente ao Common Name.

O conector atual não expõe um campo `ca_file`/`SSLContext`. Antes de alterar o código, é necessário confirmar a versão do `routeros_api` no venv do servidor MCP e sua API de validação. Se a biblioteca não aceitar CA customizada, preparar extensão mínima que:

- aceite metadata não secreta `ca_file` ou `ca_bundle_id`;
- construa um contexto TLS verificado;
- valide cadeia e hostname;
- rejeite caminhos fora do trust store aprovado;
- preserve `use_ssl=true`;
- teste a falha fechada para certificado ausente, SAN divergente e CA desconhecida.

Nenhum patch foi aplicado nesta etapa.

## Restrição de acesso à API-SSL

Após confirmar o serviço e antes de produção:

- manter `api-ssl` somente em 8729;
- restringir `address=` a origens administrativas autorizadas, quando aplicável;
- validar o filtro `input` existente antes de inserir regras;
- não abrir API-SSL para a Internet inteira;
- não habilitar API sem TLS;
- não modificar NAT existente sem autorização específica;
- se houver NAT público, permitir somente a origem administrativa aprovada e encaminhar para o destino correto;
- registrar comentários claros e não alterar regras de VPN existentes.

Qualquer mudança de firewall/NAT exige inventário, backup e autorização separados deste estudo.

## Backup e implantação futura

Antes de qualquer escrita, em janela autorizada:

1. Confirmar identidade e conexão alternativa do MikroTik.
2. Criar backup binário protegido e export sanitizado local.
3. Registrar o estado atual do serviço, certificado, NAT e filtros.
4. Validar o certificado/cadeia fora do MikroTik.
5. Aplicar somente a atribuição/correção de certificado necessária.
6. Ler novamente `/ip service`, `/certificate` e NAT.
7. Testar TLS 1.2 e, se suportado, TLS 1.3.
8. Só depois habilitar validação estrita no MCP.
9. Repetir o inventário WG-1 read-only.

O backup binário não deve ser publicado. O export para Git, se autorizado, deve ser sanitizado e não conter private keys, PSKs, senhas, tokens ou segredos.

## Rollback futuro

Se a validação falhar:

1. interromper novos testes;
2. restaurar o certificado anterior atribuído ao `api-ssl`, se confirmado no baseline;
3. restaurar o endereço permitido anterior do serviço;
4. reverter somente regras novas autorizadas, se alguma tiver sido criada;
5. revalidar acesso administrativo e VPNs existentes;
6. restaurar backup apenas conforme procedimento aprovado;
7. repetir o teste TLS sem desabilitar validação.

Não reiniciar o equipamento como primeira tentativa e não desabilitar firewall/API-SSL para “testar”.

## Riscos

- Corrigir apenas o cliente sem corrigir o servidor manterá o endpoint inseguro.
- Corrigir o certificado sem confirmar NAT pode alterar o equipamento errado.
- SAN incompatível fará o MCP rejeitar corretamente o certificado.
- CA interna distribuída incorretamente pode causar indisponibilidade ou incentivar `verify=false`.
- Perfil do cofre está marcado como `full`; futuras escritas exigem credencial RouterOS dedicada e least privilege.
- Mudanças em `address=` ou firewall podem bloquear a administração se a origem autorizada estiver errada.
- Criar CA/certificado duplicado sem inventário pode deixar certificados órfãos e dificultar rollback.

## Resultado

`BLOCKED_PENDING_ROUTEROS_READONLY_OUTPUTS`

Próximo passo: disponibilizar os três outputs RouterOS sanitizados. Depois disso será possível escolher entre atribuir um certificado existente, emitir um novo certificado compatível ou investigar NAT/intermediário, sempre mantendo as VPNs e serviços atuais intactos.
