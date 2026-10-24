# RedeTI Recovery OS

**Fluxo de produto:** inserir o pendrive Ventoy, escolher uma ISO própria do RedeTI Recovery OS, iniciar automaticamente a interface gráfica, reconhecer CPU/RAM/firmware/discos no cabeçalho e apresentar os diagnósticos disponíveis abaixo.

**[Nova aplicação gráfica e receita de ISO v0.4-alpha](boot_gui/README.md)** · [Código do painel](boot_gui/ui/) · [Backend de hardware](boot_gui/app/server.py) · [Receita de ISO](boot_gui/build/compose_iso.sh)

**Status real:** interface e receita de construção disponíveis, mas ISO bootável personalizada **ainda não foi construída/homologada**. O código Python anterior permanece como laboratório, não como fluxo final do técnico.

---

## O que existe hoje
- **Página demonstrativa:** [index.html](index.html) — arquitetura, fluxo de evidências e conceito de interface.
- **Protótipo v0.1 em Python:** motor de regras [recovery/engine.py](recovery/engine.py), CLI [recovery/cli.py](recovery/cli.py), [fixtures/](fixtures/) e [tests/](tests/).
- **Documentação:** [Especificação](docs/ESPECIFICACAO.md) e [Plano de testes](docs/PLANO_DE_TESTES.md).

> **Atenção:** esta versão NÃO é uma ISO bootável. O código trabalha SOMENTE com cenários JSON simulados, não lê discos reais e não executa comandos de recuperação. A interface HTML também é demonstrativa.

## Rodar os testes (Python >=3.10)
```bash
python3 -m pip install pytest
python3 -m pytest -q
python3 -m recovery --fixture fixtures/bcd-corrupt.json --output relatorio-lab.json
python3 -m recovery --fixture fixtures/failing-disk.json
python3 -m recovery --fixture fixtures/bitlocker-locked.json
```

## Futuras etapas
Coletores somente leitura, adaptador WinPE, bloqueios auditáveis, testes em VMs, mídia bootável híbrida e integração ao Service Desk RedeTI.

## GitHub Pages
Em **Settings > Pages**, escolha **Deploy from a branch**, branch **main**, diretório **/(root)**. Depois de publicada, a página deverá aparecer em https://paulodepaula.github.io/SO_SYSTEM_RECOVERY/.


## v0.2 — Coletor Linux somente leitura (laboratório)

Código: [recovery/linux_collector.py](recovery/linux_collector.py).
Testes: [tests/test_linux_collector.py](tests/test_linux_collector.py).

No terminal do SystemRescue, dentro do repositório:

```bash
python3 -m recovery.linux_collector --live --acknowledge-read-only
```

O módulo consulta **somente** os comandos `lsblk`, `smartctl` e `fdisk -l`. Não monta partições, não executa verificações com reparo, não modifica BCD e não escreve relatórios em disco: a saída é JSON no terminal. Os flags `--live` e `--acknowledge-read-only` são obrigatórios para executar a coleta real. O Ventoy e outros dispositivos USB/removíveis são listados, mas não submetidos a SMART/fdisk adicional. Resultados desconhecidos não significam disco saudável.

A integridade de BCD e dos arquivos Windows permanece **NOT_TESTED**, não sendo confundida com a presença dos arquivos. O bloqueio de operações de reparo permanece **BLOCKED** em todos os relatórios da v0.2.

Testes isolados, sem equipamentos reais:

```bash
python3 -m pytest -q
```

A v0.2 já dispõe de coletor de inventário de armazenamento, mas **ainda não é um sistema bootável próprio**. A ISO Linux Rescue é usada como ambiente externo de laboratório.


## v0.2 - Modulo 2: boot Windows BIOS/MBR, somente leitura

Arquivos:
- [recovery/windows_boot_collector.py](recovery/windows_boot_collector.py): inspeciona arquivos e cabecalhos em volumes NTFS ja montados read-only;
- [recovery/diagnose.py](recovery/diagnose.py): combina inventario de discos, preflight SMART e inspecao de arquivos;
- [tests/test_windows_boot_collector.py](tests/test_windows_boot_collector.py): testes simulados de seguranca e evidencia.

O modulo NAO monta particoes. Use os pontos de montagem ja criados em /mnt/redeti-boot e /mnt/redeti-windows e confirme que ambos estao em modo ro. Se nao estiverem em ro, o coletor cancela essa analise.

No SystemRescue, atualizar os tres scripts para RAM e executar:

    mkdir -p /run/redeti
    for file in linux_collector.py windows_boot_collector.py diagnose.py; do
      curl -fL "https://raw.githubusercontent.com/paulodepaula/SO_SYSTEM_RECOVERY/main/recovery/$file" -o "/run/redeti/$file" || exit 1
    done
    python3 /run/redeti/diagnose.py --live --acknowledge-read-only

O relatorio aparece apenas no terminal (JSON). O programa consulta lsblk, smartctl, fdisk -l e findmnt. Ele exige volumes NTFS somente leitura pertencentes ao mesmo disco interno. Se houver risco fisico evidenciado pelo inventario, nao realiza leitura adicional de arquivos de Windows. Nao ha comandos de reparo, montagem ou gravacao de laudos no SSD.

Inspeciona exclusivamente bootmgr, Boot/BCD, winload.exe, ntoskrnl.exe e hive SYSTEM, lendo ate 4096 bytes iniciais por arquivo. Distingue MISSING, PRESENT_UNVERIFIED e HEADER_RECOGNIZED. A integridade de BCD e Windows permanece NOT_TESTED: reconhecer assinatura nao comprova consistencia. Suporte UEFI/EFI precisa de modulo proprio.

Execucao em hardware real ainda esta em homologacao. O objetivo desta etapa e observacao, nao recuperacao.


## v0.3 experimental - diagnostico automatico em uma execucao

**Objetivo:** nao solicitar que o tecnico escolha /dev/sda, descubra volumes ou monte particoes. O script [recovery/auto_scan.py](recovery/auto_scan.py) identifica discos internos pelo inventario do Linux e avalia automaticamente particoes NTFS e ESP FAT no SystemRescue.

Execute **somente em SSD de laboratorio**, no SystemRescue:

```bash
mkdir -p /run/redeti && curl -fL https://raw.githubusercontent.com/paulodepaula/SO_SYSTEM_RECOVERY/main/recovery/auto_scan.py -o /run/redeti/auto_scan.py && python3 /run/redeti/auto_scan.py --live --acknowledge-read-only
```

Salvaguardas implementadas:
- Ignora discos USB/removiveis, como o Ventoy.
- Impede leitura adicional de arquivos se SMART falhar, estiver inconclusivo ou indicar setores problematicos.
- Ignora volumes ja montados, em vez de modificar suas opcoes.
- Monta temporariamente NTFS com `ro,norecover,nodev,nosuid,noexec` e ESP FAT com `ro,nodev,nosuid,noexec`.
- Valida a montagem `ro` com findmnt antes de ler ate 4096 bytes dos arquivos de boot e do Windows; desmonta quando termina.
- Recusa disco com tipo de transporte nao reconhecido, para evitar atingir dispositivos inesperados.
- Se detectar mais de um disco interno, nao monta nenhum; exige avaliacao humana do ambiente para evitar atingir outro disco do cliente.
- So cria diretorios temporarios sob `/run` se ele for tmpfs; gera JSON no terminal.
- Nunca executa formatacao, reparos, SFC, CHKDSK, BCDBoot ou outros comandos de escrita.

**Limites:** Montagem somente leitura nao equivale a risco fisico zero: a leitura pode sobrecarregar um disco defeituoso. Dados de cliente nao devem ser usados na homologacao. A ferramenta nao valida internamente o BCD nem a integridade do Windows; apenas presenca e cabecalhos. Particoes criptografadas, RAID/volumes nao suportados e dispositivos com SMART inconclusivo ficam sem inspecao de arquivos. Falhas ao desmontar exigem conferencia manual. O projeto ainda depende do SystemRescue e nao constitui uma ISO propria.

**Testes:** `python3 -m pytest -q` em ambiente de desenvolvimento; `tests/test_auto_scan.py` contem nove testes com coletores simulados, sem discos reais.
