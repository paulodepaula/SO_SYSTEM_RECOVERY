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

O script recusa sobrescrever a ISO de origem ou o destino já existente. A receita está em `boot_gui/recipe/` e integra todo o aplicativo em `/opt/redeti-recovery/` da mídia, iniciando sua interface gráfica com Firefox. O build **não foi executado neste repositório**: a ISO oficial de origem e as dependências de compilação precisam estar disponíveis no computador de build.

Depois de construída, teste a ISO em QEMU/VM com disco virtual descartável e, somente se homologada, copie a ISO para a partição de dados do seu Ventoy e inicialize. Não formate nem altere a instalação atual do Ventoy.

## Plano de evolução

1. **v0.4-alpha:** painel, reconhecimento e cartões de diagnósticos (código disponibilizado; boot da ISO pendente de homologação).
2. v0.5: escolher automaticamente candidato quando inequívoco; solicitar seleção quando houver ambiguidade; diagnóstico offline do boot em somente leitura.
3. v0.6: análise BCD e trilha de evidências, sem reparos.
4. v0.7: reparos supervisionados exclusivamente em discos virtuais e imagens descartáveis.
5. v1.0: testes BIOS/UEFI em matrizes de hardware e imagens, documentação e liberação controlada.

Este projeto não exige o uso do SSD de cliente durante desenvolvimento.
