# Relatórios locais de execução

O projeto mantém relatórios sanitizados de cada etapa em:

- `reports/latest.md`
- `reports/latest.json`
- `reports/history/`

O gerador é `scripts/generate-recovery-report.py`. O `appliance/build/build-local.sh` o executa automaticamente ao concluir a composição da ISO.

Regras:

- relatórios são locais por padrão;
- publicação no GitHub exige autorização explícita;
- ISOs nunca são publicadas automaticamente;
- não registrar credenciais, tokens, dados de clientes ou identificadores sensíveis;
- pendências de homologação física permanecem explícitas;
- o SHA256 deve ser calculado sobre a ISO real e conferido pelo sidecar.

Exemplo manual:

```bash
python3 scripts/generate-recovery-report.py \
  --stage BOOT-2 \
  --commit HEAD \
  --iso /caminho/para/candidata.iso \
  --compile-result PASS \
  --test "suíte automatizada aprovada" \
  --pending "homologação física BIOS/UEFI"
```
