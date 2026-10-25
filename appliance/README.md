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

O arquivo `native/main.c` é o **primeiro esqueleto de implementação**, não uma aplicação já compilada/homologada. Para compilar é necessário fornecer uma árvore **LVGL v9.x** para o Linux de destino com `LV_USE_LINUX_DRM=1`, libdrm e `json-c`. A renderização usa diretamente DRM/KMS (não `DISPLAY`, X11, Wayland, Firefox ou `127.0.0.1:8765`). A versão inicial ainda precisa de entrada de mouse/teclado evdev/libinput, fonts, logo PD como asset nativo e validação em VGA/UEFI.

**Importante:** não copie binário compilado no Ubuntu para a ISO Arch/SystemRescue sem verificar ABI e dependências. Compile para o rootfs específico e preserve a ISO anterior até passar no QEMU.

### Fluxo de boot desejado

```text
BIOS / UEFI → kernel Linux e drivers mínimos
            → inventário /run/redeti/hardware.json
            → redeti-ui (LVGL + DRM/KMS)
            → Central exclusiva RedeTI, sem desktop
```

Ainda não existe uma ISO final `appliance` neste repositório. A antiga ISO da pasta `boot_gui/` continua baseada em XFCE/Firefox e **não atende** ao novo objetivo. Não é adequado retirar o desktop da ISO antiga antes de compilar e testar uma interface DRM funcional.

### Próximos bloqueios para homologar o primeiro boot direto

1. Empacotar LVGL/DRM/evdev e compilar `redeti-ui` para o rootfs alvo.
2. Iniciar o programa diretamente pelo `init` ou serviço de boot, desligando `dostartx`; validar em QEMU sem SSD.
3. Integrar monograma PD fiel como asset renderizável pelo LVGL e teclado/mouse.
4. Validar reconhecimento real de disco no cabeçalho, sem confundir `candidato NTFS` com Windows confirmado.
5. Só depois gerar e homologar ISO Appliance v0.5 no Ventoy.


## Retencao de ISOs no Hermes

O projeto adotou politica de **apenas uma ISO RedeTI gerada e verificada** na pasta de saida, alem do cache fixo da ISO-base SystemRescue. O script compartilhado [scripts/prune-recovery-isos.sh](../scripts/prune-recovery-isos.sh) suporta --dry-run e --apply, validando SHA-256 antes de remover arquivos antigos. O compilador legado [boot_gui/build/build-local.sh](../boot_gui/build/build-local.sh) ja chama a limpeza automaticamente apos o build bem-sucedido. **Quando o compilador do Appliance for implementado, devera chamar o mesmo script** apos a validacao da nova ISO. Ate la nao existe um build de ISO Appliance ativo para aplicar esta politica.
