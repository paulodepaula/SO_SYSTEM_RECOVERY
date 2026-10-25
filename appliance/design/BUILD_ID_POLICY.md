# Identificacao obrigatoria de compilacao — RedeTI Recovery OS

Politica permanente: em **toda compilacao nativa** do dashboard, a tela deve exibir
três dados distintos, provenientes da configuracao CMake (nunca digitados no
dashboard):

1. **Versao do produto** — `vMAJOR.MINOR.PATCH`, definida em
   `project(redeti_recovery_appliance VERSION ...)`. Mudar quando o produto
   ganha uma nova versao funcional; nao altera automaticamente a cada commit.
2. **Identificador unico de compilacao** — `bYYMMDD-HHMMSS` (horario UTC
   do configure CMake, gerado automaticamente em cada build).
3. **Commit de origem** — primeiros oito caracteres do SHA Git validado,
   obtido do checkout do Hermes ou `GITHUB_SHA` no CI.

Exemplo ilustrativo:

```text
v0.6.0
b261025-173015
a1b2c3d4
```

Nao inferir o commit pela data da ISO: conferir os valores no banner do QEMU
e no arquivo `redeti-ui.buildinfo` produzido pelo compilador Hermes.

## Verificacoes obrigatorias

- `appliance/native/CMakeLists.txt`: registra os tres identificadores no
  executavel e escreve `redeti-build-id.txt` no diretorio de build.
- `appliance/build/build-native-arch.sh`: injeta SHA Git real, verifica tag
  e commit dentro do ELF e preserva `redeti-ui.buildinfo`.
- `appliance/build/build-local.sh`: compara o manifest do ELF com HEAD
  e grava `app_version`, `build_tag` e `source_commit` na ISO.buildinfo.
- `appliance/native/ui/dashboard.c`: apresenta as tres linhas no header.
  Falhar compilacao se a identidade nao for fornecida; nao usar `unknown`.
- `appliance/tests/`: testes impedem o retorno de valores fixos.
- Build nativo e boot da ISO ainda precisam ser homologados separadamente;
  teste Python/CI nao comprova boot real ou fidelidade da imagem.

Nao gerar ISO adicional apenas para renovar a identificacao. A marca de
compilacao sera atualizada automaticamente na proxima build realmente autorizada.
