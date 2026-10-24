# RedeTI Recovery OS

Sistema híbrido **Windows PE + Linux Rescue** em planejamento para diagnóstico e recuperação supervisionada de inicialização do Windows.

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
