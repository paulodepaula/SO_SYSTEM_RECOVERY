# CONTEXTO DE RETOMADA — RedeTI Recovery OS
Atualizado em 2026-10-25. Destinado a uma nova sessão de desenvolvimento.

## Objetivo do produto
ISO bootável RedeTI Recovery OS para Ventoy, focada em diagnóstico e recuperação **supervisionada** de inicialização Windows, arquivos, partições e hardware, com salvaguardas de dados. Boot direto na interface personalizada, sem XFCE, Firefox, X11, Wayland, servidor HTTP ou desktop Linux. Base SystemRescue 13.02 como infraestrutura invisível; interface nativa LVGL 9.6 + DRM/KMS e entrada Linux EVDEV.

## Repositório e ambiente
- GitHub: https://github.com/paulodepaula/SO_SYSTEM_RECOVERY
- Branch de trabalho: `main`.
- Hermes (Ubuntu) para compilar: `~/RecoveryOS/SO_SYSTEM_RECOVERY`.
- ISO-base preservada: `~/RecoveryOS/base/systemrescue-13.02-amd64.iso`.
- Binário nativo: `~/RecoveryOS/native-build/out/redeti-ui`.
- ISO gerada: `~/RecoveryOS/out/RedeTI-Recovery-OS-appliance-<timestamp>.iso`.
- No Windows, teste de QEMU com ISO copiada para `D:\ISOs\RedeTI-Recovery-OS-appliance.iso`.
- Manter ISO-base e **uma ISO RedeTI homologada**; não apagar a anterior até comprovar a nova. O compilador Appliance ainda preserva imagens não homologadas.
- Nunca homologar usando discos reais de clientes; usar QEMU com disco virtual descartável.

## Arquitetura e principais arquivos
- `appliance/native/main.c`: carrega inventário JSON, DRM/KMS, chama UI.
- `appliance/native/ui/dashboard.c` e `dashboard.h`: dashboard visual MVP v0.6.0.
- `appliance/native/input.c`, `input.h`: mouse, USB Tablet e teclado EVDEV, descoberta de eventos/hotplug, cursor visível.
- `appliance/native/lv_conf.h`: DRM, EVDEV e pool LVGL de 4 MiB (antes 64 KiB).
- `appliance/native/tests/render_smoke.c`: renderização real em memória sem DRM a 1280×720 e 1589×990.
- `appliance/probe.py`: inventário somente leitura de CPU, RAM, BIOS/UEFI, discos e partições; NTFS não comprova Windows válido.
- `appliance/boot/launch.sh` e `900-redeti-appliance.yaml`: autorun direto, `dostartx: false`, logging em `/run/redeti/appliance.log`, `ui.log`, `ui.exit`.
- `appliance/build/build-native-arch.sh`: compila binário em container Arch Linux com limites de CPU/RAM.
- `appliance/build/build-local.sh`: compõe ISO usando base validada; `compose-appliance.sh`.
- `appliance/remote/`: SSH LAN no usuário fixo `paulo`, somente chave pública Ed25519, sem senha/root; VPN Tailscale SSH opcional no mesmo usuário.
- `appliance/design/DASHBOARD_VISUAL_SPEC_V1.md`, `theme_tokens_v1.json`, `assets_manifest_v1.json`, `MVP_V0_6_0.md`: especificação fiel ao mockup premium, paleta, assets, checklist.
- Testes Python: `appliance/tests/`; CMake/CTest e GitHub Actions.

## Linha do tempo curta e diagnóstico resolvido
- v0.4 com XFCE/Firefox descartada por exigência de interface nativa.
- v0.5.x abriu diretamente no QEMU e em hardware físico e identificou CPU/RAM/partições; a fonte PT-BR de `lv_font_conv` causou labels invisíveis, então foi restaurada a Montserrat embutida, usando transliteração ASCII provisória.
- v0.5.4 incorporou EVDEV para cursor/mouse/teclado.
- v0.6.0 visual com topbar, sidebar, hero com estrelas, quatro cards reais, status LAN/SSH/VPN, ações e módulos.
- Primeira ISO v0.6.0 caiu no console SystemRescue após executar autorun: log `EVDEV discovery failed` e retorno `-11` (SIGSEGV). Dependências do executável estavam presentes. Ampliou-se heap LVGL de 64 KiB para 4 MiB, adicionaram-se testes de renderização. **Captura posterior comprovou boot do dashboard v0.6.0 no QEMU**, com CPU QEMU TCG, ~2,8 GiB, BIOS/Legacy, sem disco, status de mouse/teclado detectados. Causa exata do SIGSEGV não foi isolada em backtrace, embora a mudança de heap tenha coincidido com o sucesso.

## Última imagem de teste e correções em GitHub (AINDA NÃO TESTADAS NA NOVA ISO)
Captura QEMU v0.6.0 mostrou:
1. Banner sem notebook — breakpoint exigia conteúdo central >=1050 px; QEMU tinha ~1018 px.
2. Indicador VPN cortado na topbar.
3. Menu e ações inativas em cinza muito chamativo.
4. Módulos de diagnóstico abaixo da dobra, exigir rolagem e teste de scroll.
5. Layout ainda inferior à fidelidade do mockup premium do usuário; ícones LVGL e notebook primitivo provisórios.

**Correções publicadas em 2026-10-25:**
- `90abffb56d`: notebook aparece com `mainw>=900`, arte menor na largura ~1280, topbar mais compacta e status VPN curto.
- `ddd2457261`: ações pendentes passam a usar fundo azul neutro, não cinza sólido.
- `cc349b1495`: testes de regressão de notebook e clipping.
- `60eb9d055b`: documentação dos fatos/observações da homologação QEMU.
O código está no branch `main`. Não confundir testes de CI com boot visual da nova ISO.

## Verificações recentes no GitHub
- Testes automatizados do commit `60eb9d055`: **sucesso** (run 40162993735).
- Testes do commit `cc349b149`: **sucesso** (run 40162969592).
- Compilação nativa no commit `ddd245726`: **sucesso** (run 40162962410).
- Build com ISO e gate QEMU anterior: **sucesso** (run 40162224875, commit `2bd6a216a`), **anterior** aos últimos ajustes de layout.
- Próxima versão visual corrigida ainda precisa de uma ISO nova e de captura QEMU. Não declarar essa nova versão homologada ainda.

## Regras essenciais
- Somente leitura por padrão, sem reparos automáticos, sem montar ou formatar SSD de cliente para testar UI.
- Não copiar imagem/asset protegido nem tratar arte provisória como idêntica ao mockup; preservar logo PD original.
- Não publicar senha, chave SSH privada ou chave Tailscale em ISO/repositório. Chave pública LAN: `REDETI/authorized_keys` no pendrive Ventoy FAT/exFAT; auth key VPN: `REDETI/ts-authkey` de curta validade.
- SSH LAN de `paulo`, porta TCP/22 apenas rede local privada, VPN opcional Tailscale. Status de rede na UI baseado em arquivo de estado real, não mock.
- Não alterar outros serviços do Hermes nem instalar pacotes tipo Sergei Strellec.

## Próxima ação recomendada (objetiva)
1. Verificar que GitHub CI do último commit está verde (não apenas commit anterior).
2. No Hermes, `git pull --ff-only`; compilar só binário e passar CTest; gerar **uma** ISO experimental:
   `bash appliance/build/build-native-arch.sh`
   `bash appliance/build/build-local.sh ~/RecoveryOS/base/systemrescue-13.02-amd64.iso`
3. Copiar nova ISO para QEMU Windows substituindo o arquivo de nome fixo `D:\ISOs\RedeTI-Recovery-OS-appliance.iso`; iniciar QEMU com `-device virtio-vga -device qemu-xhci -device usb-tablet -device usb-kbd -nic none`.
4. Conferir screenshot: notebook visível, VPN sem corte, menu neutro, botões e cursor, scroll dos módulos e hardware identificado; testar 1280×720 e 1366×768.
5. Se houver crash: `cat /run/redeti/appliance.log`, `cat /run/redeti/ui.log`, `cat /run/redeti/ui.exit`, `tail -60 /var/log/sysrescue-autorun.log`; nunca presumir a causa.
6. Com boot aprovado, continuar aproximação visual do mockup com **arte de fundo, notebook e ícones próprios/licenciados** e fonte PT-BR comprovadamente compatível com LVGL 9 (sem regressão de labels).
7. Depois validar SSH LAN/VPN e inventário em disco virtual descartável, sem reparos automáticos.

## Como o próximo assistente deve operar
Continuar o desenvolvimento e aplicar correções reais no GitHub via conector disponível, em pequenos commits com testes. Distinguir *código implementado*, *compilação CI*, *ISO construída* e *homologação visual real*. Não criar imagens de ISO desnecessárias, não afirmar fidelidade visual completa e não pedir novamente dados já fornecidos acima.
