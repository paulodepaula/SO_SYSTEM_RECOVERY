# RedeTI Recovery OS — Dashboard Visual V1

**Status:** especificação aprovada como referência de implementação; **não representa UI já implementada**.
**Referência visual:** imagem enviada na conversa, 1589 × 990 px (captura não publicada no repositório).
**Escopo:** tela inicial fiel à composição, paleta, imagens, ícones e hierarquia visual do mockup; aplicação nativa LVGL 9.6 + DRM/KMS + EVDEV, sem X11, Wayland, XFCE, navegador ou serviço HTTP.
**Base técnica verificada:** `appliance/native/main.c`, `input.c`, `lv_conf.h`, `CMakeLists.txt` e `appliance/probe.py`. Preservar boot, segurança somente leitura, SSH LAN e Tailscale sem alteração de comportamento.

## 1. Fidelidade visual e restrições

- Objetivo é **reproduzir o mockup como layout e composição**, não desenhar um layout genericamente semelhante. Fundo azul-escuro estrelado, brilhos em ciano, hero com notebook à direita, sidebar e ícones consistentemente estilizados.
- Os valores abaixo foram extraídos visualmente/amostrados da imagem 1589 × 990 px e servem como **tokens iniciais**, não como medidas certificadas do original.
- Imagens reais são necessárias: estilos de LVGL não substituem, com fidelidade, o notebook azul, a textura de estrelas e os ícones ilustrados do mockup.
- Arquivos originais de arte e ícones devem ter origem/licença verificadas; não substituir o logo PD fornecido. Não publicar a captura enviada pelo usuário no GitHub sem autorização específica.
- Renderização feita por **LVGL diretamente em DRM/KMS**, sem servidor gráfico, OpenGL ou HTML.
- Nenhum texto de status é fictício. A frase "Rede Conectada", o IP `192.168.1.100` e a utilização `43%` da referência são apenas **exemplos visuais**; em produção esses dados devem vir do sistema real.
- Itens não implementados mostram "Em desenvolvimento", sem evento de reparo. Diagnóstico somente leitura.

## 2. Layout-mestre (1589 × 990; origem superior esquerda)

| Região | Posição aproximada | Dimensões | Conteúdo |
|---|---:|---:|---|
| Fundo geral | x0 y0 | 1589 × 990 | imagem estática azul noturna + leve luz ciano |
| Topbar | x16 y0 | 1556 × 92 | logo PD 72×72; título; status LAN, SSH, VPN, versão |
| Sidebar | x15 y103 | 239 × 845 | 10 opções principais + Sobre/Desligar; altura total flexível |
| Conteúdo | x272 y102 | 1250 × 845 | 4 seções; rolagem vertical só no conteúdo |
| Hero | x272 y102 | 1250 × 248 | título, descrição, selos, 2 botões e notebook à direita |
| Indicadores | x272 y367 | 1250 × 150 | CPU, RAM, Firmware, Disco/Windows; 4 colunas |
| Status / ações | x272 y530 | 1250 × 220 | Status do sistema 54%; ações rápidas 46% |
| Módulos | x272 y761 | 1250 × 186 | seis cartões em grade 3 colunas × 2 linhas |

**Medidas-base:** margem externa 15–16 px; gap principal 16 px; raio 14–16 px em blocos; cards internos raio 11–12 px; borda 1 px. A topbar permanece visível. A sidebar permanece visível em modo largo.

### Hierarquia dos elementos
- Topbar: logo branco e azul, "RedeTI Recovery OS" (32–34 px), subtítulo (15–17 px), três indicadores compactos à direita e bloco de versão.
- Sidebar: largura ~239 px, ícones 20–24 px, labels 15–17 px; item ativo fundo azul e borda/gradiente ciano; área inferior separada para Sobre e Desligar.
- Hero: título 30–32 px, descrição 18–20 px; selos "Somente leitura", "Seguro" e "Rápido", com ícones em quadrados 52×52; botão principal 365×55 e secundário 337×55. Notebook no lado direito com recorte transparente 460–530×228 px.
- Indicadores: 4 cards com largura elástica, altura 148–152 px, ícone 56×56, títulos ~15 px, número/dado ~19 px; barra de memória decorativa **somente** quando o uso real foi medido.
- Status: linhas Rede, SSH, VPN e Entrada; exibir valores reais. Ações rápidas: grade 3×2 de botões compactos.
- Módulos: seis itens 3×2; título + situação + ícone à esquerda + seta ou indicador de disponibilidade à direita.

## 3. Tokens de tema V1 (amostras visuais, ajustar após QA)

| Token | RGB | Uso |
|---|---|---|
| bg-outer | `#001126` | fundo atrás das regiões |
| bg-header | `#001735` | barra superior |
| bg-sidebar | `#081A2E` | menu lateral |
| bg-hero | `#011A38` | painel hero |
| bg-panel | `#0A2135` | status, módulos e área operacional |
| bg-card | `#1A3049` | cartões |
| bg-active | `#054D8E` | menu selecionado |
| blue-primary | `#008CF4` | botão principal |
| cyan-electric | `#00A5FE` | brilho e borda do botão |
| cyan-text | `#59B2EA` | ícones/labels em destaque |
| mint | `#0FD2B5` | status positivo/seguro |
| purple | `#A369F9` | modo de boot |
| amber | `#F8B935` | avisos e disco |
| text-primary | `#EAF4FF` | texto importante |
| text-muted | `#A5BED8` | apoio/descrições |
| border | `#234761` | contornos discretos |
| shadow | `#00101F` | profundidade |

Implementar `theme_tokens.h` com constantes C em RGB hex, tokens de tipografia e raios. Gradientes e sombras devem ser discretos; preferir assets estáticos pré-renderizados para reflexos/glow pesados, pois o equipamento de recuperação pode ter GPU antiga e CPU limitada. Nenhuma animação é necessária para fidelidade.

## 4. Fonte e renderização do português

- Título: família visual semelhante à imagem de referência (sans geométrica, peso semibold); equivalente LVGL com tamanhos 30/32, 22 e 16.
- Corpo: 15–16 px; textos secundários 13–14 px; valores 18–20 px. Nunca diminuir a fonte até ficar ilegível para preencher card.
- O projeto utiliza temporariamente Montserrat embutida e transliteração para ASCII, pois uma geração anterior de fonte customizada deixou **todos os labels invisíveis**.
- Nova fonte PT-BR deve ser compilada com gerador **compatível com LVGL 9.6** e verificada visualmente em QEMU, com a sequência **á é í ó ú ã õ ç Á É Í Ó Ú Ã Õ Ç**. Nunca ativar uma fonte customizada apenas porque o compilador passou.
- Se o teste visual falhar, utilizar fallback conhecido e manter textos legíveis; não voltar a entregar uma tela sem labels.

## 5. Assets necessários

Armazenar originais auditáveis e recursos raster preparados em pastas separadas. Gerar os descritores `lv_image_dsc_t` a partir dos arquivos licenciados e pinados no build, evitando leitura do SSD do cliente e dependência de internet em tempo de execução.

### Imagens principais

| Arquivo sugerido | Tamanho-fonte | Formato de origem | Destino | Observações |
|---|---:|---|---|---|
| `logo-pd` | existente (160×160 SVG com WebP embutido) | projeto atual | RGB565 72×72 | **Reutilizar** arte original de `assets/logo-paulo.svg` |
| `background-starfield` | 1589×990 ou 1920×1080 | PNG/WebP original | RGB565 / imagem embutida | azul escuro, pontos estelares discretos, sem texto |
| `hero-laptop` | ~600×300 | PNG/WebP RGBA | ARGB8888 recortado | notebook 3/4, tela azul com onda; transparente |
| `hero-glow` | ~600×260 | PNG RGBA | ARGB com alfa reduzido | opcional: contorno ciano e feixe atrás do notebook |
| `menu-active-glow` | ~230×52 | PNG RGBA ou LVGL style | estilo/asset | sombra luminosa sutil do item ativo |

A captura de referência mostra arte específica do notebook. Para fidelidade **não** usar imagem genérica aleatória; produzir uma ilustração própria baseada na composição e comparar visualmente no QEMU. Evitar logomarcas de terceiros no notebook sem licenciamento.

### Ícones vetoriais (fonte SVG com licença registrada)

Tamanhos de desenho: menu 22–24 px; resumo 30–32 px em quadrado de 56 px; ações 26–30 px; módulos 26–32 px em quadrado de 46 px. Preferir conjunto consistente (ex.: Lucide sob licença compatível), rasterizado em build para LVGL; não usar emojis/unicode como ícones.

| Área | Semântica / nome do ícone | Cor sugerida |
|---|---|---|
| Menu | house, zap, database, chart-no-axes-combined, cpu, panels-top-left, globe, monitor, file-text, settings, info, power | azul/ciano ou neutro |
| Cabeçalho | wifi, lock-keyhole, shield-check | azul/ciano/verde |
| Hero | book-open-check, shield-check, zap, play, keyboard | azul/verde/amarelo |
| Resumo | cpu, memory-stick, microchip, hard-drive | azul/verde/roxo/âmbar |
| Status | network, shield-check, shield, mouse-pointer-2 | azul/verde/neutro |
| Ações | search-check, monitor, hard-drive, wrench, file-copy, file-output | azul/cinza |
| Módulos | hard-drive, trending-up, cpu, panels-top-left, box, file-text | azul/verde/roxo |

O mapeamento é uma especificação de **semântica**; conferir disponibilidade dos nomes e traços no catálogo SVG efetivamente escolhido antes da exportação.

## 6. Componentes LVGL (estrutura-alvo, sem alterar o engine)

```text
appliance/native/
  main.c                      # DRM, JSON, bootstrap; sem lógica visual extensa
  input.c / input.h           # EVDEV preservado
  ui/
    dashboard.c / dashboard.h # entry point e responsividade
    theme.c / theme.h         # tokens, estilos, fontes
    topbar.c / topbar.h
    sidebar.c / sidebar.h
    hero.c / hero.h
    stats.c / stats.h
    system_status.c / system_status.h
    quick_actions.c / quick_actions.h
    modules.c / modules.h
    navigation.c / navigation.h
    view_model.c / view_model.h # adapta inventário/estado da rede para UI
  assets/
    source/                   # logo/ilustrações/ícones originais + licenças
    generated/                # descritores C gerados (não duplicar binários)
    manifest.json             # resolução, origem, licença, estado
```

### Contratos de dados

- `hardware.json` alimenta os cards de CPU/RAM/firmware/discos. Não declarar Windows confirmado só por NTFS.
- `remote-status.json` alimenta VPN e estado do SSH Tailscale; distinguir autenticação de acesso efetivo.
- `lan-ssh-status.json` alimenta IP local, usuário `paulo` e status de chave pública; **não afirmar que está pronto se apenas há listener TCP/22 sem credencial**.
- EVDEV responde no botão "Testar mouse/teclado"; o estado de "OK" deve depender de evento real (clique/tecla), não de texto fixo.
- Status de uso de RAM exige leitura real e fórmula documentada; não inventar a porcentagem `43%` do mockup.
- Menu e módulos não implementados ficam visivelmente desabilitados. "Reparo do Windows", "Backup de Drivers" e "Desligar" só receberão callbacks quando tiverem fluxos seguros e aprovação apropriada.

### Construção LVGL

- `lv_obj_create` para continentes e cards; `lv_image_create` + `lv_image_set_src` para logo, ilustração, ícones e fundo.
- `lv_obj_set_flex_flow` / `lv_obj_set_layout` ou grid para as regiões; evitar layout inteiro como coordenadas absolutas.
- Usar estilos reusáveis para bordas, raios, foco EVDEV e estados; não alocar um style novo por elemento a cada atualização de status.
- Fontes/raster devem ser compilados para LVGL 9.6 e carregados **diretamente do executável** ou de SRM local, offline.
- Atualizar textos de status com timers LVGL sem redesenhar o cenário estático.
- Cursor, Tab, Enter e foco visível precisam funcionar em QEMU e em hardware físico; todos os botões de fato clicáveis requerem callback válido.
- Ações de escrita continuam desabilitadas até autorização, auditoria e implementação segura separada.

## 7. Layout responsivo e baixa resolução

A imagem original usa proporção ~1,60 (1589×990); **não** foi projetada para caber integralmente em 1366×768.

| Modo | Largura | Regras |
|---|---|---|
| XL — fidelidade | ≥ 1500 px | sidebar 239 px, quatro indicadores, hero com notebook e grade 3×2 |
| Desktop | 1200–1499 px | sidebar 220–230 px, hero condensado, quatro cards ou 2×2 conforme espaço |
| Compacto | 900–1199 px | sidebar só ícones (~72 px), cards 2×2, hero com notebook menor |
| Legado | < 900 px | sidebar recolhível, cards em 1–2 colunas, sem hero lateral; área principal com rolagem |
| Altura < 900 px | qualquer | topbar fixa; **somente conteúdo principal rola**; não reduzir texto abaixo de 14 px |

Definir coordenadas pelo tamanho retornado do display DRM. Nada pode ficar por trás da borda direita ou inferior. Layout testado com 1024×768, 1280×720, 1366×768, 1589×990 e 1920×1080. O histórico de monitor LG antigo exige atenção especial a 1366×768/1280×720 e a renderização por software.

## 8. Performance, qualidade e implantação

- Arte estática pré-otimizada em RGB565; imagens que precisam de transparência em ARGB8888, recortadas para a área visível.
- Evitar imagens gigantes duplicadas em RAM. Limite inicial **alvo** de ~12 MiB para assets decodificados (confirmar medindo no hardware).
- Não iniciar outra thread/processo só para animações. Sem rede e sem disco interno, a home deve abrir normalmente.
- Diagnóstico do dispositivo não deve escrever em discos internos; leitura de documentos exige política de montagem somente leitura separada.
- Não gerar ISO a cada pequena alteração visual. Compilar binário, validar screenshot em QEMU e, **após aprovação**, fazer uma única ISO.
- Política de retenção: ISO-base preservada; uma ISO RedeTI aprovada, removendo anteriores só depois da homologação e nunca apagar ISO em uso.

## 9. Plano de implementação por PRs

1. **UI-01 Tema e layout:** tokens, container, topbar, sidebar e hero sem alterar leitura de hardware.
2. **UI-02 Assets:** logo oficial já existente, ilustração própria do notebook, textura estrelada e pacote SVG/ícones; registrar origem e licença.
3. **UI-03 Cards:** indicadores dinâmicos, status LAN/SSH/VPN, ações rápidas e seis módulos; status real, sem valores de mockup.
4. **UI-04 Responsividade:** 1280×720, 1366×768, 1589×990 e outros modos; foco e rolagem, sem overflow.
5. **UI-05 Fonte PT-BR:** só adotar após screenshots comprovarem glyphs; fallback a Montserrat caso a conversão falhe.
6. **UI-06 Homologação:** capturas QEMU antes/depois, hardware físico, checklist de somente leitura, mouse/teclado/SSH, build e retenção da ISO.

Nenhuma dessas etapas deve introduzir funcionalidades de reparo do Windows antes de seus módulos próprios estarem implementados e homologados.

## 10. Critérios de aceite visual e funcional

- [ ] Layout replicado com cabeçalho, sidebar, hero com notebook, 4 indicadores, painel status, ações e 6 módulos.
- [ ] Logo PD original sem troca de identidade; nenhum elemento de referência com copyright/terceiros copiado sem autorização.
- [ ] Fundo estrelado e glow presentes, sem queda perceptível de fluidez no hardware antigo.
- [ ] Ícones próprios/licenciados, nítidos e consistentes em todas as áreas, sem emojis como substitutos.
- [ ] Acentos PT-BR visíveis; nunca labels em branco ou caracteres quadrados.
- [ ] IP LAN, usuário paulo, VPN, disco/NTFS, CPU e RAM exibem **somente valores reais**; sem falsos sucessos.
- [ ] Mouse, teclado, cursor, foco e botão de teste funcionam; ações indisponíveis não fazem nada e são marcadas.
- [ ] 1366×768 não corta botão, título nem cartão; rolagem funcional.
- [ ] Boot direto: nenhum XFCE, Firefox, X11, Wayland, terminal obrigatório ou porta HTTP.
- [ ] Testes em QEMU com/sem disco; SSD de cliente nunca usado para homologação de arte.
- [ ] Build do executável validado antes de gerar ISO; manter apenas a ISO aprovada depois do teste.

**Resultado esperado:** aparência muito próxima da captura 1589×990 e funcionalidade atual preservada. Este documento é o contrato da etapa visual, não a homologação do produto.
