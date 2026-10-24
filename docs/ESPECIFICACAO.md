# Especificação técnica — RedeTI Recovery OS v0.1

## Objetivo
Projeto de ferramenta híbrida Windows PE + Linux para investigação e recuperação supervisionada de falhas de inicialização do Windows. A v0.1 é exclusivamente um protótipo laboratorial de interpretação de fixtures JSON; não inicializa por USB, não coleta dados de discos reais e não efetua reparos.

## Arquitetura prevista
- Menu bootável para selecionar Windows PE e Linux Rescue, após validação de compatibilidade e licenças.
- Adaptadores de leitura independentes para discos, NVMe/SMART, partições GPT/MBR, EFI/BCD e sistema operacional.
- Modelo comum de evidências com origem, instante, identificadores de hardware, integridade e rastreabilidade.
- Motor de regras sem efeito colateral, com achados, riscos, recomendações e plano de reparo.
- Executor de reparos futuro isolado dos coletores, com pré-condições e autorização explícita.
- Saída em JSON e futuro relatório PDF integrado à O.S. do Service Desk RedeTI.

## Diagnóstico orientado por evidências
1. Identificar máquina, unidades e instalações Windows.
2. Verificar condição física antes de operações de escrita.
3. Se houver erro de leitura ou falha SMART, bloquear escrita no disco original e recomendar preservação/clonagem.
4. Se BitLocker estiver bloqueado ou desconhecido, suspender reparos até análise e autorização.
5. Inspecionar EFI, BCD, arquivos Windows, drivers, registro e logs quando for seguro.
6. Gerar plano explicável; nunca executar reparos sem confirmação e salvaguardas.

## Salvaguardas obrigatórias nas versões futuras
- Read-only por padrão; segregação entre coleta, recomendação e execução.
- Identificar disco por serial/modelo/capacidade/UUID, não apenas /dev/sda ou Disk 0.
- Checkpoint de evidências, autorização auditável por ação e registro de comandos.
- Validação de backup ou justificativa documentada antes de operações arriscadas.
- Sem escrita em dispositivos fisicamente degradados até decisão técnica de preservação.
- Sem bypass de BitLocker; exigir credenciais/chaves legitimamente autorizadas.
- Tratamento especial para dual boot, RAID, múltiplos discos e casos ambíguos.
- Após execução futura, verificar alteração efetiva e resultado do boot em ambiente isolado.

## Escopo implementado na v0.1
- `recovery/engine.py`: regras puras sobre estrutura JSON.
- `recovery/cli.py`: leitura de um fixture identificado por `kind=redeti_lab_fixture`.
- Cenários simulados: BCD inválido, risco físico e BitLocker bloqueado.
- 4 testes automatizados de regras.
- Nenhuma chamada de subprocesso nem acesso a disco físico.

## Fora do escopo v0.1
ISO, USB bootável, WinPE funcional, live Linux, coleta de hardware, clonagem, alterações de BCD/EFI, SFC/DISM reais, interface gráfica operacional, API e auditoria persistente.

## Critérios de aceite
- Os quatro testes passam em ambiente Python 3.10+ com pytest.
- Entrada inválida sem marcador de fixture é recusada.
- Nenhuma operação de escrita ou reparo é disponibilizada.
- Saída identifica que evidências são simuladas.

## Ferramentas candidatas
Windows PE: BCDEdit, BCDBoot, SFC, DISM e APIs Windows conforme disponibilidade, licenciamento e compatibilidade.
Linux Rescue: lsblk, smartctl, nvme-cli, sgdisk, TestDisk e GNU ddrescue, após homologação.

Referências:
- https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/winpe-intro
- https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/bcdboot-command-line-options-techref-di
- https://www.gnu.org/software/ddrescue/manual/ddrescue_manual.html
