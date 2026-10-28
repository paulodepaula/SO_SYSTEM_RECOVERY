# RedeTI Recovery OS — diagnóstico read-only do SSH pela VPN

**Estado:** verificador integrado ao *processo de construção da próxima ISO*.
Nenhuma nova ISO foi gerada, instalada ou testada em equipamento físico.
Não executar reparos de firewall, alterar ACLs ou habilitar Tailscale SSH
gerenciado apenas porque uma conexão TCP na porta 22 responde.

## Investigação da falha histórica

Durante o teste anterior, a VPN Tailscale recebeu IP 100.x e respondeu a
`tailscale ping`, e `Test-NetConnection -Port 22` conectou, mas o cliente
OpenSSH no Windows parou em `Connection timed out during banner exchange`.
Isso prova conexão TCP, **não** prova que um servidor SSH retornou sua linha
de identificação SSH-2.0 nem que a autenticação terminou.

O código atual suporta dois caminhos distintivos:

- `vpn_ssh_mode=disabled` (**native**): Tailscale funciona como VPN e o
  OpenSSH do Recovery OS precisa responder ao cliente com chave Ed25519
  autorizada. O banner `ssh-banner.txt` se aplica aqui.
- `vpn_ssh_mode=managed`: o `tailscaled` toma o TCP/22 da tailnet e
  aplica as regras próprias de Tailscale SSH, incluindo eventual `check`
  de reautenticação. O OpenSSH nativo continua na LAN. Seu banner estático
  não necessariamente aparece no acesso pela tailnet.

A seleção atual depende do marcador vazio `REDETI/tailscale-ssh.enable`
no Ventoy; para investigação, **preserve o estado original**. Não troque
modos ou desative a proteção da ACL antes de registrar evidências.

## Script somente leitura (próxima ISO)

Caminho no live system:

```bash
python3 /opt/redeti-appliance/remote/ssh-diagnose.py --read-only
```

O script imprime somente códigos de estado:

```text
vpn_state=connected
vpn_ssh_mode=native
lan_ssh_state=ready
sshd_port_22_listening=yes
local_ssh_identification=ssh_identification_ok
vpn_firewall=vpn_ssh_rule_present
native_ssh_banner=present
diagnostic_complete=read_only
```

As linhas acima são **exemplo**, não resultados observados em equipamento.
O teste somente abre conexão TCP **local** 127.0.0.1:22, verifica se o
servidor devolve identificação `SSH-2.0-` e consulta regras de iptables com
`iptables -S` (sem alteração). Com usuário `paulo` sem privilégios root,
a verificação do firewall e dos arquivos protegidos pode retornar
`unavailable`. Isso não comprova falha: use o console root de manutenção
somente se houver procedimento local autorizado.

**Não imprima** `/run/redeti/remote.log` nem cole resultados completos
de `tailscale status --json`: esses arquivos podem conter detalhes de rede
e autenticação. O script deliberadamente só divulga códigos fixos.

## Saída pública para o operador

O processo privilegiado também publica uma visão mínima em
`/run/redeti-status/vpn-status.json`, fora de `/run/redeti`. O diretório
privado continua `root:root` com `0700` e o socket administrativo não é
exposto ao usuário `paulo`. A saída pública não contém IP, token, auth key,
OAuth, URL de autenticação, log ou estado completo da tailnet.

Comando destinado à consulta SSH somente leitura:

```bash
redeti-status
```

Ele mostra somente `vpn_state`, `connectivity`, `failure_code`,
`registration_stage`, `vpn_ssh_mode` e o marcador fixo
`diagnostic_complete=read_only`. Os códigos `provisioning_*`,
`tag_authorization`, `authentication` e `connectivity*` distinguem falhas
somente quando a evidência local permite essa classificação; caso contrário,
é usado `registration_failed`.

## Teste do lado Windows (após uma nova conexão VPN autorizada)

1. Confirme o IP Tailscale da máquina em sua tela local (não use IP antigo).
2. Rode `tailscale ping <IP>` e depois
   `ssh -vvv -o ConnectTimeout=10 -o ConnectionAttempts=1 paulo@<IP>`.
3. Confirme o fingerprint mostrado no Recovery OS antes de aceitar a
   chave host; não desabilite `StrictHostKeyChecking`.
4. Se houver `Connection established.` seguido de timeout de banner,
   compare com o diagnóstico local: se o OpenSSH local responde, investigar
   Tailscale SSH gerenciado, ACL/check e regras de fluxo da tailnet.
5. Não publicar porta 22 na internet, não inserir `ACCEPT` amplo no
   firewall e não compartilhar chaves privadas no diagnóstico.

Não há conclusão causal definitiva sobre o timeout anterior sem evidências
da mesma inicialização nas duas pontas.

Referência: https://tailscale.com/docs/features/tailscale-ssh
