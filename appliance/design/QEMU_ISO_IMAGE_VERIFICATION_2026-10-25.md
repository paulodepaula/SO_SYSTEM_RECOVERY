# RedeTI Recovery OS — confirmar notebook correto na ISO / QEMU

## Observação de 25/10/2026
A captura QEMU apresentou o **layout de status com três colunas**, mas ainda exibiu o
**notebook procedural antigo**, em vez da imagem fornecida pelo usuário (teclado
realista e lupa/pulso ciano). Isso sugere fortemente que a ISO iniciada ou a cópia
do Windows antecede os commits de integração da imagem. Não é evidência de
problema no DRM nem do arquivo original.

## Comprovação da origem
- Asset aprovado: `appliance/native/assets/source/hero-laptop-panel.png` (380x197).
- Gerador: `appliance/native/premium_assets.py`, que emite o único
  `redeti_hero_laptop` diretamente no ELF.
- Os scripts de build Hermes comparam o commit do ELF com o HEAD.
- A topbar mostra agora os **8 caracteres do commit compilado** abaixo de
  `v0.6.0`, no lugar do indicador genérico `DRM`.
- O nome da nova ISO contém esse mesmo prefixo do commit, e o arquivo
  `.iso.buildinfo` informa SHA256/commit para comparar com a cópia Windows.

## Procedimento no Hermes: uma ISO somente depois da compilação aprovada

```bash
cd ~/RecoveryOS/SO_SYSTEM_RECOVERY
git status --short
git pull --ff-only origin main
git rev-parse HEAD
python3 -m unittest discover -s appliance/tests -v
bash appliance/build/build-native-arch.sh
cat ~/RecoveryOS/native-build/out/redeti-ui.commit
grep -A10 -m1 'const lv_image_dsc_t redeti_hero_laptop' \
  ~/RecoveryOS/native-build/cache/lvgl/premium_assets.c
bash appliance/build/build-local.sh ~/RecoveryOS/base/systemrescue-13.02-amd64.iso
```

Anotar o caminho da **ISO recém-criada** e seu SHA256, conforme a saída do
builder. Não escolher ISO antiga por ordem alfabética.

## Procedimento no Windows/QEMU
1. Encerrar o QEMU por completo e garantir que o processo anterior terminou.
2. Copiar **a nova ISO** para o caminho usado pelo comando QEMU; não
   reutilizar a cópia de nome fixo sem substituí-la.
3. Copiar também o `.sha256` correspondente. Se a ISO receber nome fixo,
   ajustar apenas o nome do arquivo hash, não o seu primeiro campo.
4. Abrir PowerShell para verificar:

```powershell
$iso = "D:\ISOs\RedeTI-Recovery-OS-appliance.iso"
(Get-FileHash -Algorithm SHA256 $iso).Hash
```

Comparar com o campo `iso_sha256` do `.iso.buildinfo` produzido no Hermes.
Os 64 caracteres precisam ser **idênticos**.

5. Iniciar QEMU apontando explicitamente para `$iso`, com
   `-nic none` e sem discos reais conectados.
6. Verificar na imagem do QEMU o hash de 8 caracteres abaixo de `v0.6.0`.
   Se a topbar ainda exibir `DRM`, a ISO **não** contém a revisão
   com identificação visual.
7. Confirmar notebook realista no hero e funcionamento da interface.
   Um CI verde isoladamente não comprova boot da ISO.

## Estados
- GitHub: código e arquivo visual incorporados.
- CI de Python e compilação nativa: validar execução do commit relevante.
- Hermes: build final somente a partir da revisão que será homologada.
- Windows/QEMU: ainda não homologado para a nova imagem.
