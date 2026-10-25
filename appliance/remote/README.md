# RedeTI Recovery OS — SSH local e VPN (v0.5.3)

## Como funciona

O usuário de suporte é **paulo**, nas duas modalidades. O boot inicia a interface gráfica DRM/KMS e dois serviços separados:

| Acesso | Serviço | Endereço | Autenticação |
|---|---|---|---|
| Rede local | OpenSSH dedicado | `paulo@IP_LOCAL:22` | Chave pública Ed25519, sem senha |
| VPN | Tailscale SSH | `paulo@IP_VPN:22` | Identidade e regras da tailnet |

A rede local **não depende da VPN**. O firewall permanece ativo (`nofirewall: false`) e permite conexões LAN somente pela interface física e sub-rede privada diretamente conectada (RFC1918). Não há publicação da porta 22 na internet, nem regra ampla `INPUT ACCEPT`. O OpenSSH padrão do SystemRescue fica mascarado; apenas a instância dedicada com configuração restritiva é iniciada.

A conta `paulo` não recebe senha e não possui `sudo` automático. Não é possível fazer SSH como `root`. O serviço abre a porta local quando a rede está disponível, mas **nenhum login será aceito até que uma chave pública seja provisionada**.

## 1. Provisionar a chave pública do SSH local

No computador de suporte (Windows/PowerShell), gere um par Ed25519 se ainda não tiver:

```powershell
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\redeti_recovery_ed25519" -C "redeti-recovery"
```

Guarde o arquivo **sem .pub** somente no computador confiável do técnico — ele é a chave privada. Copie exclusivamente o conteúdo de `redeti_recovery_ed25519.pub` para a partição de dados do pendrive Ventoy (FAT/exFAT, rótulo `Ventoy`), neste arquivo:

```text
REDETI/authorized_keys
```

Alternativamente, use um segundo pendrive FAT/exFAT com rótulo `REDETI_CFG`. O arquivo aceita até quatro linhas de chaves públicas `ssh-ed25519`, sem opções extras. O sistema localiza a partição pelo rótulo **e por ser USB**, monta-a em somente leitura, valida o arquivo e o copia para `/home/paulo/.ssh/authorized_keys` no sistema de recuperação temporário em RAM. Ele **não pesquisa nem monta os SSDs internos** para credenciais.

No boot sem chave, a Central RedeTI exibirá `SSH LAN: IP | aguardando chave publica`; basta inserir a mídia autorizada e o serviço tentará lê-la novamente. A rede VPN continua opcional.

## 2. Conectar por SSH local

Após a tela mostrar `SSH LAN: paulo@192.168.x.x`:

```powershell
ssh -i "$env:USERPROFILE\.ssh\redeti_recovery_ed25519" paulo@192.168.x.x
```

Substitua pelo **IP mostrado no painel**. O endereço deve ser acessível na mesma sub-rede local. Em QEMU com NAT e encaminhamento de porta de laboratório, use `ssh -p 2222 paulo@127.0.0.1`.

**Identidade do servidor:** o host SSH usa uma chave nova, gerada em `/run/redeti/ssh/` a cada boot; o fingerprint pode ser consultado localmente em `/run/redeti/ssh/host_fingerprint`. Como o fingerprint muda após reinicializações, confira-o por canal confiável antes de aceitar uma nova identidade. Não desative permanentemente a verificação de host SSH.

## 3. VPN Tailscale SSH (opcional)

Mantenha a tag **`tag:redeti-recovery`** na tailnet e restrinja o acesso a técnicos autorizados, somente como `paulo`.

Exemplo de regras conceituais a integrar às políticas existentes (substitua o endereço de exemplo pelo seu usuário autorizado; revise outras regras globais que possam ampliar o acesso):

```json
{
  "groups": {"group:recovery-admins": ["tecnico-autorizado@exemplo.com"]},
  "tagOwners": {"tag:redeti-recovery": ["group:recovery-admins"]},
  "grants": [{"src": ["group:recovery-admins"], "dst": ["tag:redeti-recovery"], "ip": ["tcp:22"]}],
  "ssh": [{
    "action": "check",
    "checkPeriod": "1h",
    "src": ["group:recovery-admins"],
    "dst": ["tag:redeti-recovery"],
    "users": ["paulo"]
  }]
}
```

Para conexão automática, gere uma chave de autenticação **efêmera**, com a tag, duração curta e preferência por uso único. Coloque **somente** a chave no pendrive FAT/exFAT autorizado:

```text
REDETI/ts-authkey
```

**Não publique ou envie esse segredo ao ChatGPT/GitHub.** A chave temporária é lida do USB e usada a partir de `/run`, sem ser embutida na ISO. Após o uso, remova o arquivo do pendrive e revogue a chave se necessário. A VPN mantém estado apenas na RAM, exigindo novo provisionamento após reinicialização.

Quando conectada:

```bash
ssh paulo@100.x.x.x
```

Tailscale SSH intercepta porta 22 **somente no endereço VPN**, sem impedir o SSH convencional no endereço LAN. Regras da tailnet são necessárias para autorizar o acesso.

## 4. Homologar com QEMU sem discos de clientes

A VM precisa ter rede, por exemplo NAT com encaminhamento somente para o loopback do host:

```powershell
& "C:\Program Files\qemu\qemu-system-x86_64.exe" `
  -machine q35,vmport=off -accel tcg -cpu max -m 3072 -smp 2 `
  -device virtio-vga -device qemu-xhci -device usb-tablet `
  -boot order=d -cdrom "D:\ISOs\RedeTI-Recovery-OS-appliance.iso" `
  -nic user,hostfwd=tcp:127.0.0.1:2222-:22
```

A chave pública deverá estar em um volume USB de laboratório visível para a VM; o QEMU com ISO CD-ROM isolada **não recebe automaticamente o pendrive físico**. Não passe discos de clientes para a VM. Para testar a VPN é necessário rede virtual, chave de laboratório e tailnet autorizada.

No terminal virtual da ISO, confira:

```bash
cat /run/redeti/lan-ssh-status.json
cat /run/redeti/remote-status.json
ss -lntp | grep ':22'
iptables -S REDETI_LAN_SSH
systemctl status redeti-lan-sshd --no-pager
```

Requisitos para aprovação: usuário `paulo` autentica na LAN com chave pública, senha e root são negados, rede externa não recebe conexões, Tailscale mantém as regras de ACL e o painel nativo continua funcionando sem rede.

**Estado de desenvolvimento:** scripts e testes de lógica foram adicionados; o boot com SSH LAN na ISO **ainda exige homologação real em QEMU** antes de uso em máquinas de clientes.
