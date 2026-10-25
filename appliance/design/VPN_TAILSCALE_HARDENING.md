# RedeTI Recovery OS — VPN privada, provisionamento seguro e homologacao

Escopo: SystemRescue + LVGL/DRM/EVDEV, sem X11, navegador, servidor HTTP,
webapp, acesso remoto publico ou gravacao nos discos do cliente.

## Modelo adotado

- SSH local **ja homologado**: usuario fixo `paulo`, somente chaves publicas
  Ed25519 de `REDETI/authorized_keys`, sem senha/root.
- A VPN Tailscale fornece **transporte WireGuard privado**, nao uma segunda
  autenticacao SSH. `--ssh=false` conserva o OpenSSH protegido e a mesma chave
  de administrador para LAN e rede externa.
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
5. Ejetar com seguranca, iniciar Recovery OS e verificar no dashboard
   `VPN conectada` e endereco `100.x.x.x`. Caso falhe, consultar o estado
   da VPN; nunca publicar a chave, nem ligar roteamento de portas.
6. Apos sucesso, remover `REDETI/ts-authkey` do pendrive em um Windows
   confiavel e revogar a chave no Tailscale Admin Console. Revogacao da
   auth key nao encerra a sessao ja criada: se necessario, remover tambem
   o no temporario em Machines.
7. A partir do computador tecnico ja na mesma tailnet, testar em
   **outra rede** (por exemplo, hotspot) usando o IP exibido:
   `ssh -o IdentitiesOnly=yes -i <chave-privada-local> paulo@100.x.y.z`.
   Antes do aceite de nova host key, comparar a fingerprint SSH mostrada
   no painel do Recovery OS por canal confiavel.

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
