# RedeTI Recovery OS — Arquitetura Appliance (decisão v0.5)

**Decisão de produto (24/10/2026):** o pendrive Ventoy deve iniciar diretamente uma única aplicação **gráfica nativa e exclusiva**, sem desktop Linux, XFCE, GNOME, X11, Wayland, Firefox ou servidor HTTP. A interface carrega a marca pessoal PD e a identidade RedeTI Recovery OS.

## Experiência obrigatória

1. Plugar Ventoy e selecionar `RedeTI-Recovery-OS.iso`.
2. Boot Linux silencioso (kernel/drivers invisíveis ao técnico; mostrar splash/logo RedeTI).
3. Iniciar o executável `redeti-ui` em modo de vídeo **DRM/KMS direto**.
4. Enquanto exibe o cabeçalho, coletar automaticamente CPU, RAM, firmware da sessão de boot, discos e tabela de partições, sem perguntar `/dev/sda` e sem abrir terminal.
5. Mostrar instalações Windows **confirmadas** somente quando houver evidência dos arquivos adequados; caso contrário mostrar `Windows provável` ou `Não identificado`. Não confundir NTFS com Windows. Não confundir firmware usado no boot do Recovery OS com o modo de boot do Windows instalado.
6. Exibir os cartões de diagnóstico: Armazenamento/SMART, Partições, Boot EFI/BCD, Arquivos Windows, Registro/Drivers e Relatório Técnico. Cartões não implementados devem ficar desabilitados, nunca fingir que foram executados.
7. Nenhuma reparação ou escrita no disco interno na fase v0.5. Diagnóstico mais profundo somente depois de avaliação de risco, preferencialmente sobre imagem, com auditoria e autorização.

## Arquitetura técnica

```text
Ventoy → ISO híbrida BIOS/UEFI
       → kernel Linux + initramfs/drivers (sem desktop)
       → systemd ou init mínimo
            ├── redeti-inventory (lê /proc, /sys, lsblk; JSON em /run tmpfs)
            ├── redeti-ui (LVGL + DRM/KMS; tela única exclusiva)
            └── rede/SSH/VPN (futuro, independente e bloqueado por padrão)
```

**LVGL com driver DRM/KMS** é a camada preferida: usa `/dev/dri/cardX` e desenha diretamente no monitor. Entrada de mouse/teclado via evdev/libinput. Não existe área de trabalho ou navegador. Fallback de vídeo para dispositivos legados: fbdev, somente se disponível e testado. Em QEMU, habilitar controladora de vídeo com DRM/KMS e dispositivo USB tablet para entrada. Não depender de OpenGL/EGL para o primeiro protótipo; iniciar com dumb buffers/software rendering.

As bibliotecas de vídeo e drivers ainda são necessárias: **não é possível desenhar uma interface sem componentes gráficos**, mas não é necessário carregar um *ambiente gráfico de desktop*.

## Base de sistema

**Etapa A — primeiro boot direto:** reaproveitar kernel, firmware e ferramentas do SystemRescue 13.02, mas não iniciar XFCE; empacotar `redeti-ui` nativo em um SRM, iniciar em VT dedicado e testar no QEMU. Não alterar a receita estável `boot_gui/` antes de confirmar que a renderização DRM e entrada funcionam.

**Etapa B — imagem independente mínima:** customizar Linux próprio (Buildroot ou rootfs minimalista equivalente), com drivers SATA/NVMe/USB/RAID/NTFS/EFI, LVGL, coletores e rede opcional, preservando Ventoy e UEFI/Legacy. O kernel é mantido pela compatibilidade com hardware; reduzir desktop não implica remover drivers de armazenamento.

O executável LVGL deve ser compilado para as bibliotecas do sistema de destino (não copiar binário Ubuntu incompatível para SystemRescue/Arch). Construir em um ambiente de build alinhado ao rootfs, com dependências pinadas e testes reproduzíveis.

## Header e indicadores

- **Identidade**: monograma PD, nome RedeTI Recovery OS, versão e estado `Somente leitura`.
- **Computador**: modelo de CPU, núcleos lógicos, RAM, modo de boot **do Recovery OS** (UEFI/Legacy).
- **Disco candidato**: modelo, capacidade, interface, partições encontradas e estado de detecção do sistema Windows.
- **Outros discos**: não escolher automaticamente quando houver mais de um disco interno.
- **Rede/VPN**: estado offline ou aguardando autorização, sem chave persistente no ISO.

## Segurança obrigatória

- Varredura inicial exclusivamente de metadados em leitura: `/proc`, `/sys`, `lsblk`, dados SMART (sem autotestes) de disco selecionado/confiável.
- Detectar e excluir o Ventoy e qualquer mídia USB/removível das operações de recuperação.
- Identificação detalhada do sistema operacional exige evidências de estrutura de arquivos (ex. `Windows/System32`, BCD, EFI), não apenas rótulo NTFS; acesso aos arquivos requer a política de leitura segura.
- Disco com SMART crítico, transportes ambíguos, BitLocker, volumes montados em escrita, RAID não compreendido ou múltiplos candidatos: não executar ações arriscadas; sinalizar condição.
- Temporários e logs somente em `/run` (RAM), nunca no disco do cliente por padrão.
- Mesmo com SSH/VPN remoto, reparos continuam bloqueados até liberação posterior e específica.
- O serviço nativo não expõe HTTP na porta 8765.

## Critérios de aceite do primeiro marco

1. QEMU inicia e chega **diretamente** ao painel PD/RedeTI sem mouse ou terminal prévio.
2. Sem XFCE, barra de tarefas, Firefox, Xorg, Wayland ou páginas de erro HTTP.
3. Iniciar com zero discos também abre o painel e mostra `Nenhum disco interno`.
4. CPU, RAM, firmware e lista de discos exibem valores reais da VM e não dados fictícios.
5. BIOS e UEFI testados separadamente, usando firmwares virtuais apropriados.
6. Disco de laboratório com Windows: somente declarar Windows confirmado quando verificadores de assinatura/arquivos estiverem homologados; antes, `candidato`.
7. Todos os testes em VMs ou discos descartáveis; nenhuma modificação em equipamento/dados reais.
8. A ISO gerada só será chamada `boot direto validado` após capturas reais e testes de entrada/saída.

## Histórico e migração

- `boot_gui/`: legado experimental (XFCE + Firefox + servidor Python). Mantido para referência e rollback, **não é arquitetura do produto final**.
- `recovery/`: regras e coletores Python reutilizáveis para o motor sem UI web.
- `appliance/`: nova linha de desenvolvimento dedicada ao boot direto.
- Não anunciar a ISO já existente como versão Appliance. Ela ainda contém o XFCE e deve ser mantida separada.

## Referências técnicas

- https://lvgl.io/docs/open/integration/embedded_linux/drivers/drm
- https://lvgl.io/docs/open/integration/embedded_linux/drivers/evdev
- https://github.com/lvgl/lv_port_linux
- https://www.system-rescue.org/scripts/sysrescue-customize/
