# RedeTI Recovery OS — Relatório SSH-4

- Etapa: `SSH-4 — investigação da rejeição da chave pública`
- Gerado em UTC: `2026-10-28T21:05:30Z`
- Projeto: `SO_SYSTEM_RECOVERY`
- Branch: `main`
- Base publicada investigada: `a266b181db485045746849715c576c412ec49daf`
- Estado: `LOCAL_FIX_PREPARED_PHYSICAL_EVIDENCE_REQUIRED`

## Sintoma confirmado

- TCP/22 do Recovery OS: alcançável.
- Host key ED25519: validada em momentos distintos conforme fingerprint apresentada pelo equipamento.
- Chave Hermes provisionada no Ventoy: válida e presente.
- Login `paulo` pelo Hermes: rejeitado com `Permission denied (publickey)`.
- Nenhum diagnóstico remoto foi executado porque a autenticação falhou.

## Causa encontrada no código

`appliance/remote/lan-start.sh` iniciava o SSH com `systemd-run` em modo bloqueante:

```text
systemd-run --quiet --collect --unit=redeti-lan-sshd ... sshd -D ...
```

O processamento de `REDETI/authorized_keys` ocorria somente depois dessa chamada, no loop iniciado por `key_loaded=false`. Como `sshd -D` permanece ativo, o shell não alcançava a rotina de provisionamento. Isso explica a porta 22 aberta com autenticação pública recusada.

## Correção preparada localmente

Alteração mínima local:

```text
systemd-run --quiet --no-block --collect --unit=redeti-lan-sshd ... sshd -D ...
```

Foi adicionada uma regressão em `appliance/tests/test_lan_ssh.py` que exige `--no-block` antes do loop de provisionamento.

A correção e o teste permanecem locais nesta etapa. Nenhum código foi publicado no GitHub, conforme a solicitação de publicar somente os relatórios sanitizados.

## Verificações locais

- Teste RED antes da correção: PASS como reprodução — a regressão falhou porque `--no-block` não existia.
- Teste GREEN da correção: PASS.
- Simulação de duas chaves Ed25519 distintas em `lan.py valid_keys/install-key`: PASS.
  - Duas entradas aceitas.
  - Comentários removidos do arquivo instalado.
  - Limite de quatro entradas preservado.
- Suíte completa:

```text
python3 -m unittest discover -s appliance/tests -v
```

Resultado: `166` testes aprovados, `0` falhas.

- Sintaxe `lan-start.sh`: PASS.
- `git diff --check`: PASS.
- Nenhuma ISO gerada.
- Nenhum QEMU executado.
- Nenhum Recovery OS físico, Ventoy, firewall, serviço ou disco de cliente alterado.

## Fluxo validado no código

- Fonte autorizada: partição USB removível com label `Ventoy` ou `REDETI_CFG`.
- Filesystems aceitos: `exfat` e `vfat`.
- Mapeamentos Ventoy só são aceitos quando o sysfs confirma o mesmo dispositivo USB.
- Arquivo lido: `REDETI/authorized_keys`.
- Destino instalado: `/home/paulo/.ssh/authorized_keys`.
- `AuthorizedKeysFile`: `/home/paulo/.ssh/authorized_keys`.
- OpenSSH: usuário `paulo`, somente chave pública, sem root e sem senha.
- Permissões aplicadas no destino: diretório `0700`, arquivo `0600`, proprietário `paulo:paulo`.
- Validador: somente chaves `ssh-ed25519`, de uma a quatro entradas, sem opções de `authorized_keys`.

## Evidência ainda necessária no equipamento físico

Como a autenticação não foi possível, estes comandos read-only devem ser executados localmente no Recovery OS, em console físico ou após uma sessão autorizada:

```bash
findmnt -rn -S /dev/sda1 -o SOURCE,FSTYPE,OPTIONS,TARGET
lsblk -o NAME,TYPE,SIZE,TRAN,FSTYPE,LABEL,MOUNTPOINTS
stat -c '%A %a %U:%G %s %n' /home/paulo/.ssh /home/paulo/.ssh/authorized_keys
sha256sum /home/paulo/.ssh/authorized_keys
/usr/bin/sshd -T -f /opt/redeti-appliance/remote/sshd_config | grep -E 'authorizedkeysfile|allowusers|pubkeyauthentication|passwordauthentication|authenticationmethods|strictmodes'
systemctl status redeti-lan-sshd --no-pager
journalctl -b -u redeti-lan-sshd --no-pager -n 120
ip -brief address
redeti-status
```

Para conferir fingerprints sem publicar chaves:

```bash
while read -r type key _; do
  printf '%s %s\n' "$type" "$key" | ssh-keygen -lf - -E sha256
done < /home/paulo/.ssh/authorized_keys
```

## Próxima etapa

A correção exige nova ISO para chegar ao Recovery OS físico. A geração da ISO e qualquer homologação física permanecem bloqueadas até autorização específica.

`PHYSICAL_SSH_TEST: BLOCKED_PENDING_NEW_ISO_AND_PHYSICAL_EVIDENCE`
