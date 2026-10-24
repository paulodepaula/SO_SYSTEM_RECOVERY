# RedeTI Recovery OS

Projeto de sistema bootável híbrido Windows PE + Linux para diagnóstico e recuperação supervisionada de falhas de inicialização do Windows.

## Página do projeto

A página pública está implementada em `index.html`, sem dependências externas. Mostra uma reprodução HTML/CSS responsiva da interface conceitual e descreve arquitetura, diagnóstico orientado por evidências, salvaguardas e roadmap.

Para testar localmente, abra `index.html` no navegador. A página não executa diagnósticos nem reparos.

## GitHub Pages

Em **Settings > Pages > Build and deployment**, escolha **Deploy from a branch**, branch **main**, diretório **/(root)** e salve. A URL esperada após o GitHub publicar é `https://paulodepaula.github.io/SO_SYSTEM_RECOVERY/`.

## Escopo

- A interface web é demonstrativa.
- Coletores de hardware, reparos reais, ISO híbrida e integração ao Service Desk ainda não estão implementados nesta página.
- Qualquer futuro reparo persistente exigirá identificação e confirmação do dispositivo, evidências, autorização, salvaguardas e auditoria.
