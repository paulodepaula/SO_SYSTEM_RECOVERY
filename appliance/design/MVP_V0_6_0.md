# RedeTI Recovery OS — Primeiro MVP visual (v0.6.0)

## O que foi implementado

A interface native DRM/KMS deixou de ser uma coluna de cartões e passou a ter um dashboard escuro inspirado na referência 1589×990, mantendo SystemRescue como backend invisível.

- Identidade: logomarca PD existente, título, subtítulo, versão e três indicadores superiores LAN/SSH/VPN;
- Menu esquerdo: Início, Diagnóstico, Discos e Partições, SMART, EFI/BCD, Windows, Rede, Hardware, Logs, Configurações, Sobre, Desligar;
- Banner: fundo estrelado, glow, notebook ilustrado **com primitivas LVGL**, mensagens de somente leitura/segurança, botões funcionais de inventário e teste de entrada;
- Quatro cards conectados a dados reais em `hardware.json`: CPU, RAM, firmware do boot do Recovery OS e candidatos a Windows/discos;
- Status e rede: `/run/redeti/lan-ssh-status.json`, `/run/redeti/remote-status.json`, `paulo@IP` apenas após chave SSH autorizada; input EVDEV real;
- Ações rápidas e módulos: inventário/hardware/discos navegam para detalhes; operações ainda não implementadas estão desabilitadas;
- Inventário com partições e dispositivos internos/USB identificados, sem montar ou escrever nos discos.
- Layout adaptativo com sidebar completa em telas largas, compacta entre 900–1199 px, e dashboard vertical para telas menores.

A versão mantém os ícones contidos no Montserrat/símbolos do LVGL e notebook **ilustrado via LVGL**, não uma fotografia. Para correspondência pixel a pixel com a imagem de referência, o catálogo de ícones e o hero fotográfico licenciados permanecem como etapa visual posterior. Não atribuir ao MVP paridade visual total com a referência.

## Arquivos

- `appliance/native/main.c`: único bootstrap DRM/KMS + leitura do hardware + loop LVGL.
- `appliance/native/ui/dashboard.c`: tela nativa, widgets, navegação e atualização de estados.
- `appliance/native/ui/dashboard.h`: interface entre bootstrap e dashboard.
- `appliance/native/input.c`: mouse/teclado EVDEV já existentes e preservados.
- `appliance/design/DASHBOARD_VISUAL_SPEC_V1.md`: definição detalhada da referência.
- `appliance/tests/test_dashboard_mvp.py`: testes de regressão e limites de segurança.

## Estado do MVP e critérios de homologação

**MVP de código** exige compilação nativa C aprovada e testes automáticos verdes. **MVP de ISO** exige posteriormente execução no QEMU e confirmação com mouse/teclado, tendo em vista que a compilação sozinha não valida DRM, USB, alinhamento e fontes em tempo de execução.

Teste no QEMU isolado, sem disco real nem rede:

```powershell
& "C:\Program Files\qemu\qemu-system-x86_64.exe" `
  -machine q35,vmport=off -accel tcg -cpu max -m 3072 -smp 2 `
  -device virtio-vga -device qemu-xhci -device usb-tablet -device usb-kbd `
  -display gtk,grab-on-hover=off -boot order=d `
  -cdrom "D:\ISOs\RedeTI-Recovery-OS-appliance.iso" -nic none
```

Exigir:

- `v0.6.0` no cabeçalho; tela principal sem XFCE, X11, navegador nem terminal;
- mouse/cursor, teclado e Tab/Enter funcionais no botão de teste;
- sem disco interno, indicação real de ausência, sem inventar Windows/SMART;
- com disco *virtual descartável*, partições exibidas e USB/RECOVERY separado;
- LAN, SSH e VPN mostram situação atual, não estados fictícios;
- itens desativados não executam reparação, formatação nem escrita;
- testar 1280×720, 1366×768 e 1589×990; o conteúdo principal deve rolar sem cortar controles.

## Comandos no Hermes após aprovação da compilação

```bash
cd ~/RecoveryOS/SO_SYSTEM_RECOVERY
git pull --ff-only
python3 -m unittest discover -s appliance/tests -v
bash appliance/build/build-native-arch.sh
bash appliance/build/build-local.sh ~/RecoveryOS/base/systemrescue-13.02-amd64.iso
ls -lh ~/RecoveryOS/out/RedeTI-Recovery-OS-appliance-*.iso
```

**Atenção:** esses comandos só devem ser executados após a compilação CI ser aprovada. A nova ISO será experimental até o teste visual. Não apagar ISO anteriormente homologada antes de testar a nova. O construtor de Appliance preserva imagens anteriores enquanto isso.

## Construcao isolada da ISO no GitHub (sem usar o Hermes)

O fluxo [Build RedeTI Recovery OS Appliance MVP ISO](../../.github/workflows/build-appliance-mvp.yml) monta uma unica imagem nativa a partir do mesmo builder do Hermes, em ambiente Linux temporario, com ISO-base validada por SHA-256, executavel LVGL compilado em Arch e recursos de VPN/SSH. Nao distribui credenciais. O artifact e retido por **apenas um dia**, para evitar acumular grandes imagens. A propria criacao inicial do workflow dispara um build; os futuros builds sao manuais em Actions → Run workflow.

**Nao confundir build de ISO com boot homologado.** Depois de o job concluir, baixe o artifact ZIP, extraia a ISO e seu checksum, valide o SHA-256 e teste no QEMU sem disco real. A tela deve exibir v0.6.0 e os controles de mouse/teclado devem responder.

