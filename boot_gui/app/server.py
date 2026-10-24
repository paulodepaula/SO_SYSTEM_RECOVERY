"""RedeTI Recovery OS graphical cockpit v0.4-alpha.

Local-only (127.0.0.1) HTTP interface. Automatically reads CPU/RAM/firmware,
block-device inventory and probable Windows disk. No mounts or repairs.
Optional SMART query occurs only when clicked.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

APP_DIR = Path(__file__).resolve().parent.parent
UI_DIR = APP_DIR / "ui"
CANDIDATE_TYPES = {"ata", "sata", "nvme", "sas", "scsi", "virtio"}
DEV_RE = re.compile(r"^/dev/[A-Za-z0-9_.-]+$")
LSBLK = ["lsblk", "--json", "--bytes", "--paths", "--output", "NAME,TYPE,SIZE,MODEL,TRAN,RM,FSTYPE,PTTYPE,PARTTYPE"]
CARDS = [
    {"id":"inventory","title":"Discos e partições","subtitle":"Dispositivos, volumes e indícios de Windows","ready":True,"state":"Inventário automático"},
    {"id":"smart","title":"Disco e SMART","subtitle":"Saúde e erros reportados pelo armazenamento","ready":True,"state":"Análise somente leitura"},
    {"id":"boot","title":"Inicialização EFI / BCD","subtitle":"Boot Manager e configuração de inicialização","ready":False,"state":"Em desenvolvimento"},
    {"id":"windows","title":"Arquivos do Windows","subtitle":"Carregador, kernel e integridade offline","ready":False,"state":"Em desenvolvimento"},
    {"id":"registry","title":"Registro e drivers","subtitle":"Serviços e drivers de boot","ready":False,"state":"Em desenvolvimento"},
    {"id":"report","title":"Relatório técnico","subtitle":"Evidências e plano de recuperação","ready":False,"state":"Em desenvolvimento"},
]

def run(argv):
    if argv[0] not in ("lsblk", "smartctl"):
        raise ValueError("Not a read-only allowlisted command")
    try:
        p = subprocess.run(argv, capture_output=True, text=True, errors="replace", check=False, timeout=12)
        return p.returncode, p.stdout[:100000], p.stderr[:2000]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)

def read(path):
    try: return Path(path).read_text(errors="replace")
    except OSError: return ""

def size(n):
    return f"{n / 1073741824:.1f} GiB" if isinstance(n,(int,float)) and n >= 0 else "Não informado"

def cpu(info):
    for line in info.splitlines():
        if line.lower().startswith(("model name","hardware","processor")) and ":" in line:
            value = line.split(":",1)[1].strip()
            if value and not value.isdigit(): return value
    return "Não identificado"

def disks_from(blockdevices):
    disks=[]
    for d in blockdevices:
        if not isinstance(d,dict) or d.get("type") != "disk": continue
        parts=[p for p in d.get("children",[]) if isinstance(p,dict) and p.get("type")=="part"]
        usb=bool(d.get("rm")) or d.get("tran")=="usb"
        eligible=not usb and d.get("tran") in CANDIDATE_TYPES
        disks.append({
            "device": d.get("name"), "model": str(d.get("model") or "Sem modelo").strip(),
            "size": size(d.get("size")), "transport": d.get("tran") or "desconhecido",
            "partition_table": d.get("pttype") or "desconhecida",
            "is_recovery_media": usb, "eligible":eligible,
            "windows_indicators":any((p.get("fstype") or "").lower()=="ntfs" for p in parts),
            "partitions":[{"device":p.get("name"),"size":size(p.get("size")),
                           "filesystem":p.get("fstype") or "desconhecido"} for p in parts],
        })
    internal=[d for d in disks if d["eligible"]]
    possible=[d for d in internal if d["windows_indicators"]]
    if len(internal)==1:
        d=internal[0]
        target={"status":"PROVAVEL" if len(possible)==1 else "NAO_CONFIRMADO",
                "label":d["model"],"device":d["device"],"size":d["size"],
                "note":("Indícios de Windows (NTFS); boot ainda não comprovado."
                        if possible else "Disco interno detectado; Windows ainda não identificado.")}
    elif len(internal)>1:
        target={"status":"SELECAO_NECESSARIA","label":f"{len(internal)} discos internos",
                "device":None,"size":"","note":"Múltiplos discos: não escolher automaticamente."}
    else:
        target={"status":"NAO_IDENTIFICADO","label":"Nenhum disco interno identificado",
                "device":None,"size":"","note":"Verifique controladora, RAID ou firmware."}
    return disks,target

def overview(live=False,command=run,files=read,efi=None,logical=None):
    if efi is None: efi=Path("/sys/firmware/efi").is_dir()
    cpuinfo=files("/proc/cpuinfo")
    meminfo=files("/proc/meminfo")
    mem=re.search(r"^MemTotal:\s*(\d+)\s*kB",meminfo,re.M)
    result={"version":"0.4-alpha","mode":"LIVE_READ_ONLY" if live else "DEMO",
            "repair_allowed":False,"mounts_performed":False,
            "cpu":cpu(cpuinfo),"logical_processors":logical if logical is not None else (os.cpu_count() or 0),
            "memory":size(int(mem.group(1))*1024) if mem else "Não identificado",
            "boot_firmware":"UEFI" if efi else "BIOS / Legacy",
            "firmware_note":"Refere-se ao boot do Recovery OS, não necessariamente ao Windows",
            "diagnostics":CARDS,"disks":[],"warnings":[]}
    if live:
        code,out,err=command(LSBLK)
        if code:
            result["warnings"].append("lsblk indisponível: "+err[:120])
            blockdevices=[]
        else:
            try:
                blockdevices=json.loads(out)["blockdevices"]
                if not isinstance(blockdevices,list): raise ValueError("invalid")
            except (ValueError,KeyError,TypeError): 
                blockdevices=[]
                result["warnings"].append("Inventário de discos inválido")
    else:
        blockdevices=[
            {"name":"/dev/sda","type":"disk","size":512110190592,"model":"SSD LABORATÓRIO",
             "tran":"ata","rm":False,"pttype":"dos",
             "children":[{"name":"/dev/sda1","type":"part","fstype":"ntfs","size":52428800},
                         {"name":"/dev/sda2","type":"part","fstype":"ntfs","size":511543281152}]},
            {"name":"/dev/sdb","type":"disk","model":"Ventoy USB","size":62914560000,
             "tran":"usb","rm":True}]
        result.update(cpu="Intel Core i5 (exemplo)",logical_processors=6,
                      memory="16.0 GiB",boot_firmware="BIOS / Legacy")
        result["warnings"].append("MODO DEMONSTRAÇÃO: dados fictícios")
    result["disks"],result["target"]=disks_from(blockdevices)
    return result

def smart(live=False,command=run):
    if not live: return {"status":"DEMO","message":"Consulta indisponível em demonstração."}
    code,out,err=command(LSBLK)
    if code: return {"status":"BLOCKED","message":"Inventário não disponível"}
    try:
        ds,_=disks_from(json.loads(out)["blockdevices"])
    except (ValueError,TypeError,KeyError): 
        return {"status":"BLOCKED","message":"Inventário inválido"}
    candidates=[d for d in ds if d["eligible"]]
    if len(candidates)!=1:
        return {"status":"BLOCKED","message":"A consulta exige exatamente um disco interno."}
    dev=candidates[0]["device"]
    if not isinstance(dev,str) or not DEV_RE.fullmatch(dev):
        return {"status":"BLOCKED","message":"Identificador inválido"}
    code,out,err=command(["smartctl","-H","-A","-i",dev])
    m=re.search(r"SMART overall-health self-assessment test result:\s*(PASSED|FAILED)",out,re.I)
    attrs={}
    for line in out.splitlines():
        vals=line.split()
        if len(vals)>=10 and vals[0] in {"5","197","198","199"} and vals[-1].isdigit():
            attrs[vals[0]]=int(vals[-1])
    return {"status":"COLLECTED" if out else "INCONCLUSIVE","disk":dev,
            "health":m.group(1) if m else "NÃO VERIFICADO",
            "attributes":{"realocados":attrs.get("5"),"pendentes":attrs.get("197"),
                          "incorrigiveis":attrs.get("198"),"erros_crc":attrs.get("199")},
            "message":err[:120] if not out else "Consulta sem autotestes e sem reparos."}

class Handler(BaseHTTPRequestHandler):
    live=False
    def log_message(self,*_): pass
    def response(self,code,content,typ):
        self.send_response(code)
        for k,v in [("Content-Type",typ),("Content-Length",str(len(content))),
                    ("Cache-Control","no-store"),("X-Content-Type-Options","nosniff"),
                    ("Content-Security-Policy","default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'")]:
            self.send_header(k,v)
        self.end_headers()
        self.wfile.write(content)
    def do_GET(self):
        path=urlsplit(self.path).path
        if path in ("/api/overview","/api/smart"):
            value=overview(self.live) if path.endswith("overview") else smart(self.live)
            self.response(200,json.dumps(value,ensure_ascii=False).encode(),"application/json; charset=utf-8")
        elif path in ("/","/index.html","/app.js","/style.css","/assets/logo-paulo.svg"):
            name=path.lstrip("/") or "index.html"
            suffix=Path(name).suffix
            mimetype={".html":"text/html; charset=utf-8",".js":"text/javascript; charset=utf-8",
                      ".css":"text/css; charset=utf-8",".svg":"image/svg+xml"}.get(suffix,"application/octet-stream")
            try: self.response(200,(UI_DIR/name).read_bytes(),mimetype)
            except OSError: self.response(404,b"Not found","text/plain")
        else: self.response(404,b"Not found","text/plain")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--live",action="store_true")
    p.add_argument("--port",type=int,default=8765)
    args=p.parse_args()
    Handler.live=args.live
    print("RedeTI cockpit at http://127.0.0.1:"+str(args.port),flush=True)
    ThreadingHTTPServer(("127.0.0.1",args.port),Handler).serve_forever()
if __name__=="__main__":main()
