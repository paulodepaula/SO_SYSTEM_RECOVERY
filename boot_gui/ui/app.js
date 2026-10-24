"use strict";
const el=id=>document.getElementById(id);
const icons={inventory:"▤",smart:"▣",boot:"⌘",windows:"▧",registry:"♙",report:"▤"};
let snapshot=null;
async function api(url){const r=await fetch(url,{cache:"no-store"});if(!r.ok)throw Error("Falha HTTP "+r.status);return await r.json();}
function message(title,text){el("result").querySelector("strong").textContent=title;el("result").querySelector("p").textContent=text;}
function renderCards(items){
  el("cards").replaceChildren();
  for(const item of items){
    const card=document.createElement("article");card.className="card";
    const icon=document.createElement("div");icon.className="icon";icon.textContent=icons[item.id]||"▣";
    const title=document.createElement("h3");title.textContent=item.title;
    const details=document.createElement("p");details.textContent=item.subtitle;
    const footer=document.createElement("div");footer.className="card-foot";
    const tag=document.createElement("span");tag.className="tag "+(item.ready?"ready":"");tag.textContent=item.state;
    const button=document.createElement("button");button.type="button";button.textContent=item.id==="inventory"?"Ver inventário":item.id==="smart"?"Analisar SMART":"Indisponível";
    button.disabled=!item.ready;button.addEventListener("click",()=>runCard(item.id));
    footer.append(tag,button);card.append(icon,title,details,footer);el("cards").append(card);
  }
}
function showDisks(){
  if(!snapshot)return;
  const parts=snapshot.disks.map(d=>[
    (d.device||"—")+" · "+d.model+" · "+d.size+" · "+(d.is_recovery_media?"USB / recuperação":"interno"),
    ...d.partitions.map(p=>"   "+p.device+" · "+p.size+" · "+p.filesystem)
  ].join("\n"));
  message("Inventário de discos e partições",parts.join("\n\n")||"Nenhum disco identificado.");
}
async function runCard(id){
  if(id==="inventory"){showDisks();return;}
  if(id!=="smart")return;
  message("Analisando SMART","Consultando indicadores em leitura; nenhum autoteste ou reparo será executado.");
  try{
    const r=await api("/api/smart");
    if(r.status!=="COLLECTED"){message("Consulta SMART não concluída",r.message||"Sem dados");return;}
    const a=Object.entries(r.attributes||{}).map(([k,v])=>k+": "+(v===null?"indisponível":v)).join(" · ");
    message("SMART: "+r.health,"Disco: "+r.disk+"\n"+a+"\n"+r.message+"\nSMART aprovado não garante ausência de falhas.");
  }catch(e){message("Falha ao consultar SMART",e.message);}
}
async function refresh(){
  el("refresh").disabled=true;
  try{
    snapshot=await api("/api/overview");
    el("disk").textContent=snapshot.target.label;el("disk-detail").textContent=(snapshot.target.device||"")+" "+(snapshot.target.size||"");
    el("disk-note").textContent=snapshot.target.note;el("cpu").textContent=snapshot.cpu;
    el("cores").textContent=snapshot.logical_processors+" processadores lógicos";
    el("ram").textContent=snapshot.memory;el("firmware").textContent=snapshot.boot_firmware;
    el("drive-count").textContent=snapshot.disks.length+" disco(s) encontrado(s)";
    el("mode").textContent=snapshot.mode==="DEMO"?"DEMONSTRAÇÃO":"SOMENTE LEITURA";
    el("warnings").textContent=(snapshot.warnings||[]).join(" | ");
    renderCards(snapshot.diagnostics||[]);
    message("Diagnóstico orientado por evidências","Hardware reconhecido. O disco com Windows é apenas um candidato até verificarmos sua inicialização. Selecione o diagnóstico desejado.");
  }catch(e){message("Erro no reconhecimento",e.message);}
  finally{el("refresh").disabled=false;}
}
el("refresh").addEventListener("click",refresh);refresh();