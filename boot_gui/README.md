# RedeTI Recovery OS — Central gráfica bootável (v0.4-alpha)

**Objetivo do produto:** Ventoy → escolher RedeTI-Recovery-OS.iso → ambiente gráfico XFCE → painel RedeTI aberto automaticamente. O técnico não precisa usar terminal para descobrir disco, processador, RAM ou modo UEFI/Legacy.

## O que a interface faz

Ao abrir, consulta (sem escrever em disco):
- modelo de CPU e contagem de processadores lógicos (Linux /proc/cpuinfo);
- memória RAM instalada (Linux /proc/meminfo);
- modo de boot do **Recovery OS** por /sys/firmware/efi;
- SSDs/HDs internos, dispositivos USB/Ventoy, tamanho, esquema de partições e volumes via lsblk;
- indica o **possível disco do Windows** apenas quando há um único disco interno, e o rotula como não comprovado.

Abaixo, lista módulos de diagnóstico. Inventário apresenta as partições detectadas. SMART só consulta indicadores em leitura após o clique do técnico, quando há exatamente um disco interno. EFI/BCD, integridade Windows, registro/drivers e laudo ainda estão desabilitados como **Em desenvolvimento**.

## Segurança e limites

Não monta partições, não edita BCD, não executa CHKDSK/SFC/DISM, não escreve arquivos no SSD, não automatiza reparos. Interface local (127.0.0.1), sem painel remoto. Não identifica a integridade de um Windows instalado; reconhecer NTFS não demonstra que o computador é inicializável. O tipo UEFI/Legacy refere-se à sessão de boot do Recovery OS, não necessariamente do sistema instalado. Trate a primeira ISO como **laboratório**, nunca como ferramenta homologada para dados reais de clientes.

## Prévia em Linux (sem acesso a hardware)

```bash
python3 boot_gui/app/server.py
# Abra http://127.0.0.1:8765 no navegador do ambiente de desenvolvimento
```

Sem `--live`, a página mostra dados fictícios e banner **DEMONSTRAÇÃO**.

Testes isolados:
```bash
python3 -m unittest discover -s boot_gui/tests -v
```


## Compilacao local no Hermes-server (recomendada)

O Hermes pode gerar e atualizar a ISO localmente. **Nao ha necessidade de baixar o artefato grande do GitHub Actions em cada alteracao.** Reutilize a imagem original `systemrescue-13.02-amd64.iso` obtida uma vez, inclusive copiando-a da particao de dados do Ventoy (sem alterar o pendrive). O script atual exige exatamente esta versao e valida seu SHA-256 oficial.

Primeira preparacao, no Ubuntu 24.04 do Hermes:

```bash
sudo apt update
sudo apt install -y git curl ca-certificates xorriso squashfs-tools
sudo curl -fL "https://gitlab.com/systemrescue/systemrescue-sources/-/raw/main/airootfs/usr/share/sysrescue/bin/sysrescue-customize?inline=false" -o /usr/local/bin/sysrescue-customize
sudo chmod 755 /usr/local/bin/sysrescue-customize
mkdir -p "$HOME/RecoveryOS/base" "$HOME/RecoveryOS/out"
git clone https://github.com/paulodepaula/SO_SYSTEM_RECOVERY.git "$HOME/RecoveryOS/SO_SYSTEM_RECOVERY"
```

Copie a ISO-base **uma unica vez** do seu Ventoy (usando um gerenciador de arquivos na sua maquina ou transferencia local segura) para:

```text
~/RecoveryOS/base/systemrescue-13.02-amd64.iso
```

No Hermes, para gerar a ISO pela primeira vez:

```bash
cd "$HOME/RecoveryOS/SO_SYSTEM_RECOVERY"
bash boot_gui/build/build-local.sh "$HOME/RecoveryOS/base/systemrescue-13.02-amd64.iso"
```

A cada atualizacao do codigo:

```bash
cd "$HOME/RecoveryOS/SO_SYSTEM_RECOVERY"
git pull --ff-only
bash boot_gui/build/build-local.sh "$HOME/RecoveryOS/base/systemrescue-13.02-amd64.iso"
```

Saida: `~/RecoveryOS/out/RedeTI-Recovery-OS-alpha-<data>.iso` e seu `.sha256`. O script verifica a integridade da ISO original, recusa sobrescrever arquivos existentes e confere a estrutura da nova ISO. **Nao utiliza comandos `dd`, formata discos nem instala nada no SSD analisado.** A recompilacao consome espaco em disco local e ainda deve ser testada em QEMU antes de ser utilizada no Ventoy. O SystemRescue permite construir em Linux e tambem em WSL, com as dependencias adequadas.

Nota: `sysrescue-customize` e obtido da fonte oficial e executa codigo no host; revise a origem antes de instalar. Esta instalacao inicial exige internet para os pacotes e um script pequeno. O download de mais de 1 GB da ISO-base e necessario apenas se voce ainda nao possui uma copia verificavel.

## Criar a ISO própria a partir do SystemRescue

O SystemRescue suporta personalização da ISO com `sysrescue-customize`, inclusão de arquivos usando um módulo **SRM**, inicialização automática de interface gráfica via `dostartx` e `gui_autostart`. Referências oficiais:
- https://www.system-rescue.org/scripts/sysrescue-customize/
- https://www.system-rescue.org/manual/Configuring_SystemRescue/
- https://www.system-rescue.org/manual/gui_autostart_Start_programs_on_graphical_desktop/
- https://www.system-rescue.org/Modules/

Em uma máquina Linux independente para **compilação**, obtenha ISO oficial do SystemRescue e instale `xorriso`, `squashfs-tools` e o script oficial `sysrescue-customize` confiável. Depois, na raiz deste repositório:

```bash
bash boot_gui/build/compose_iso.sh /caminho/systemrescue-13.02-amd64.iso /saida/RedeTI-Recovery-OS-alpha.iso
```

O script recusa sobrescrever a ISO de origem ou o destino já existente. A receita está em `boot_gui/recipe/` e integra todo o aplicativo em `/opt/redeti-recovery/` da mídia, iniciando sua interface gráfica com Firefox. A primeira ISO **foi gerada pelo GitHub Actions** com a base oficial 13.02 e o SHA-256 original validado. A inicialização gráfica no QEMU está em teste separado; a criação do arquivo ISO não representa homologação de boot.

Depois de construída, teste a ISO em QEMU/VM com disco virtual descartável e, somente se homologada, copie a ISO para a partição de dados do seu Ventoy e inicialize. Não formate nem altere a instalação atual do Ventoy.


## Primeira ISO experimental gerada (24/10/2026)

Build bem-sucedido: https://github.com/paulodepaula/SO_SYSTEM_RECOVERY/actions/runs/40135166088

- Artefato: `RedeTI-Recovery-OS-alpha-ISO`, que contém `RedeTI-Recovery-OS-alpha.iso` e `RedeTI-Recovery-OS-alpha.iso.sha256`.
- O ZIP de artefato expirará em 27/10/2026 (21:39 UTC). Para reproduzir, use **Actions → Build RedeTI Recovery OS ISO (alpha) → Run workflow**.
- O ZIP tem cerca de 1,38 GB e é obtido na seção Artifacts da execução do workflow.
- A compilação, os testes de lógica, a verificação de checksum da ISO original e a verificação estrutural do ISO personalizado concluíram com sucesso.
- **Não foi comprovado boot gráfico em QEMU ainda.** Teste de boot isolado: https://github.com/paulodepaula/SO_SYSTEM_RECOVERY/actions/workflows/smoke-recovery-iso.yml

**Procedimento de laboratório após o boot gráfico ser validado:** extraia a ISO do ZIP, confira `sha256sum -c RedeTI-Recovery-OS-alpha.iso.sha256`, copie `RedeTI-Recovery-OS-alpha.iso` à partição de dados do Ventoy e selecione-a no menu. Não grave a ISO diretamente sobre o Ventoy e não use em disco de cliente nesta fase.

## Plano de evolução

1. **v0.4-alpha:** painel, reconhecimento e cartões de diagnósticos implementados, ISO criada no GitHub Actions; teste de boot em QEMU pendente.
2. v0.5: escolher automaticamente candidato quando inequívoco; solicitar seleção quando houver ambiguidade; diagnóstico offline do boot em somente leitura.
3. v0.6: análise BCD e trilha de evidências, sem reparos.
4. v0.7: reparos supervisionados exclusivamente em discos virtuais e imagens descartáveis.
5. v1.0: testes BIOS/UEFI em matrizes de hardware e imagens, documentação e liberação controlada.

Este projeto não exige o uso do SSD de cliente durante desenvolvimento.

## Acesso remoto por VPN e SSH (v0.5 planejada)

A arquitetura de conexao automatica na inicializacao, identidades efemeras, Tailscale SSH, controles de acesso e ausencia de credenciais embutidas na ISO esta em [docs/VPN_SSH_BOOT.md](../docs/VPN_SSH_BOOT.md). **A ISO alpha atual nao inclui VPN/SSH**.


## Erro QEMU: kernel x86-64 detecta CPU i686

Esse erro aparece quando o emulador apresenta um processador de 32 bits ao SystemRescue 13.02. **Nao indica ISO corrompida.** Escolha `qemu-system-x86_64` e um modelo de CPU 64-bit, em vez de `qemu-system-i386` ou `-cpu qemu32`.

No Hermes, para testar a ISO local sem ligar discos de clientes a maquina virtual:

```bash
sudo apt install -y qemu-system-x86
bash boot_gui/build/test-qemu-x64.sh ~/RecoveryOS/out/RedeTI-Recovery-OS-alpha-AAAAMMDDTHHMMSSZ.iso
```

Substitua o nome pelo arquivo ISO realmente gerado. Se o Hermes nao tiver interface grafica, o teste disponibiliza VNC apenas em `127.0.0.1:5900`. No Windows, abra um tunel SSH para o Hermes (`ssh -L 5900:127.0.0.1:5900 paulo@hermes-server`) e use seu visualizador VNC em `localhost:5900`. O teste nao adiciona HDD/SSD nem adaptador de rede a VM.

Em Windows, a alternativa e executar diretamente a versao 64-bit do QEMU, por exemplo:

```powershell
& "C:\Program Files\qemu\qemu-system-x86_64.exe" -machine q35 -accel tcg -cpu max -m 3072 -smp 2 -boot order=d -cdrom "D:\ISOs\RedeTI-Recovery-OS-alpha.iso" -nic none
```

Ajuste o caminho da ISO. Evite utilitarios que iniciem a imagem com QEMU de 32 bits por padrao.
