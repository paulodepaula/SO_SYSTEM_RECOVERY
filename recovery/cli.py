"""Fixture-only CLI; intentionally no device discovery or subprocess execution."""
import argparse
import json
from pathlib import Path
from .engine import analyze


def main(argv=None):
    parser = argparse.ArgumentParser(description="RedeTI Recovery OS v0.1 - modo laboratorio sem acesso a hardware")
    parser.add_argument("--fixture", required=True, help="Arquivo JSON de dados simulados")
    parser.add_argument("--output", help="Caminho para gravar relatorio JSON (somente arquivo de laboratorio)")
    args = parser.parse_args(argv)
    path = Path(args.fixture)
    if not path.is_file() or path.suffix.lower() != ".json":
        parser.error("Informe um arquivo fixture .json existente")
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(snapshot, dict) or snapshot.get("kind") != "redeti_lab_fixture":
        parser.error("Entrada recusada: kind deve ser redeti_lab_fixture")
    result = analyze(snapshot)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
