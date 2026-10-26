# RedeTI Recovery OS — VPN privada, provisionamento seguro e homologacao

Escopo: SystemRescue + LVGL/DRM/EVDEV, sem X11, navegador, servidor HTTP,
webapp, acesso remoto publico ou gravacao nos discos do cliente.

## Modelo adotado

- SSH local **ja homologado**: usuario fixo `paulo`, somente chaves publicas
  Ed25519 de `REDETI/authorized_keys`, sem senha/root.
- A VPN Tailscale fornece **transporte WireGuard privado**. Por padrao
  Tailscale SSH fica desligado, mantendo OpenSSH + Ed25519 na LAN e na VPN.
- **Apos revisar ACLs**, o tecnico pode ativar o Tailscale SSH gerenciado com
  um arquivo vazio `REDETI/tailscale-ssh.enable` no mesmo USB Ventoy confiavel.
  Nesse modo, somente as conexoes pela tailnet usam as identidades de
  host e a autenticacao gerenciadas pelo Tailscale. Isso evita registros
  manuais de chaves de host a cada boot *via VPN*, enquanto o SSH LAN continua
  independente, exigindo Ed25519 e verificacao de host.
- Nao ativar Tailscale SSH se a politica SSH do tailnet permitir `root`,
  outras contas ou operadores nao autorizados. A diretiva OpenSSH
  `PermitRootLogin no` nao controla o servidor embutido do Tailscale.
  Usar regras especificas para `tag:redeti-recovery`, usuario `paulo`,
  e opcionalmente reautenticacao `check` com SSO.
- `tailscaled --state=mem:` nao grava identidade do cliente em disco. A cada
  reinicio, cria-se uma identidade temporaria nova; um token **one-off** sera
  necessario para um boot futuro. Tags e permissões devem ser revisadas no
  console administrativo do Tailscale.
- Nao anunciar subnets/exit node nem aceitar rotas/DNS externos. O firewall
  local, instalado **antes do Tailscale iniciar**, aceita apenas TCP/22 vindo
  de `tailscale0` ao IP do proprio Recovery OS; bloqueia outros serviços
  pela VPN e conexões novas iniciadas do Recovery para outros nos da tailnet.
- Tailscale `--netfilter-mode=off` impede que regras automaticas sobreponham
  a politica restritiva. Nao ha roteamento/VPN bridge para discos do cliente.
- VNC no futuro: somente loopback + tunel SSH restrito. **Nao implementado
  nesta etapa**; `AllowTcpForwarding no` permanece habilitado.

## Antes de iniciar uma VPN

1. No Tailscale Admin Console, **substituir** regras amplas `* -> *` por
   politicas de menor privilegio. Nao basta acrescentar uma grant restrita
   se outra regra concede acesso amplo.
2. Criar/autorizar a tag `tag:redeti-recovery` e conceder aos **dispositivos
   ou identidades dos tecnicos** apenas acesso TCP/22 a essa tag.
   O tecnico deve ter Tailscale autenticado no proprio Windows.
3. Gerar **fora do GitHub e desta conversa** uma auth key temporaria para
   a tag: preferir **one-off + ephemeral + expiracao curta**. Tokens reutilizaveis
   sao mais praticos para multiplos boots, mas aumentam o risco caso o
   pendrive seja perdido. Nunca usar um token de longa duracao.
4. No pendrive principal Ventoy (exFAT, rotulo `Ventoy`), preparar:
   `REDETI/authorized_keys` (chaves publicas existentes) e
   `REDETI/ts-authkey` (a chave temporaria em uma unica linha ASCII).
   **A chave privada Ed25519 permanece exclusivamente no computador do tecnico.**
   Nao enviar o conteudo de `ts-authkey` aqui, a GitHub issues, logs
   ou capturas de tela.
5. Se desejar a identidade SSH gerenciada na VPN, **somente apos
   limitar as regras `ssh` e grants no Tailscale Admin Console**, criar
   `REDETI/tailscale-ssh.enable` como arquivo vazio (zero bytes). O codigo
   recusa arquivo simbolico ou com conteudo. Sem esse arquivo, a autenticacao
   permanece exclusivamente via Ed25519, mesmo na VPN. Nunca incluir tokens
   ou identidades privadas nesse marcador.
6. Ejetar com seguranca, iniciar Recovery OS e verificar no dashboard
   `VPN conectada` e endereco `100.x.x.x`. Caso falhe, consultar o estado
   da VPN; nunca publicar a chave, nem ligar roteamento de portas.
7. Apos sucesso, remover `REDETI/ts-authkey` do pendrive em um Windows
   confiavel e revogar a chave no Tailscale Admin Console. Revogacao da
   auth key nao encerra a sessao ja criada: se necessario, remover tambem
   o no temporario em Machines.
8. A partir do computador tecnico ja na mesma tailnet, testar em
   **outra rede** (por exemplo, hotspot) usando o IP exibido:
   `ssh -o IdentitiesOnly=yes -i <chave-privada-local> paulo@100.x.y.z`.
   Se Tailscale SSH gerenciado estiver habilitado e autorizado na policy,
   conectar via `tailscale ssh paulo@<nome-ou-ip-tailnet>`; a distribuicao
   de host keys usa a identidade da tailnet. No SSH convencional (LAN ou VPN
   sem marcador), conferir a fingerprint exibida no painel e no Windows
   antes de aceitar uma nova host key.

## Diagnostico de estado (sem dados secretos)

Em `/run/redeti/remote-status.json`:
- `awaiting_provision`: pendrive nao contem chave VPN acessivel;
- `invalid_auth_key`: o token nao atende ao formato exigido;
- `connecting`: registrando o no temporario;
- `vpn_auth_failed`: token expirou, tag nao autorizada, ACL ou rede;
- `firewall_blocked` / `firewall_unverified`: VPN nao validada como segura;
- `connected`: rede privada conectada, com IP exibido; **nao prova login SSH**.

A tela `Rede | Diagnostico SSH e VPN` mostra apenas estado e IP privado;
nenhum segredo e exibido. Logs, status, chaves de host em RAM e autenticação
temporaria ficam em `/run/redeti/`.

## Portoes de homologacao

1. Codigo + testes Python, shell syntax, compilacao C/CTest, manifest da ISO.
2. Boot QEMU isolado sem dispositivos fisicos, confirmar nao regressao LVGL.
3. Equipamento fisico sem dados sensiveis: LAN SSH segue funcionando.
4. Auth key temporaria carregada do Ventoy; VPN mostra `connected`.
5. Testar **outra rede**, sem encaminhar TCP/22 no roteador do cliente.
6. Login como `paulo` usando a mesma chave Ed25519, sem senha; observar
   conectividade sem VNC/HTTP/portas adicionais abertas.
7. Revogar token e registrar somente versao, build, commit, resultado e
   eventuais erros sem copiar credenciais ou informações dos clientes.

Nao apagar ISO anterior antes de aprovar os itens acima. Codigo na main ou
CI verde nao equivale a VPN homologada no equipamento fisico.

## Por que o erro de known_hosts se repete na LAN?

O servidor OpenSSH gera host key temporaria em `/run/redeti/ssh` em cada
boot, para nao gravar segredos em disco do cliente, ISO ou Ventoy exFAT.
Por isso conexoes repetidas a `192.168.x.x` exigem validacao de fingerprint
quando a chave muda. **Nao** usar `StrictHostKeyChecking=no` nem copiar a mesma
chave privada de host para varias maquinas. Para LAN persistente entre boots,
sera preciso uma solucao de SSH host CA com assinatura confiavel, ou armazenamento
protegido por equipamento, a ser implementada e homologada separadamente.

Tailscale SSH usa autenticacao baseada em identidade do tailnet (nao no
`authorized_keys` do OpenSSH). Somente habilitar com politica SSH propria e
usuarios de origem restritos. As regras OpenSSH de usuario `paulo` e
`PermitRootLogin no` continuam valendo exclusivamente no SSH da LAN.
