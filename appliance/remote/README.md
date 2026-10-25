# RedeTI Recovery OS — VPN + SSH de suporte

Esta versão usa **Tailscale SSH** (servidor SSH embutido no próprio Tailscale), que só aceita tráfego da tailnet autorizado por políticas. **Não usa SSH convencional no endereço LAN**; a imagem mascara `sshd.service`. O usuário Linux de suporte é **`redeti`**, sem senha, sem `sudo` automático e sem acesso root. O acesso não modifica os discos por padrão, mas uma sessão remota é um canal administrativo e deve ser usada somente com autorização do proprietário do equipamento.

## Preparação da tailnet — uma única vez

1. Instale Tailscale no computador do técnico e entre na tailnet autorizada da RedeTI.
2. No console da Tailscale, crie a tag **`tag:redeti-recovery`** e uma política de rede/SSH que permita exclusivamente aos administradores de suporte autorizados conectar a essa tag na porta TCP/22 e como usuário **`redeti`**. Não permita `root` como usuário SSH e não conceda acesso amplo aos demais computadores da tailnet.
3. Em **Settings → Keys**, gere uma **auth key efêmera** com esta tag; dê preferência a chave de uso único, curta validade e aprovação restrita. Um boot consome uma auth key de uso único; para reiniciar e reconectar automaticamente será necessária nova chave, pois o estado da VPN é mantido em RAM.
4. **Não envie a chave ao ChatGPT, GitHub, logs, tickets ou capturas de tela.** A chave deve ser criada e controlada pela equipe autorizada. Revogue-a após uso e remova o dispositivo da tailnet se houver perda do pendrive.

Referências: https://tailscale.com/docs/features/tailscale-ssh · https://tailscale.com/docs/features/access-control/auth-keys · https://tailscale.com/docs/features/ephemeral-nodes

### Modelo de política de acesso (ajustar à tailnet existente)

Exemplo conceitual para o editor de políticas Tailscale, **substituindo o e-mail por uma identidade real autorizada** e mesclando as regras com a política existente, sem eliminá-la:

```json
{
  "groups": {
    "group:recovery-admins": ["tecnico-autorizado@exemplo.com"]
  },
  "tagOwners": {
    "tag:redeti-recovery": ["group:recovery-admins"]
  },
  "grants": [
    {
      "src": ["group:recovery-admins"],
      "dst": ["tag:redeti-recovery"],
      "ip": ["tcp:22"]
    }
  ],
  "ssh": [
    {
      "action": "check",
      "checkPeriod": "1h",
      "src": ["group:recovery-admins"],
      "dst": ["tag:redeti-recovery"],
      "users": ["redeti"]
    }
  ]
}
```

As permissões são **aditivas**: se sua tailnet possui um `grants` amplo que libera `*` para `*`, é preciso revisar essa regra também para que o acesso permaneça restrito. Nunca conceda `users: ["root"]` ou `autogroup:nonroot` aos computadores Recovery. O exemplo não é uma alteração automática da tailnet.

## Provisionamento do pendrive (sem gravar no SSD do cliente)

Use a **partição de dados exFAT/FAT do Ventoy** com rótulo `Ventoy`, ou outro **pendrive separado** FAT/exFAT com rótulo `REDETI_CFG`. O sistema **não monta partições internas** para buscar as credenciais; e não busca em NTFS para evitar confundir um volume Windows com o dispositivo de suporte.

No pendrive autorizado crie o caminho:

```text
REDETI/ts-authkey
```

Conteúdo: **somente uma chave de autenticação Tailscale** válida no formato `tskey-auth-...`, sem aspas e sem espaços extras. Não copie a chave para a ISO. O Linux monta a partição USB em somente leitura, copia a chave para um arquivo temporário com permissões `0600` sob `/run/redeti` (RAM), desmonta o pendrive e usa o parâmetro `--auth-key=file:` do Tailscale, que evita colocar o segredo na linha de comando.

**Atenção:** o arquivo continua no pendrive enquanto não for removido pelo operador. USB/FAT/exFAT não criptografam esse segredo; não deixe credenciais reutilizáveis armazenadas em pendrives de campo. Depois do primeiro boot de uma chave de uso único, remova o arquivo do pendrive em um equipamento confiável; revogue a chave no console. Para múltiplos boots, gere e provisione uma nova chave.

## Comportamento ao iniciar

- O painel RedeTI abre normalmente, mesmo **sem rede** e **sem credencial**.
- A ISO cria o usuário `redeti` bloqueado para login por senha; desativa o `sshd` convencional.
- Se detectar exatamente um pendrive/partição de provisionamento autorizado, inicia um nó Tailscale com `--state=mem:` (sem chaves ou estado em SSD), anuncia `tag:redeti-recovery`, ativa **Tailscale SSH** e mostra o IP 100.x no próprio painel.
- Se a chave for inválida, expirada, ausente, ou a tailnet não permitir SSH, permanece sem acesso remoto. O painel exibe o estado e continua a diagnosticar localmente.
- Não expõe sub-redes do cliente, não aceita rotas externas nem opera como exit node.

No computador autorizado, depois que o painel mostrar `VPN: conectada | SSH: redeti@100.x.x.x`:

```bash
ssh redeti@100.x.x.x
```

O computador do técnico precisa estar na mesma tailnet e a política da VPN deve conceder tanto acesso de rede (TCP 22) como permissão Tailscale SSH para o usuário `redeti`. Em caso de dúvida, consulte o estado e as políticas em https://login.tailscale.com/admin/machines e Access controls. Este SSH não dá `sudo` automaticamente.

## Homologação segura

Teste primeiro em QEMU com rede e **somente dispositivos virtuais descartáveis**, sem mapear discos de clientes e com uma tailnet de laboratório isolada. Com `-nic none`, a interface local continuará funcionando, mas o acesso VPN estará indisponível (comportamento esperado). Depois valide com pendrive de laboratório e autenticação efêmera; verifique que o SSH não responde pelo IP LAN e que só um computador autorizado da tailnet consegue conectar. Acesso remoto **ainda não homologado** em hardware físico.

A integração não inclui uma chave real e não registra Tailscale em nome do usuário automaticamente sem provisionamento. No Hermes, o builder baixa apenas as ferramentas estáticas da Tailscale; o credenciamento ocorre exclusivamente após o boot no laboratório.
