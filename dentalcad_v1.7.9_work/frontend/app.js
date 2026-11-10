
const API = window.location.protocol === "https:" ? "" : "http://127.0.0.1:8010"; let token=null;
const $=id=>document.getElementById(id);
const show=o=>$("out").textContent=typeof o==="string"?o:JSON.stringify(o,null,2);
async function call(path,opt={}){
  opt.headers=Object.assign({},opt.headers||{}); if(token) opt.headers.Authorization="Bearer "+token;
  const r=await fetch(API+path,opt); const ct=r.headers.get("content-type")||"";
  if(!r.ok){const b=ct.includes("json")?await r.json():await r.text(); const d=b.detail; const msg=typeof d==="string"?d:Array.isArray(d)?d.map(x=>((x.loc||[]).slice(1).join(".")||"champ")+" : "+x.msg).join(" ; "):JSON.stringify(b);
    throw new Error(r.status+" — "+msg)}
  return r;
}
const run=f=>async(...a)=>{try{await f(...a)}catch(e){show("ERREUR : "+e.message)}};
fetch(API+"/health").then(r=>r.json()).then(j=>$("status").innerHTML='Serveur : <span class="ok">en ligne (v'+j.version+')</span>')
 .catch(()=>$("status").innerHTML='Serveur : <span class="ko">injoignable</span>');
function fd(o){const f=new FormData();for(const k in o){const v=o[k];
  if(v instanceof FileList){for(const x of v)f.append(k,x)} else f.append(k,v)} return f}
window.login=run(async()=>{
  const f=new URLSearchParams({username:$("email").value,password:$("pw").value});
  const r=await call("/api/auth/token",{method:"POST",body:f}); const j=await r.json();
  token=j.access_token; $("who").textContent="Connecté : "+j.full_name+" ("+j.role+")"; $("pw").value=""; show("Connexion réussie");
});
window.createCase=run(async()=>{
  const p=await(await call("/api/patients",{method:"POST",body:fd({external_id:$("ext").value,first_name:$("fn").value,last_name:$("ln").value})})).json();
  const c=await(await call("/api/cases",{method:"POST",body:fd({patient_id:p.id,case_number:$("cn").value})})).json();
  $("caseId").textContent=c.id; show({patient:p,cas:c});
});
window.segment=run(async()=>{
  show("Segmentation en cours (peut durer 1 à 3 minutes)…");
  const j=await(await call("/api/segment",{method:"POST",body:fd({files:$("segFiles").files,threshold:$("thr").value,split_z:$("splitZ").value})})).json();
  show(j); $("dl").innerHTML="";
  for(const r of j.results){
    const b=await(await call(r.url)).blob(); const a=document.createElement("a");
    a.href=URL.createObjectURL(b); a.download=r.file; a.textContent="Télécharger "+r.file+" "; $("dl").appendChild(a);
  }
});
window.registerIcp=run(async()=>{
  show("Calage en cours…");
  const j=await(await call("/api/register",{method:"POST",body:fd({cbct_files:$("regFiles").files,stl_file:$("regStl").files[0],threshold:$("thr").value})})).json();
  show(j);
});
window.savePlan=run(async()=>{
  const j=await(await call("/api/cases/"+$("caseId").textContent+"/plan",{method:"POST",body:fd({implants:$("plan").value})})).json();
  $("ver").value=j.version; show(j);
});
window.validatePlan=run(async()=>{
  if(!confirm("Avez-vous contrôlé ce plan visuellement sur les coupes ?")) return;
  show(await(await call("/api/cases/"+$("caseId").textContent+"/plan/"+$("ver").value+"/validate",{method:"POST"})).json());
});
window.makeGuide=run(async()=>{
  const r=await call("/api/guide/generate",{method:"POST",body:fd({case_id:$("caseId").textContent,plan_version:$("ver").value,gum_stl:$("gumStl").files[0]})});
  const b=await r.blob(); const a=document.createElement("a"); a.href=URL.createObjectURL(b); a.download="guide_test.stl";
  a.textContent="Télécharger guide_test.stl"; $("dl").innerHTML=""; $("dl").appendChild(a);
  show({validation:JSON.parse(r.headers.get("X-Guide-Validation")),volume_mm3:r.headers.get("X-Guide-Volume")});
});

let vid=null,vMeta=null,vReq=0,vUrl=null;
window.vPrepare=run(async()=>{
  show("Chargement de l'examen… (1 à 2 minutes pour 400 coupes)");
  const j=await(await call("/api/viewer/prepare",{method:"POST",body:fd({files:$("vFiles").files})})).json();
  vid=j.job_id; vMeta=j; $("vCtl").style.display="block"; vPlaneChange();
  show({examen_charge:true,coupes:j.counts,espacement_mm:j.spacing_xyz_mm,valeurs_min_max:[j.intensity_min,j.intensity_max]});
});
window.vPlaneChange=()=>{const n=vMeta.counts[$("vPlane").value];const r=$("vIdx");r.max=n-1;r.value=Math.floor(n/2);vDraw()};
window.vDraw=run(async()=>{
  if(!vid)return; const my=++vReq, pl=$("vPlane").value, i=$("vIdx").value;
  $("vIdxTxt").textContent=i+" / "+(vMeta.counts[pl]-1);
  const q="plane="+pl+"&index="+i+"&low="+encodeURIComponent($("vLow").value)+"&high="+encodeURIComponent($("vHigh").value);
  const b=await(await call("/api/viewer/"+vid+"/slice?"+q)).blob();
  if(my!==vReq)return; if(vUrl)URL.revokeObjectURL(vUrl); vUrl=URL.createObjectURL(b); $("vImg").src=vUrl;
});
window.vDelete=run(async()=>{
  if(!vid){show("Aucun examen chargé");return}
  await call("/api/viewer/"+vid,{method:"DELETE"}); vid=null; $("vCtl").style.display="none"; $("vImg").removeAttribute("src"); show("Examen effacé du serveur");
});

// ---- règle de mesure (dans le plan de la coupe affichée) ----
let vPts=[];
function vPitch(plane,meta,natW,natH){
  // Espacement physique moyen par pixel de la coupe effectivement rendue.
  // Les coupes coronale/sagittale sont parfois étirées par _stretch_rows côté serveur.
  const [sx,sy,sz]=meta.spacing_xyz_mm;
  const nz=meta.counts.axial, ny=meta.counts.coronal, nx=meta.counts.sagittal;
  if(plane==="axial") return [sx*nx/natW, sy*ny/natH];
  const widthMm=plane==="coronal" ? nx*sx : ny*sy;
  return [widthMm/natW, nz*sz/natH];
}
function vDist(p,q,pitch){return Math.hypot((q[0]-p[0])*pitch[0],(q[1]-p[1])*pitch[1])}
window.vRulerReset=()=>{vPts=[];vCanvas();$("vRuler").textContent="—"};
function vCanvas(){
  const im=$("vImg"),cv=$("vCv"); cv.width=im.clientWidth; cv.height=im.clientHeight;
  const g=cv.getContext("2d"); g.clearRect(0,0,cv.width,cv.height);
  if(!vPts.length)return; const k=im.clientWidth/im.naturalWidth;
  g.strokeStyle="#00e5ff";g.fillStyle="#00e5ff";g.lineWidth=2;
  vPts.forEach(p=>{g.beginPath();g.arc(p[0]*k,p[1]*k,4,0,7);g.fill()});
  if(vPts.length===2){g.beginPath();g.moveTo(vPts[0][0]*k,vPts[0][1]*k);g.lineTo(vPts[1][0]*k,vPts[1][1]*k);g.stroke()}
}
$("vImg").addEventListener("click",e=>{
  const im=e.target; if(!vMeta||!im.naturalWidth)return;
  const r=im.getBoundingClientRect();
  // clientWidth/clientHeight excluent la bordure CSS; le pointage et le canevas
  // doivent utiliser exactement cette même zone d'image, sans l'erreur de 2 px.
  const x=(e.clientX-r.left-im.clientLeft)*(im.naturalWidth/im.clientWidth);
  const y=(e.clientY-r.top-im.clientTop)*(im.naturalHeight/im.clientHeight);
  if(x<0 || y<0 || x>im.naturalWidth || y>im.naturalHeight)return;
  if(vPts.length>=2)vPts=[];
  vPts.push([x,y]); vCanvas();
  if(vPts.length===2){
    const d=vDist(vPts[0],vPts[1],vPitch($("vPlane").value,vMeta,im.naturalWidth,im.naturalHeight));
    $("vRuler").textContent=d.toFixed(1)+" mm (plan "+$("vPlane").value+", coupe "+$("vIdx").value+")";
  } else $("vRuler").textContent="1er point placé…";
});
$("vImg").addEventListener("load",()=>{vPts=[];vCanvas();$("vRuler").textContent="—"});

window.showLib=run(async()=>{show(await(await call("/api/implants")).json())});

// CSP: handlers are registered here; no inline JavaScript is required.
const bindClick = (selector, fn) => document.querySelectorAll(selector).forEach(el => el.addEventListener('click', fn));
bindClick('[data-handler-login]', () => window.login());
bindClick('[data-handler-createCase]', () => window.createCase());
bindClick('[data-handler-segment]', () => window.segment());
bindClick('[data-handler-registerIcp]', () => window.registerIcp());
bindClick('[data-handler-showLib]', () => window.showLib());
bindClick('[data-handler-savePlan]', () => window.savePlan());
bindClick('[data-handler-validatePlan]', () => window.validatePlan());
bindClick('[data-handler-makeGuide]', () => window.makeGuide());
bindClick('[data-handler-vPrepare]', () => window.vPrepare());
bindClick('[data-handler-vDelete]', () => window.vDelete());
bindClick('[data-handler-vRulerReset]', () => window.vRulerReset());
$('vPlane').addEventListener('change', () => window.vPlaneChange());
$('vIdx').addEventListener('input', () => window.vDraw());
$('vLow').addEventListener('change', () => window.vDraw());
$('vHigh').addEventListener('change', () => window.vDraw());
