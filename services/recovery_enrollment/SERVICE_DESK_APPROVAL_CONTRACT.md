# Contrato de aprovação de VPN entre Service Desk e Hermes

**Estado:** servidor de verificação e canal UNIX **implementados com testes
isolados**; assinatura real no Service Desk e implantação Hermes **NÃO feitas**.
Issue: `paulodepaula/SO_SYSTEM_RECOVERY#1`.

## Fluxo autorizado

1. Recovery OS inicia sessão pendente no endpoint de bootstrap HTTPS. Exibe
   no LVGL apenas código de pareamento e validade; chave Tailscale jamais é
   mostrada ao técnico.
2. Técnico autenticado no **Service Desk** consulta sessões pendentes em UI
   interna (futuro). Antes de aprovar, verifica MFA, perfil **e permissão
   explícita** `RECOVERY_VPN_APPROVE`, vínculo da O.S. e autorização do
   atendimento. `GESTOR` ou `ADMIN` por si só **não** bastam no Service Desk.
3. O técnico confere o código de 8 dígitos que aparece no equipamento físico.
   O servidor do Service Desk gera uma afirmação curta, assinada com HMAC-SHA256.
4. O backend do Service Desk transmite a afirmação apenas pelo canal privado
   operacional para o broker Hermes; nunca ao navegador, à ISO ou ao cliente.
5. O broker verifica assinatura, expiração, audiência, sessão, código, papel,
   permissão e nonce ainda não utilizado. Em seguida aprova a sessão pendente.
6. Somente o Agent que abriu a sessão, com seu segredo efêmero próprio, poderá
   reclamar **uma** chave Tailscale de uso único, usando HTTPS autenticado.
   A chave OAuth administrativa permanece exclusivamente no Hermes.

## Contrato da afirmação assinada

Payload JSON canônico com campos **exatos**, sem propriedades adicionais:

```json
{
  "version": 1,
  "aud": "redeti-recovery-enrollment",
  "iss": "redeti-servicedesk",
  "sid": "SESSION_ID_GERADO_PELO_BROKER",
  "code": "12345678",
  "operator": "ID_INTERNO_AUTENTICADO",
  "role": "GESTOR",
  "permission": "RECOVERY_VPN_APPROVE",
  "os_id": "OS_42",
  "iat": 1700000000,
  "exp": 1700000060,
  "nonce": "TOKEN_RANDOMICO_BASE64URL_COM_32_BYTES"
}
```

- `code` contém oito dígitos e é fornecido pelo técnico após conferência
  física do equipamento, **não** pelo Agent como autorização.
- `operator` deve ser derivado da sessão autenticada do Service Desk, nunca
  de parâmetro livre enviado pelo browser. `os_id` deve ser consultado no
  backend e autorizado ao técnico.
- `role` permitido pelo verificador: `SUPER_ADMIN`, `ADMIN` ou `GESTOR`.
  Isso é uma **segunda defesa** e não substitui RBAC e escopo persistidos no
  Service Desk. O usuário `TECNICO` não aprova sessões nesta fase.
- `iat` é timestamp UNIX em segundos; `exp` deve estar no futuro, no máximo
  120 segundos após `iat`. A recomendação é validade de 60 segundos.
- `nonce` é aleatório, único por aprovação, base64url de pelo menos
  24 caracteres. Após verificação, fica consumido em memória mesmo quando
  o código informado não confere. Sem tentativas ilimitadas.
- Serialização de bytes JSON em UTF-8, sem sigilo no payload. Nunca colocar
  tokens Tailscale, credenciais de cliente ou dados de OS no payload.

`assertion = "v1." + BASE64URL_SEM_PADDING(json_bytes) + "." +
BASE64URL_SEM_PADDING(HMAC_SHA256(chave_compartilhada, bytes("v1."+payload)))`

A chave HMAC deve ter **32 bytes ou mais**, ser rotacionável e ficar somente
em segredo local protegido no Hermes e no backend do Service Desk. Nunca
armazenar a chave em GitHub, .env versionado, ISO, pendrive ou log.

## Canal administrativo Hermes

Arquivo do socket UNIX: nome sugerido `approval.sock`, criado pelo backend
num diretório **privado, já existente e pertencente ao usuário de serviço**,
com modo de diretório `0700` e socket `0600`.

Mensagem HTTP enviada **pelo socket UNIX**, não pela rede TCP:

```http
POST /v1/operator/sessions/<sid>/approve HTTP/1.1
Content-Type: application/json
Content-Length: ...

{"assertion":"v1.<json-base64url>.<hmac-base64url>"}
```

- Resposta `204`: aprovada; `403`: assinatura, sessão, código ou validade
  rejeitada; `404`: rota inválida. Sem dados secretos no retorno.
- Somente o serviço de integração autorizado deve conseguir abrir o socket.
  **Não montar indiscriminadamente** o socket em containers ou reverse
  proxies e não redirecionar `/v1/operator` ao público.
- O serviço HTTP de Agent (bootstrap/claim) continua separado e limitado a
  `127.0.0.1` no backend; o ingress HTTPS de campo ainda não foi implantado.
- Atualmente `create_operator_socket_server` é uma fábrica de servidor,
  não possui launcher, unidade systemd ou port TCP. O processo principal e
  guarda de segredos precisam ser desenhados antes do deploy.

## Restrições do Service Desk

No repositório `paulodepaula/ProjVsCode`, seguir `AGENTS.md`,
`.ai/WORKFLOW.md` e `.ai/CHANGE_LIMITS.md`:
branch `dev/ai-shared`, issue própria, coordenação de posse com Hermes,
revisão especial para autenticação/integração externa, sem mexer
`prisma/schema.prisma`, Docker/Cloudflare/credenciais sem aprovação
específica. `main` permanece estável; sem merge ou deploy automático.

No momento a issue #45 coordena o projeto de contratos e o limite de duas
issues ativas impede iniciar código concorrente de autenticação sem liberar
uma vaga e formalizar a posse. **Nada foi modificado em ProjVsCode.**

## Homologação ainda necessária

- Em ambiente de teste do Hermes, executar Socket + Broker + emissor fake
  para demonstrar aprovação fim a fim sem Tailscale real.
- Criar adaptador assinador no Service Desk após configurar permissão
  persistente ou utilizar autorização existente comprovada.
- Segredo compartilhado em gerenciador local/rotação, e usuários/OS reais
  validados do lado servidor; nunca confiar no frontend.
- Adicionar processos separados/isolamento, teste de restauração/restart,
  nonce store compartilhado para múltiplas instâncias e rate limits por usuário.
- HTTPS externo de bootstrap com identidade da sessão, proteção contra
  sequestro, antiabuso, TLS e observabilidade sanitizada.
- Testar integração Tailscale sem chave permanente e corrigir
  `Connection timed out during banner exchange` antes de UAT.
- Só depois gerar ISO LVGL e homologar em computadores físicos.

**Testes unitários não significam serviço implantado ou sistema homologado.**
