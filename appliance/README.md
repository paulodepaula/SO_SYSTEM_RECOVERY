# RedeTI Recovery OS — Linha Appliance (sem desktop Linux)

Esta pasta implementa a nova direção do produto. **Não é uma variante do Sergei Strelec e não inicia um desktop Linux:** o kernel e drivers executam em segundo plano, enquanto o aplicativo LVGL utiliza diretamente o display DRM/KMS.

## Conteúdo existente

- [ARCHITECTURE.md](ARCHITECTURE.md): arquitetura e critérios de aceite do boot direto.
- [probe.py](probe.py): reconhecimento automático de CPU, RAM, firmware do Recovery OS, discos e partições; retorna JSON em stdout ou somente sob `/run/redeti`.
- [tests/test_probe.py](tests/test_probe.py): seis testes simulados, sem acesso a discos.
- [native/main.c](native/main.c): **protótipo inicial** da tela DRM/KMS nativa com os cartões RedeTI, que lê JSON do inventário.

### Segurança

O coletor inicial não monta partições, não altera BCD, não executa SMART self-tests nem escreve no armazenamento. Somente sinaliza o possível Windows quando encontra NTFS. Confirmação de Windows, BitLocker, BCD e análises profundas são fases posteriores. Um SSD do cliente não deve ser utilizado no desenvolvimento.

### Testar o coletor (sem ISO)

```bash
python3 -m unittest discover -s appliance/tests -v
python3 appliance/probe.py
```

O segundo comando é somente consulta de inventário no equipamento onde for executado; na homologação use VM descartável. No SystemRescue, o boot futuro gravará seu JSON em memória RAM:

```bash
python3 /opt/redeti-appliance/probe.py --output /run/redeti/hardware.json
```

### Sobre a tela LVGL

O arquivo `native/main.c` já compilou no GitHub Actions com LVGL 9.6, DRM/KMS e logo PD incorporada. **Isso ainda não equivale à homologação de inicialização real no SystemRescue/QEMU.** Para compilar é necessário fornecer uma árvore **LVGL v9.x** para o Linux de destino com `LV_USE_LINUX_DRM=1`, libdrm e `json-c`. A renderização usa diretamente DRM/KMS (não `DISPLAY`, X11, Wayland, Firefox ou `127.0.0.1:8765`). A versão inicial ainda precisa de entrada de mouse/teclado evdev/libinput, fonts, logo PD como asset nativo e validação em VGA/UEFI.

**Importante:** não copie binário compilado no Ubuntu para a ISO Arch/SystemRescue sem verificar ABI e dependências. Compile para o rootfs específico e preserve a ISO anterior até passar no QEMU.

### Fluxo de boot desejado

```text
BIOS / UEFI → kernel Linux e drivers mínimos
            → inventário /run/redeti/hardware.json
            → redeti-ui (LVGL + DRM/KMS)
            → Central exclusiva RedeTI, sem desktop
```

O código da receita de build da ISO Appliance está disponível, mas **a ISO nativa ainda não foi produzida nem testada em boot real**. A antiga ISO da pasta `boot_gui/` continua baseada em XFCE/Firefox e **não atende** ao novo objetivo. Não é adequado retirar o desktop da ISO antiga antes de compilar e testar uma interface DRM funcional.

### Próximos bloqueios para homologar o primeiro boot direto

1. Empacotar LVGL/DRM/evdev e compilar `redeti-ui` para o rootfs alvo.
2. Iniciar o programa diretamente pelo `init` ou serviço de boot, desligando `dostartx`; validar em QEMU sem SSD.
3. Integrar monograma PD fiel como asset renderizável pelo LVGL e teclado/mouse.
4. Validar reconhecimento real de disco no cabeçalho, sem confundir `candidato NTFS` com Windows confirmado.
5. Só depois gerar e homologar ISO Appliance v0.5 no Ventoy.


## Retencao de ISOs no Hermes

O projeto adotou politica de **apenas uma ISO RedeTI gerada e verificada** na pasta de saida, alem do cache fixo da ISO-base SystemRescue. O script compartilhado [scripts/prune-recovery-isos.sh](../scripts/prune-recovery-isos.sh) suporta --dry-run e --apply, validando SHA-256 antes de remover arquivos antigos. O compilador legado [boot_gui/build/build-local.sh](../boot_gui/build/build-local.sh) ja chama a limpeza automaticamente apos o build bem-sucedido. **Quando o compilador do Appliance for implementado, devera chamar o mesmo script** apos a validacao da nova ISO. Ate la nao existe um build de ISO Appliance ativo para aplicar esta politica.


## Etapa A em implementacao: compilacao nativa e ISO sem XFCE

A linha Appliance tem scripts independentes da receita antiga `boot_gui`. **O executavel em C e o conjunto de bibliotecas ainda precisam passar no teste real SystemRescue/QEMU.**

### Compilar apenas o executavel no Hermes (sem gerar ISO)

```bash
cd ~/RecoveryOS/SO_SYSTEM_RECOVERY
git pull --ff-only
bash appliance/build/build-native-arch.sh
```

Requer Docker no Hermes. O script cria um conteiner **Arch Linux nao privilegiado**, monta o codigo do projeto em leitura (`/project:ro`) e grava apenas no cache dedicado `~/RecoveryOS/native-build/`. Ele instala dependencias no conteiner, busca o LVGL v9.6.0 fixado por commit e compila `redeti-ui` com DRM/KMS e json-c. O monograma PD original e convertido localmente para RGB565 e incorporado como recurso do executavel, sem navegador.

A compilacao inicial baixa uma imagem Arch e dependencias pequenas/moderadas, mas **nao baixa nem cria outra ISO de 1,3 GB**. Revisoes posteriores reutilizam o cache de compilacao. A compilacao Arch e deliberada para aproximar o ambiente ABI do SystemRescue, mas nao elimina a necessidade de validar dinamicamente as bibliotecas no boot.

Arquivo final: `~/RecoveryOS/native-build/out/redeti-ui`.

### Gerar uma unica ISO de laboratorio (somente depois de compilar)

```bash
cd ~/RecoveryOS/SO_SYSTEM_RECOVERY
bash appliance/build/build-local.sh ~/RecoveryOS/base/systemrescue-13.02-amd64.iso
```

Este builder separado insere o executavel e o coletor Python no SRM, adiciona `900-redeti-appliance.yaml` com `dostartx: false`, e configura o `autorun` de console para executar o programa. Usa a ISO-base preservada e valida sua assinatura SHA-256, mas **nao promete que o binario rodara no runtime SystemRescue antes do QEMU**.

A ISO gerada tem nome `RedeTI-Recovery-OS-appliance-<timestamp>.iso`. Por seguranca, enquanto o primeiro boot nativo nao passar, o script mantem a ISO anterior. Depois do aceite visual e do teste de entrada, utilizar o controlador de retencao `scripts/prune-recovery-isos.sh` para manter somente a versao aprovada.

### Teste QEMU sem disco

Na VM usar CPU 64-bit e DRM do adaptador grafico; nao conectar HDD/SSD e nao habilitar rede. Exemplo no Windows, ajustando a ISO:

```powershell
& "C:\Program Files\qemu\qemu-system-x86_64.exe" -machine q35,vmport=off -accel tcg -cpu max -m 3072 -smp 2 -device virtio-vga -device qemu-xhci -device usb-tablet -boot order=d -cdrom "D:\ISOs\RedeTI-Recovery-OS-appliance.iso" -nic none
```

**Critério de aceite:** logo PD e Central RedeTI aparecem diretamente, sem desktop, barra XFCE, Firefox ou HTTP. A ausencia de disco interno aparece como `Nenhum disco interno identificado`; nao se pode marcar Windows como confirmado apenas com NTFS.

### Evidencias da compilacao

`[Native LVGL compile — GitHub Actions](https://github.com/paulodepaula/SO_SYSTEM_RECOVERY/actions/workflows/native-appliance.yml)` valida a compilacao do projeto sem compilar ISO. Os testes simulados do `appliance/tests/` validam o inventario e a independencia do boot. A ISO appliance so sera anunciada como homologada depois do teste de boot completo.

### Correcao do checksum ao transferir executavel do Docker para o Hermes

Builds anteriores a correcao gravavam `/out/redeti-ui` no arquivo `redeti-ui.sha256`. Este caminho so existe dentro do conteiner Docker. A falha observada no Hermes foi `sha256sum: /out/redeti-ui: No such file or directory`.

O compilador agora gera checksum portavel com o nome `redeti-ui`, e o construtor de ISO verifica o hash dos bytes do executavel real no Hermes, ignorando o caminho antigo no sidecar. Assim, **nao e necessario recompilar o binario de 1,4 MB que ja foi gerado**:

```bash
cd ~/RecoveryOS/SO_SYSTEM_RECOVERY
git pull --ff-only
bash appliance/build/build-local.sh ~/RecoveryOS/base/systemrescue-13.02-amd64.iso
```

Caso o Hermes ainda tenha o codigo antigo e o `git pull` nao esteja disponivel, uma correcao local e:

```bash
cd ~/RecoveryOS/native-build/out
sha256sum redeti-ui > redeti-ui.sha256
sha256sum -c redeti-ui.sha256
```

A compilacao da ISO ainda exige o teste separado de boot DRM/KMS no QEMU; sucesso de checksum nao equivale a homologacao de boot.
