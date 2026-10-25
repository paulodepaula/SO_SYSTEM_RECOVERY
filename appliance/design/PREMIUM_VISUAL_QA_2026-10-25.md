# QA — Rodada premium nativa — 2026-10-25

## Escopo implementado
- `appliance/native/ui/theme.c/.h`: fundos em gradiente azul-marinho, sombra leve e glow ciano nas regioes nativas.
- `appliance/native/premium_assets.py`: arte original do notebook em perspectiva com brilho integrado e 17 icones de 24x24 desenhados por Pillow, sem rede. Gera descritores ARGB8888 no build.
- `appliance/native/ui/assets.h`: contratos dos descritores visuais.
- `appliance/native/ui/dashboard.c`: imagem do notebook integrada ao hero com escala por largura e substituicao do conjunto de simbolos por icones recoloridos LVGL, mantendo fallback.
- `appliance/native/CMakeLists.txt`: arte embutida nos executaveis e CTest com 1280x720, 1366x768 e 1589x990.
- `appliance/tests/test_dashboard_mvp.py`: contratos de arte offline e escopo.

## Estados de comprovacao (nao confundir)
1. **Implementado no GitHub**: arquivos publicados na branch `main`.
2. **Testes Python**: consultar run de `Recovery OS unit tests` do ultimo HEAD, nao de commit anterior.
3. **Compilacao nativa e rasterizacao CTest**: consultar run de `Appliance native LVGL compile (no ISO)` que inclui o ultimo commit com mudanca nativa.
4. **ISO construida no Hermes**: PENDENTE.
5. **Homologacao grafica em QEMU da ISO nova**: PENDENTE.
6. **Teste fisico, SSH LAN/VPN e disco de laboratorio**: PENDENTE.

## Checklist antes de aprovar nova ISO
- Compilar no Hermes a partir do ultimo `main` limpo e passar CTest.
- Somente apos sucesso, montar **uma** ISO experimental com SystemRescue 13.02 verificado.
- Nao excluir ISO homologada anterior ate aprovar substituta.
- QEMU com `-nic none` e sem SSD de cliente; usar disco virtual descartavel quando necessario.
- Fotografar ou capturar 1280x720 e 1366x768 com scroll **no topo** e na area de modulos.
- Confirmar notebook visivel, textura gradiente/glow sem artefatos, e icones nitidos.
- Conferir IP/VPN/SSH reais, topbar sem texto cortado, botoes desativados discretos.
- Clicar `Testar Entrada`, Tab/Enter e rolar sem regressao.
- Verificar `/run/redeti/ui.log`, `/run/redeti/ui.exit` em caso de falha de boot.
- Nao alterar discos; diagnosticos continuam em somente leitura.

## Limitacoes conhecidas
- Ilustracao e icones sao propria arte procedural, nao sao copias pixel a pixel do mockup de referencia.
- O fundo estrelado ainda usa primitivas nativas LVGL, e nao uma imagem vetorial mestre.
- Fonte PT-BR segue Montserrat com transliteracao provisoria.
- O notebook nao foi homologado visualmente no equipamento real; a verificacao sera feita pela ISO unica da rodada.
- O stack SSH/Tailscale, a deteccao hardware e o SystemRescue nao foram modificados.
