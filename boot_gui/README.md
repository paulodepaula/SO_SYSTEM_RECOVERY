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
