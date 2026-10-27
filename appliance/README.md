# RedeTI Recovery OS — Linha Appliance (sem desktop Linux)

## Primeiro MVP visual v0.6.0

O código do dashboard nativo foi implementado em [native/ui/dashboard.c](native/ui/dashboard.c), com a especificação, limitações e roteiro de homologação em [design/MVP_V0_6_0.md](design/MVP_V0_6_0.md). Ele contém topbar com logo PD e status LAN/SSH/VPN reais, menu lateral, hero escuro estrelado com notebook LVGL, quatro indicadores de hardware, painel de status/ações, seis módulos e inventário de discos/partições. Mouse/teclado EVDEV e boot direto DRM foram preservados.

**Limites atuais:** notebook ilustrado por primitivas em vez de arte fotográfica, ícones LVGL incorporados em vez de biblioteca de SVG próprios, fonte sem acentos usando fallback seguro. SMART, EFI/BCD, registro, reparo e relatório técnico não são anunciados como implementados nem executam ações. O MVP de código não equivale a ISO homologada: executar a compilação C e testes no GitHub, depois gerar somente uma ISO experimental no Hermes e validar visualmente no QEMU.

## Interface visual premium — especificação V1

A tela inicial tem agora uma **especificação visual detalhada e mensurável**, baseada na captura 1589×990 enviada como referência. O trabalho foi especificado **sem modificar o executável ou gerar outra ISO**:

- [Dashboard Visual Spec V1](design/DASHBOARD_VISUAL_SPEC_V1.md): regiões, cores, dimensões, ícones, hero, componentes LVGL, fonte PT-BR, responsividade e aceite;
- [Tokens V1](design/theme_tokens_v1.json): paleta e medidas em formato consumível pelo código;
- [Manifesto de assets V1](design/assets_manifest_v1.json): logo original reutilizável, notebook, fundo, glows e ícones ainda a criar/validar.

Apenas a especificação e o inventário foram publicados nesta etapa. A aparência do mockup **ainda não está implementada na ISO**. A implantação deve seguir UI-01 até UI-06, com capturas QEMU nas resoluções previstas e somente leitura preservada.

Esta pasta implementa a nova direção do produto. **Não é uma variante do Sergei Strelec e não inicia um desktop Linux:** o kernel e drivers executam em segundo plano, enquanto o aplicativo LVGL utiliza diretamente o display DRM/KMS.

## Acesso remoto v0.5.3: SSH LAN + VPN

A nova imagem Appliance usa o **usuário fixo `paulo`** tanto no SSH da rede local quanto no Tailscale SSH. O serviço OpenSSH local é iniciado no boot, independente da VPN, mas **a autenticação exige uma chave pública Ed25519** no pendrive (`REDETI/authorized_keys`); não existe senha padrão. O firewall permite a porta 22 somente na interface e sub-rede privada diretamente conectada. O Tailscale continua opcional e separado.

A tela exibirá estados diferentes para `SSH LAN` e `VPN`, incluindo `paulo@IP` quando a conexão estiver pronta. Detalhes, instruções de geração de chave e teste QEMU estão em [remote/README.md](remote/README.md). **Ainda não homologado no boot físico com a nova configuração.**

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

### Splash antecipado

O splash gráfico é iniciado pela unidade `redeti-early-splash.service`, ligada a
`sysinit.target` no primeiro userspace real, antes do `autorun` que inicia o
inventário e a interface DRM/KMS. O `launch.sh` encerra essa unidade antes de
abrir `redeti-ui` e mantém um fallback caso o framebuffer só apareça depois ou
não exista.

O initramfs Archiso (`inspect/sysresccd.img`) foi inspecionado: seu `init` usa
`busybox/ash` e não contém Python nem o renderer necessário. Por isso o splash
não é injetado no initramfs; mensagens do kernel e da montagem inicial podem
continuar visíveis em alguns BIOS/UEFI. Esta é uma limitação conhecida e não
deve ser confundida com falha do splash no userspace. A unidade usa somente
`/dev/fb0`, não grava armazenamento, não depende de rede e falha fechado para
o efeito visual sem interromper o boot técnico.

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


## Acesso remoto SSH + VPN (próxima ISO experimental)

A integração de **Tailscale SSH** está preparada na pasta [remote/](remote/README.md), com usuário fixo **`redeti`**, sem senha e sem `sudo` automático. Não existe login remoto aberto na LAN. Durante o boot, o serviço verifica se há uma chave efêmera de provisionamento em um pendrive FAT/exFAT explicitamente rotulado `Ventoy` ou `REDETI_CFG`, no arquivo `REDETI/ts-authkey`. O dispositivo interno do cliente nunca é pesquisado para credenciais.

Sem chave autorizada ou rede, a interface funciona normalmente, mas a VPN/SSH ficam inativos. Depois de conectar, a interface exibe `VPN: conectada | SSH: redeti@100.x.x.x`. A ISO nunca inclui uma chave VPN e o estado do Tailscale é mantido em RAM.

O construtor `appliance/build/build-local.sh` baixa, uma vez, a versão estática fixa do Tailscale de seu distribuidor HTTPS oficial, mantém o cache em `~/RecoveryOS/native-build/out` e inclui a ferramenta no SRM. Isso aumenta o tamanho da ISO em relação à versão sem acesso remoto, mas não cria ISOs extras. A limpeza das ISOs anteriores só ocorre depois da homologação de uma nova imagem.

**Leia [o guia de provisionamento e políticas Tailscale](remote/README.md) antes de usar no campo.** Essa integração ainda precisa ser testada em QEMU com rede virtual, chave efêmera de laboratório, ACL restritiva e confirmação de que o IP LAN não aceita SSH. Nenhuma credencial real foi criada ou adicionada ao repositório.

## Correcao emergencial v0.5.2: painel sem textos

No teste QEMU, depois de introduzir `lv_font_conv@1.5.3`, a UI mostrou os cartoes e a logo mas os textos sumiram (exceto o titulo em Montserrat 28). Isso revela uma incompatibilidade de fonte LVGL 8/9 que passou no teste de compilacao, mas nao na renderizacao DRM.

Para a **v0.5.2**, o aplicativo voltou ao `lv_font_montserrat_16` (ja validado no boot), com transliteracao temporaria de caracteres UTF-8 acentuados para ASCII. A tela voltara a apresentar palavras legiveis como "Memoria", "Inicializacao" e "Particoes"; **os acentos ainda nao estarao presentes**. O JSON original do reconhecimento e preservado. Uma fonte PT-BR compatibilizada sera testada posteriormente com renderizacao, nao apenas compilacao.

O projeto usa a interface nativa no QEMU e em hardware fisico; a **v0.5.2 ainda exige boot de homologacao** antes de ser declarada estavel. Nao apague a ultima ISO que exibia texto ate que a nova tenha sido comprovada.

## Firewall e Tailscale SSH

A receita mantem `nofirewall: false`, ou seja, **firewall SystemRescue ativo**. O OpenSSH convencional segue mascarado e nao recebe conexoes da rede LAN. O script `appliance/remote/start.sh` **nao abre TCP 22 em eth0, wlan0 ou em todas as interfaces**. Somente depois de autenticar o Tailscale, obter IP 100.x e identificar `tailscale0`, insere (ou valida) regra INPUT IPv4 restrita a `-i tailscale0 -d IP_DA_VPN/32 -p tcp --dport 22 -j ACCEPT`.

Isso nao garante que Tailscale SSH ja esteja operacional na ISO que esta rodando. E necessario provisionar a chave, conectar rede na VM e validar as regras da tailnet. Com `-nic none` no QEMU, a VPN nao conecta e nenhuma regra e aplicada.

Consulte [remote/README.md](remote/README.md) para o provisionamento e controle de acesso. **Nunca desative o firewall por completo somente para ativar o SSH.**

## v0.5.4 — mouse e teclado diretos no QEMU e hardware físico

**Falha observada em v0.5.3:** o painel nativo abre e reconhece CPU/RAM, mas não movimenta o cursor nem recebe teclas porque `LV_USE_EVDEV` estava desativado e não existia dispositivo `lv_indev` associado à tela DRM/KMS. Isso **não é falha de USB do QEMU nem motivo para instalar XFCE**.

**Correção no código:** a build v0.5.4 habilita `LV_USE_EVDEV=1`, implementa `appliance/native/input.c` e usa `lv_evdev_discovery_start` (LVGL 9.6) para detectar automaticamente dispositivos sob `/dev/input/event*` e dispositivos USB conectados posteriormente. Vincula ponteiros REL (mouse), ABS (USB Tablet), teclado e um cursor visível à tela DRM; liga o teclado ao `lv_group`. Mostra o status dos periféricos e um botão **TESTAR MOUSE / TECLADO**, que responde a clique ou Tab + Enter. Os demais cartões continuam informativos e não executam reparos.

Em QEMU Windows teste com:

```powershell
& "C:\Program Files\qemu\qemu-system-x86_64.exe" `
  -machine q35,vmport=off `
  -accel tcg -cpu max -m 3072 -smp 2 `
  -device virtio-vga `
  -device qemu-xhci -device usb-tablet -device usb-kbd `
  -display gtk,grab-on-hover=off `
  -boot order=d -cdrom "D:\ISOs\NOME-EXATO-DA-NOVA-ISO.iso" `
  -nic none
```

Ajuste o caminho da ISO. O VM usa uma interface USB Tablet absoluta e teclado virtual USB; não passa teclado, mouse nem discos físicos do Windows para o Linux. Com `-nic none`, SSH LAN e VPN permanecerão sem rede, como esperado. Para testar SSH use a receita de rede de laboratório documentada em [remote/README.md](remote/README.md).

**Critérios de aceite:** versão visual v0.5.4; status `mouse detectado | teclado detectado`; cursor acompanha o mouse; clique no botão responde; Tab/Enter também responde. Sem disco interno, painel continua em somente leitura. Verificação CI valida que os símbolos do driver compilaram, **mas não comprova os eventos de entrada**: precisam ser testados visualmente no QEMU.

Se a janela não receber teclas, clique nela para dar foco. `Ctrl+Alt+G` libera o ponteiro capturado pelo QEMU quando necessário; isso é diferente do driver EVDEV ausente na ISO v0.5.3.
