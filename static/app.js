// ── CONFIG DEL SERVIDOR LOCAL ──────────────────────────────
const API = '';
let aiStatus={configured:false,remote:false,model:null};
let deleteStatus={enabled:false,authorized:false,available:false,max_batch:100,state:'disabled',token_present:false,revoked:false};

// ── UTILS ─────────────────────────────────────────────────
const MO=['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
function fd(d){
  try{
    const x=new Date(d.includes('T')?d:(d.length===10?d+'T12:00:00Z':d));
    if(isNaN(x)) return{day:'?',mo:'?',yr:'?',full:d};
    return{day:x.getUTCDate(),mo:MO[x.getUTCMonth()],yr:x.getUTCFullYear(),full:x.getUTCDate()+'/'+MO[x.getUTCMonth()]+'/'+x.getUTCFullYear()};
  }catch{return{day:'?',mo:'?',yr:'?',full:d};}
}
function safeId(id){return String(id||'').replace(/[^a-zA-Z0-9_-]/g,'');}
function gurl(id){return`https://mail.google.com/mail/u/0/#all/${safeId(id)}`;}
function attachmentUrl(messageId,a){
  const qs=new URLSearchParams({
    message_id:safeId(messageId),
    attachment_id:String(a.attachment_id||''),
    filename:String(a.filename||'adjunto'),
    mime_type:String(a.mime_type||'application/octet-stream')
  });
  return `${API}/api/attachment?${qs.toString()}`;
}
async function saveAttachment(url, filename){
  const res=await fetch(url);
  if(!res.ok)throw new Error('Error HTTP '+res.status);
  const blob=await res.blob();
  if(window.showSaveFilePicker){
    const handle=await window.showSaveFilePicker({
      suggestedName: filename,
      types:[{description:'Archivo adjunto', accept:{[blob.type||'application/octet-stream']:[`.${(filename.split('.').pop()||'bin').toLowerCase()}`]}}],
    });
    const writable=await handle.createWritable();
    await writable.write(blob);
    await writable.close();
    return;
  }
  const objectUrl=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=objectUrl;
  a.download=filename;
  a.click();
  setTimeout(()=>URL.revokeObjectURL(objectUrl), 1000);
}
async function onAttachmentClick(ev){
  const a=ev.currentTarget;
  const url=a.getAttribute('href');
  const filename=a.dataset.filename||'adjunto';
  ev.preventDefault();
  ev.stopPropagation();
  try{
    await saveAttachment(url, filename);
    toast(`Descargado ${filename}`,'ok');
  }catch(e){
    toast('Error descargando adjunto: '+e.message,'err');
  }
}
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
function lnk(s){
  return esc(s).replace(/https?:\/\/[^\s<>"']+/g,u=>{
    try{
      const raw=u.replace(/&amp;/g,'&');
      const url=new URL(raw);
      if(!['http:','https:'].includes(url.protocol))return u;
      return `<a href="${esc(url.href)}" target="_blank" rel="noopener noreferrer">${u}</a>`;
    }catch{return u;}
  });
}
function toast(msg,t='ok'){const el=document.getElementById('toast');el.textContent=msg;el.className='toast '+t+' show';clearTimeout(el._t);el._t=setTimeout(()=>el.classList.remove('show'),3000);}
function togglePanel(id){document.getElementById(id).classList.toggle('col');}

// ── STATUS CHECK ──────────────────────────────────────────
async function checkStatus(){
  const led=document.getElementById('sled'), msg=document.getElementById('smsg');
  try{
    const r=await fetch(`${API}/api/status`,{signal:AbortSignal.timeout(3000)});
    const d=await r.json();
    aiStatus=d.ai||aiStatus;
    deleteStatus=d.permanent_delete||deleteStatus;
    if(d.ok){
      led.className='sled ok';
      msg.textContent='✓ Gmail conectado — búsqueda en tiempo real disponible';
      document.getElementById('snd-add').disabled=false;
      document.getElementById('snd-inp').disabled=false;
    } else {
      led.className=d.can_search?'sled chk':'sled err';
      msg.textContent='⚠ '+(d.msg||'Gmail no disponible');
      document.getElementById('snd-add').disabled=!d.can_search;
      document.getElementById('snd-inp').disabled=!d.can_search;
    }
    return d;
  }catch{
    led.className='sled err';
    msg.textContent='✗ Servidor no disponible — python3 server.py para iniciarlo';
    document.getElementById('snd-add').disabled=true;
    document.getElementById('snd-inp').disabled=true;
    document.getElementById('search-hint').textContent='⚠ Inicia el servidor primero: python3 server.py';
    return null;
  }
}

// ── CATEGORÍAS ────────────────────────────────────────────
const CATS={
  all:   {label:'🌐 Todos',       color:'var(--v)'},
  money: {label:'💰 Monetario',   color:'var(--w)',  keys:['invoice','factura','billing','amount','price','€','$','statement','cobro','pago','cargo','receipt','recibo','extracto','importe']},
  warn:  {label:'⚠ Avisos',       color:'var(--d)',  keys:['expires tomorrow','final notice','urgent','warning','exceeded','failed','could not','expiring','aviso','alerta','urgente','expira','expirado','action required','expirará','run failed']},
  sub:   {label:'🔄 Suscripción', color:'var(--p)',  keys:['subscription','renew','renewal','suscripci','licencia','license','plan','imunify','amazon music','se renovará','renovación']},
  ssl:   {label:'🔒 SSL/Certs',   color:'#9ca3af',   keys:["let's encrypt","certificate","ssl","tls","cert","acme","expiration notice"]},
  sec:   {label:'🛡 Seguridad',   color:'#f43f5e',   keys:['security','vulnerability','cve','malware','security patch','exposed','access key','verification','unauthorized']},
  maint: {label:'🔧 Mantenimiento',color:'#22d3ee',  keys:['maintenance','scheduled','network upgrade','patch','restart','backup task','package update']},
  domain:{label:'🌐 Dominio',     color:'#60a5fa',   keys:['domain','dominio','whois','registr','alta del dominio','renovación de dominio','expire','expira','dns']},
  comm:  {label:'📢 Comunicación',color:'var(--s)',  keys:["what's new","newsletter","update","release","features","novedades","adjustments","announcement","email routing","gpt-","introducing","dev news","updated permissions","copilot"]},
};
function baseCats(e){
  const h=[e.subject||e.sub,e.body,e.from,e.tag].join(' ').toLowerCase();
  return Object.keys(CATS).filter(k=>k!=='all'&&CATS[k].keys&&CATS[k].keys.some(kw=>h.includes(kw)));
}
function senderDomain(from){
  const matches=String(from||'').toLowerCase().match(/[a-z0-9._%+-]+@([a-z0-9.-]+\.[a-z]{2,})/g);
  if(!matches||!matches.length)return'';
  return matches[matches.length-1].split('@').pop();
}
function providerMatches(from,provider){
  const domain=senderDomain(from);
  return !!domain&&(domain===provider||domain.endsWith('.'+provider));
}
function matchingRules(e){
  const h=[e.subject||e.sub,e.body||e.snippet,e.from,e.tag].join(' ').toLowerCase();
  return customRules.filter(r=>{
    const provider=!r.provider||providerMatches(e.from,r.provider);
    const keywords=!r.keywords.length||(r.keyword_operator==='all'?r.keywords.every(kw=>h.includes(kw)):r.keywords.some(kw=>h.includes(kw)));
    return provider&&keywords&&(r.provider||r.keywords.length);
  });
}
function cats(e){
  const out=baseCats(e);
  matchingRules(e).forEach(r=>{if(!out.includes(r.category))out.push(r.category);});
  return out;
}
const SEVERITY_META={
  high:{label:'Alta', color:'var(--d)'},
  medium:{label:'Media', color:'var(--o)'},
  low:{label:'Baja', color:'var(--s)'},
};
const SEVERITY_ORDER={high:0,medium:1,low:2};
const CATEGORY_SEVERITY={warn:'high',sec:'high',ssl:'high',money:'medium',sub:'medium',domain:'medium',maint:'medium',comm:'low'};
const CATEGORY_SEVERITY_REASON={
  warn:'Aviso urgente o fallo detectado',
  sec:'Seguridad o vulnerabilidad detectada',
  ssl:'Certificado o TLS pendiente',
  money:'Factura, cobro o coste detectado',
  sub:'Renovación o suscripción pendiente',
  domain:'Dominio o vencimiento detectado',
  maint:'Mantenimiento o actualización programada',
  comm:'Comunicación informativa',
};
function messageCategories(e){return cats(e);}
function primaryCategory(e){
  const cs=messageCategories(e);
  return ['warn','sec','ssl','money','sub','domain','maint','comm'].find(k=>cs.includes(k))||cs[0]||'comm';
}
function messageSeverity(e){
  const base=CATEGORY_SEVERITY[primaryCategory(e)]||'low';
  return matchingRules(e).reduce((severity,r)=>SEVERITY_ORDER[r.severity]<SEVERITY_ORDER[severity]?r.severity:severity,base);
}
function severityReason(e){
  const severity=messageSeverity(e);
  const rule=matchingRules(e).find(r=>r.severity===severity);
  return rule?`Regla personalizada: ${rule.label}`:(CATEGORY_SEVERITY_REASON[primaryCategory(e)]||'Sin categorías de riesgo');
}
function severityLabel(e){return SEVERITY_META[messageSeverity(e)].label;}
function severityColor(e){return SEVERITY_META[messageSeverity(e)].color;}
function severityRank(e){return SEVERITY_ORDER[messageSeverity(e)]??2;}
function providerName(e){
  const raw=String(e.provider||e.tag||e.from||'Email');
  return raw.split('·')[0].trim()||'Email';
}
function providerKey(e){return providerName(e).toLowerCase();}
let customRules=[];

// ── ESTADO ────────────────────────────────────────────────
const FIXED=[{dom:'vultr.com',label:'Vultr',color:'var(--v)',fixed:true},{dom:'plesk.com',label:'Plesk',color:'var(--p)',fixed:true},{dom:'gmail.com',label:'Servidor',color:'var(--s)',fixed:true}];
const KNOWN=[
  {dom:'dondominio.com',label:'DonDominio',color:'#60a5fa'},{dom:'cloudflare.com',label:'Cloudflare',color:'#f97316'},
  {dom:'amazon.com',label:'Amazon/AWS',color:'#facc15'},{dom:'letsencrypt.org',label:"Let's Encrypt",color:'#34d399'},
  {dom:'github.com',label:'GitHub',color:'#e2e8f0'},{dom:'stripe.com',label:'Stripe',color:'#818cf8'},
  {dom:'anthropic.com',label:'Anthropic',color:'#fb923c'},{dom:'paypal.com',label:'PayPal',color:'#38bdf8'},
  {dom:'openai.com',label:'OpenAI',color:'#4ade80'},{dom:'wordpress.com',label:'WordPress',color:'#67e8f9'},
  {dom:'namecheap.com',label:'Namecheap',color:'#c084fc'},{dom:'web.dev',label:'web.dev',color:'#34d399'},
];
const PAL=['#fb923c','#22d3ee','#a3e635','#e879f9','#facc15','#c084fc','#f97316','#60a5fa','#4ade80','#f43f5e'];

let activeEmails=[];
let customSrcs=[];
let cf='all',cq='',activeCat='all',selMode=false;
const deleted=new Set(),selected=new Set(),openMessages=new Set();
let pendingDel=[],expData=null,expFmt='md',expScope=null;
let summaryDays=30,summaryData=null;
let stateReady=false,saveTimer=null,saveInFlight=false,savePending=false,editingRuleId=null;
let hiddenReviewItems=[],deletionAudit=[];
const hiddenSelected=new Set();
let hiddenReviewPage=1,hiddenReviewPages=1,hiddenReviewTotal=0,hiddenReviewPageSize=20,hiddenReviewLoading=false,hiddenRangeAnchorId=null;
let hiddenOrphanPurgePending=false;

function srcColor(e){
  if(e.src==='v') return 'var(--v)';
  if(e.src==='p') return 'var(--p)';
  if(e.src==='s') return 'var(--s)';
  const k=KNOWN.find(k=>e.from&&e.from.includes(k.dom));if(k)return k.color;
  const c=customSrcs.find(c=>e.from&&e.from.includes(c.dom));return c?c.color:'var(--o)';
}
function senderLabel(dom){
  const k=KNOWN.find(k=>k.dom===dom);return k?k.label:dom;
}
function senderColor(dom){
  const f=FIXED.find(f=>f.dom===dom);if(f)return f.color;
  const k=KNOWN.find(k=>k.dom===dom);if(k)return k.color;
  const c=customSrcs.find(c=>c.dom===dom);return c?c.color:'var(--o)';
}
function setSrcFilter(f){
  document.querySelectorAll('.src').forEach(x=>{x.classList.remove('on');x.style.cssText='';});
  const btn=document.querySelector(`.src[data-f="${f}"]`)||document.querySelector('.src[data-f="all"]');
  btn.classList.add('on');
  const col=FC[btn.dataset.f]||'var(--v)';
  btn.style.cssText=`background:${col};border-color:${col};color:#fff`;
  cf=btn.dataset.f;
}
function focusSender(dom){
  cq=dom;
  activeCat='all';
  document.getElementById('srch').value=dom;
  setSrcFilter('all');
}

// ── ESTADO LOCAL PERSISTENTE ─────────────────────────────
function currentState(){
  return {
    version:1,
    custom_sources:customSrcs.map(s=>({dom:s.dom,label:s.label,color:s.color})),
    custom_rules:customRules.map(r=>({...r,keywords:[...r.keywords]})),
    hidden_ids:[...deleted],
    preferences:{source_filter:cf,category_filter:activeCat,search_query:cq}
  };
}
function applyState(state){
  const s=state||{};
  customSrcs=Array.isArray(s.custom_sources)?s.custom_sources.map(x=>({
    dom:String(x.dom||'').toLowerCase(),
    label:String(x.label||x.dom||''),
    color:String(x.color||'var(--o)'),
    fixed:false
  })).filter(x=>x.dom):[];
  customRules=Array.isArray(s.custom_rules)?s.custom_rules.map(r=>({
    id:String(r.id||''),
    label:String(r.label||'Regla personalizada'),
    provider:String(r.provider||'').toLowerCase(),
    keywords:Array.isArray(r.keywords)?r.keywords.map(x=>String(x).toLowerCase()).filter(Boolean):[],
    keyword_operator:r.keyword_operator==='all'?'all':'any',
    category:CATS[r.category]?r.category:'comm',
    severity:SEVERITY_META[r.severity]?r.severity:'low'
  })).filter(r=>r.id):[];
  deleted.clear();
  (Array.isArray(s.hidden_ids)?s.hidden_ids:[]).forEach(id=>deleted.add(String(id)));
  deletionAudit=Array.isArray(s.deletion_audit)?s.deletion_audit:[];
  const p=s.preferences||{};
  cq=String(p.search_query||'');
  activeCat=CATS[p.category_filter]?p.category_filter:'all';
  document.getElementById('srch').value=cq;
  const savedFilter=['all','v','p','s','cu'].includes(p.source_filter)?p.source_filter:'all';
  setSrcFilter(savedFilter==='cu'&&!customSrcs.length?'all':savedFilter);
  document.getElementById('cu-btn').style.display=customSrcs.length?'':'none';
}
async function loadState(){
  try{
    const r=await fetch(`${API}/api/state`,{signal:AbortSignal.timeout(3000)});
    if(!r.ok)throw new Error('Error HTTP '+r.status);
    const d=await r.json();
    applyState(d.state||{});
  }catch(e){
    toast('No se pudo cargar el estado local: '+e.message,'err');
  }finally{
    stateReady=true;
  }
}
function queueSaveState(){
  if(!stateReady)return;
  savePending=true;
  clearTimeout(saveTimer);
  saveTimer=setTimeout(saveState,350);
}
async function flushSaveState(){
  if(!stateReady)return;
  clearTimeout(saveTimer);
  savePending=true;
  await saveState();
}
async function saveState(){
  if(!stateReady||saveInFlight)return;
  saveInFlight=true;
  try{
    do{
      savePending=false;
      const r=await fetch(`${API}/api/state`,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({state:currentState()})
      });
      if(!r.ok){
        const err=await r.json().catch(()=>({error:'Error HTTP '+r.status}));
        throw new Error(err.detail||err.error||('Error HTTP '+r.status));
      }
    }while(savePending);
  }catch(e){
    toast('No se pudo guardar estado local: '+e.message,'err');
  }finally{
    saveInFlight=false;
  }
}
async function refreshSourcesFromGmail(){
  const sources=[...FIXED,...customSrcs];
  if(!sources.length)return;
  let added=0;
  const existing=new Set(activeEmails.map(e=>e.id));
  for(const s of sources){
    const emails=await searchGmail(s.dom,{busy:false,errors:false});
    if(!Array.isArray(emails))continue;
    emails.map(e=>({...e,src:s.fixed?s.dom==='vultr.com'?'v':s.dom==='plesk.com'?'p':'s':'cu',sub:e.subject||e.sub||'(sin asunto)'})).forEach(e=>{
      if(!existing.has(e.id)){existing.add(e.id);activeEmails.push(e);added++;}
    });
  }
  if(added>0){
    renderSenders();renderCats();render();
    toast(`✓ ${added} correo${added!==1?'s':''} recuperado${added!==1?'s':''} de fuentes guardadas`,'ok');
  }
}
async function hydrateMessageAttachments(email){
  const sources=activeEmails.filter(item=>item.id===email.id);
  if(!sources.length)sources.push(email);
  const source=sources[0];
  if(source.attachments_checked||source._attLoading)return;
  sources.forEach(item=>{item._attLoading=true;});
  try{
    const r=await fetch(`${API}/api/message?message_id=${encodeURIComponent(source.id)}`,{signal:AbortSignal.timeout(15000)});
    if(!r.ok)throw new Error('Error HTTP '+r.status);
    const d=await r.json();
    const live=d.email||{};
    sources.forEach(item=>{
      item.attachments=Array.isArray(live.attachments)?live.attachments:[];
      item.attachments_checked=true;
      item.attachments_error='';
    });
  }catch(e){
    sources.forEach(item=>{
      item.attachments=[];
      item.attachments_checked=true;
      item.attachments_error=e.message||'No se pudieron comprobar los adjuntos';
    });
  }finally{
    sources.forEach(item=>{item._attLoading=false;});
    render();
  }
}

// ── BÚSQUEDA REAL EN GMAIL ────────────────────────────────
async function searchGmail(sender,opts={}){
  const busy=opts.busy!==false,showErr=opts.errors!==false;
  const btn=document.getElementById('snd-add');
  if(busy){
    btn.disabled=true;
    btn.innerHTML='<span class="spin"></span>Buscando…';
  }
  try{
    const r=await fetch(`${API}/api/search?sender=${encodeURIComponent(sender)}&max=30`);
    if(!r.ok){
      const err=await r.json().catch(()=>({error:'Error HTTP '+r.status}));
      throw new Error(err.detail||err.error||('Error HTTP '+r.status));
    }
    const d=await r.json();
    return d.emails||[];
  }catch(e){
    if(showErr)toast('Error buscando en Gmail: '+e.message,'err');
    return null;
  }finally{
    if(busy){
      btn.disabled=false;
      btn.textContent='+ Buscar en Gmail';
    }
  }
}

async function addSrc(raw){
  const val=raw.trim().toLowerCase().replace(/^@/,'');
  if(!val){toast('Introduce un dominio o email','err');return;}
  const dom=val.includes('@')?val.split('@')[1]:val;
  const query=val.includes('@')?val:dom;
  const validDom=/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$/;
  const validEmail=/^[a-z0-9._%+-]+@[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$/;
  if(!validDom.test(val)&&!validEmail.test(val)){
    toast('Usa un dominio o email válido','err');
    return;
  }

  // Color
  const known=KNOWN.find(k=>dom.includes(k.dom)||k.dom.includes(dom));
  const color=known?known.color:PAL[customSrcs.length%PAL.length];
  const label=known?known.label:dom;

  // Buscar en Gmail en tiempo real
  toast(`Localizando correos de ${query} en Gmail…`,'ok');
  const emails=await searchGmail(query);
  if(emails===null)return;
  if(emails.length===0){
    toast(`${label}: no se encontraron correos`,'err');
    return;
  }

  // Normalizar campo subject → sub
  const normalized=emails.map(e=>({...e,sub:e.subject||e.sub||'(sin asunto)'}));

  // Añadir solo los nuevos
  const existing=new Set(activeEmails.map(e=>e.id));
  const nuevos=normalized.filter(e=>!existing.has(e.id));
  activeEmails=[...activeEmails,...nuevos];

  if(![...FIXED,...customSrcs].some(s=>s.dom===dom)){
    customSrcs.push({dom,label,color,fixed:false});
    document.getElementById('cu-btn').style.display='';
  }
  document.getElementById('snd-inp').value='';
  focusSender(dom);
  renderSenders();
  renderCats();
  render();
  queueSaveState();
  toast(`✓ ${label}: ${emails.length} correo${emails.length!==1?'s':''} localizado${emails.length!==1?'s':''}; ${nuevos.length} incorporado${nuevos.length!==1?'s':''}`,'ok');
}

// ── RENDER SENDERS ────────────────────────────────────────
function renderSenders(){
  const grid=document.getElementById('snd-chips');grid.innerHTML='';
  [...FIXED,...customSrcs].forEach(s=>{
    const cnt=activeEmails.filter(e=>!deleted.has(e.id)&&e.from&&e.from.includes(s.dom)).length;
    const chip=document.createElement('div');
    chip.className='schip';
    chip.style.cssText=`border-color:${s.color}88;color:${s.color};background:${s.color}14`;
    chip.innerHTML=`<span>${esc(s.label)}</span><span class="count" style="opacity:.55;margin-left:3px;">(${cnt})</span>`
      +(s.fixed?'':` <button class="xcl" data-d="${esc(s.dom)}">✕</button>`);
    if(!s.fixed) chip.querySelector('.xcl').addEventListener('click',ev=>{ev.stopPropagation();removeSrc(s.dom);});
    grid.appendChild(chip);
  });
  document.getElementById('snd-tag').textContent=`${FIXED.length+customSrcs.length} fuentes`;
  renderKD();renderLegend();
}
function renderKD(){
  const grid=document.getElementById('kd-grid');grid.innerHTML='';
  KNOWN.forEach(k=>{
    const done=customSrcs.some(c=>c.dom===k.dom);
    const chip=document.createElement('div');
    chip.className='kdchip'+(done?' done':'');
    chip.style.cssText=`border-color:${k.color}88;color:${k.color};background:${k.color}14`;
    chip.textContent=(done?'✓ ':'')+k.label;
    if(!done) chip.addEventListener('click',()=>addSrc(k.dom));
    grid.appendChild(chip);
  });
}
function renderLegend(){
  const bar=document.getElementById('lgnd');bar.innerHTML='';
  [...FIXED,...customSrcs].forEach(s=>{
    const li=document.createElement('div');li.className='li';
    li.innerHTML=`<div class="ld" style="background:${s.color}"></div>${esc(s.label)}`;
    bar.appendChild(li);
  });
}
function removeSrc(dom){
  const s=customSrcs.find(x=>x.dom===dom);
  customSrcs=customSrcs.filter(c=>c.dom!==dom);
  activeEmails=activeEmails.filter(e=>e.src!=='cu'||!e.from||!e.from.includes(dom));
  renderSenders();if(cf==='cu'&&!customSrcs.length)setSrcFilter('all');
  queueSaveState();
  toast(`${s?.label||dom} eliminado`,'ok');render();
}

document.getElementById('snd-add').addEventListener('click',()=>addSrc(document.getElementById('snd-inp').value));
document.getElementById('snd-inp').addEventListener('keydown',e=>{if(e.key==='Enter')addSrc(document.getElementById('snd-inp').value);});

// ── REGLAS PERSONALIZADAS ────────────────────────────────
function renderRules(){
  const list=document.getElementById('rule-list');
  list.innerHTML='';
  document.getElementById('rules-tag').textContent=customRules.length;
  if(!customRules.length){
    list.innerHTML='<div class="empty">Sin reglas personalizadas. Se aplican las reglas base.</div>';
    return;
  }
  customRules.forEach(rule=>{
    const item=document.createElement('div');
    item.className='rule-item';
    const conditions=[rule.provider?`Proveedor: ${rule.provider}`:'',rule.keywords.length?`Texto (${rule.keyword_operator==='all'?'todas':'alguna'}): ${rule.keywords.join(', ')}`:''].filter(Boolean).join(' · ');
    item.innerHTML=`<div class="rule-main"><div class="rule-name">${esc(rule.label)} · ${esc(CATS[rule.category].label)} · ${esc(SEVERITY_META[rule.severity].label)}</div><div class="rule-desc">${esc(conditions)}</div></div><div class="rule-actions"><button class="rule-edit" type="button">Editar</button><button class="rule-del" type="button">Eliminar</button></div>`;
    item.querySelector('.rule-edit').addEventListener('click',()=>{
      editingRuleId=rule.id;
      document.getElementById('rule-label').value=rule.label;
      document.getElementById('rule-provider').value=rule.provider;
      document.getElementById('rule-keywords').value=rule.keywords.join(', ');
      document.getElementById('rule-keyword-operator').value=rule.keyword_operator||'any';
      document.getElementById('rule-category').value=rule.category;
      document.getElementById('rule-severity').value=rule.severity;
      document.getElementById('rule-add').textContent='Guardar cambios';
      document.getElementById('rule-label').focus();
    });
    item.querySelector('.rule-del').addEventListener('click',()=>{
      customRules=customRules.filter(r=>r.id!==rule.id);
      if(editingRuleId===rule.id)resetRuleForm();
      renderRules();renderCats();render();queueSaveState();
      toast(`Regla "${rule.label}" eliminada`,'ok');
    });
    list.appendChild(item);
  });
}
function resetRuleForm(){
  editingRuleId=null;
  ['rule-label','rule-provider','rule-keywords'].forEach(id=>document.getElementById(id).value='');
  document.getElementById('rule-keyword-operator').value='any';
  document.getElementById('rule-add').textContent='+ Añadir regla';
}
function addRule(){
  const label=document.getElementById('rule-label').value.trim()||'Regla personalizada';
  const provider=document.getElementById('rule-provider').value.trim().toLowerCase().replace(/^@/,'');
  const keywords=document.getElementById('rule-keywords').value.split(',').map(x=>x.trim().toLowerCase()).filter(Boolean).slice(0,20);
  const keyword_operator=document.getElementById('rule-keyword-operator').value==='all'?'all':'any';
  const category=document.getElementById('rule-category').value;
  const severity=document.getElementById('rule-severity').value;
  const validDomain=/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$/;
  if(!provider&&!keywords.length){toast('Indica proveedor, palabras clave o ambos','err');return;}
  if(provider&&!validDomain.test(provider)){toast('Usa un dominio de proveedor válido','err');return;}
  const rule={id:editingRuleId||`rule_${Date.now().toString(36)}`,label,provider,keywords,keyword_operator,category,severity};
  if(editingRuleId)customRules=customRules.map(r=>r.id===editingRuleId?rule:r);
  else customRules.push(rule);
  const action=editingRuleId?'actualizada':'añadida';
  resetRuleForm();
  renderRules();renderCats();render();queueSaveState();
  toast(`Regla "${label}" ${action}`,'ok');
}
Object.entries(CATS).filter(([key])=>key!=='all').forEach(([key,value])=>{
  const option=document.createElement('option');
  option.value=key;option.textContent=value.label.replace(/^[^\p{L}\p{N}]+\s*/u,'');
  document.getElementById('rule-category').appendChild(option);
});
document.getElementById('rule-add').addEventListener('click',addRule);
document.getElementById('rule-keywords').addEventListener('keydown',e=>{if(e.key==='Enter')addRule();});

// ── CAT CHIPS ─────────────────────────────────────────────
function renderCats(){
  const grid=document.getElementById('cat-grid');grid.innerHTML='';
  Object.entries(CATS).forEach(([k,v])=>{
    const chip=document.createElement('div');
    chip.className='cchip'+(activeCat===k?' on':'');
    chip.dataset.cat=k;
    chip.style.cssText=`border-color:${v.color}66;color:${v.color};${activeCat===k?`background:${v.color}30`:``}`;
    chip.innerHTML=`${v.label} <span class="cn" id="cn-${k}"></span>`;
    chip.addEventListener('click',()=>{activeCat=k;renderCats();render();queueSaveState();});
    grid.appendChild(chip);
  });
}
function updateCatCounts(){
  const base=filteredBySrc();
  Object.keys(CATS).forEach(k=>{
    const el=document.getElementById('cn-'+k);
    if(el)el.textContent=k==='all'?base.length:base.filter(e=>cats(e).includes(k)).length;
  });
}

// ── FILTROS ───────────────────────────────────────────────
function normSub(e){return e.sub||e.subject||'(sin asunto)';}
function filteredBySrc(){
  const q=cq.toLowerCase().trim();
  return activeEmails.filter(e=>{
    if(deleted.has(e.id))return false;
    const ms=cf==='all'||(cf==='v'&&e.src==='v')||(cf==='p'&&e.src==='p')||(cf==='s'&&e.src==='s')||(cf==='cu'&&e.src==='cu');
    const mq=!q||[normSub(e),e.body,e.from,e.to,e.cc||'',e.tag].join(' ').toLowerCase().includes(q);
    return ms&&mq;
  });
}
function filtered(){const b=filteredBySrc();return activeCat==='all'?b:b.filter(e=>cats(e).includes(activeCat));}

function itemMeta(e){
  const categories=messageCategories(e);
  const severity=messageSeverity(e);
  const reason=severityReason(e);
  const provider=providerName(e);
  const dt=fd(e.date||'');
  return {
    ...e,
    _categories:categories,
    _severity:severity,
    _severityReason:reason,
    _provider:provider,
    _date:dt,
    _summary:normSub(e),
    _snippet:(e.body||e.snippet||'').split('\n')[0]||'',
  };
}
function queueItems(){
  return filtered()
    .map(itemMeta)
    .sort((a,b)=>{
      const sev=severityRank(a)-severityRank(b);
      if(sev!==0)return sev;
      const da=(b.date||'').localeCompare(a.date||'');
      if(da!==0)return da;
      const pa=providerKey(a).localeCompare(providerKey(b));
      if(pa!==0)return pa;
      return a._summary.localeCompare(b._summary);
    });
}
function groupItems(items){
  const groups={};
  items.forEach(e=>{(groups[e._provider]||(groups[e._provider]=[])).push(e);});
  return Object.entries(groups).sort((a,b)=>{
    const sa=Math.min(...a[1].map(severityRank));
    const sb=Math.min(...b[1].map(severityRank));
    if(sa!==sb)return sa-sb;
    return a[0].localeCompare(b[0]);
  });
}
function groupStats(list){
  const out={high:0,medium:0,low:0};
  list.forEach(e=>{out[messageSeverity(e)]=(out[messageSeverity(e)]||0)+1;});
  return out;
}
function severityBadge(e){
  const sev=messageSeverity(e);
  return `<span class="sev ${sev}">${esc(SEVERITY_META[sev].label)}</span>`;
}
function providerBadge(e){
  const col=srcColor(e);
  return `<span class="ctg" style="background:${col}22;border:1px solid ${col}55;color:${col}">${esc(e._provider||providerName(e))}</span>`;
}
function categoryBadges(e){
  return e._categories.slice(0,3).map(k=>`<span class="cbdg" style="background:${CATS[k].color}22;border:1px solid ${CATS[k].color}44;color:${CATS[k].color}">${CATS[k].label}</span>`).join('');
}
function attachmentBadge(e, atts, attChecked){
  return e.attachments_error
    ?`<span class="att-none" aria-label="No se pudieron comprobar los adjuntos" title="${esc(e.attachments_error)}">📎 !</span>`
    :!attChecked
    ?`<span class="att-pending" aria-label="Comprobando adjuntos">📎 ...</span>`
    :atts.length
    ?`<a class="att-badge att-open" href="${esc(attachmentUrl(e.id,atts[0]))}" data-filename="${esc(atts[0].filename||'adjunto')}" download="${esc(atts[0].filename||'adjunto')}" aria-label="Descargar adjunto ${esc(atts[0].filename||'adjunto')}">📎 ${atts.length} adj.</a>`
    :`<span class="att-none" aria-label="Sin adjuntos">📎 0 adj.</span>`;
}
function attachmentDetail(e, atts, attChecked){
  return e.attachments_error
    ?`<div class="efr"><span class="efk">Adj.</span><span class="efv att-empty">No se pudieron comprobar los adjuntos.</span></div>`
    :!attChecked
    ?`<div class="efr"><span class="efk">Adj.</span><span class="efv att-loading">Comprobando adjuntos en Gmail...</span></div>`
    :atts.length
    ?`<div class="efr"><span class="efk">Adj.</span><span class="efv att-list">${atts.map(a=>`<a class="att-link att-open" href="${esc(attachmentUrl(e.id,a))}" data-filename="${esc(a.filename||'adjunto')}" download="${esc(a.filename||'adjunto')}" aria-label="Descargar adjunto ${esc(a.filename||'adjunto')}">📎 ${esc(a.filename||'adjunto')}</a>`).join('')}</span></div>`
    :`<div class="efr"><span class="efk">Adj.</span><span class="efv att-empty">Sin adjuntos</span></div>`;
}

// ── RENDER CARDS ──────────────────────────────────────────
function render(){
  const list=document.getElementById('list');list.innerHTML='';
  const fil=queueItems();
  if(!fil.length){
    list.innerHTML=`<div class="empty"><b>Sin acciones pendientes</b><br>La cola está vacía. Ajusta filtros o añade remitentes para localizar correos accionables.</div>`;
  } else {
    groupItems(fil).forEach(([provider,items])=>{
      const sec=document.createElement('div');sec.className='grp';
      const header=document.createElement('div');
      const stats=groupStats(items);
      const severity=items.reduce((acc,e)=>severityRank(e)<severityRank(acc)?e:acc,items[0]);
      const sev=messageSeverity(severity);
      header.className=`grph grp${sev}`;
      header.innerHTML=`
        <div class="grpt">
          <div class="grpn">${esc(provider)}</div>
          <div class="grps">${items.length} correo${items.length!==1?'s':''} · ${stats.high} alta${stats.high!==1?'s':''} · ${stats.medium} media${stats.medium!==1?'s':''} · ${stats.low} baja${stats.low!==1?'s':''}</div>
        </div>
        <span class="sev ${sev}">${esc(SEVERITY_META[sev].label)}</span>
      `;
      sec.appendChild(header);
      items.forEach(e=>{
        const sub=e._summary;
        const dt=e._date;
        const atts=Array.isArray(e.attachments)?e.attachments:[];
        const attChecked=e.attachments_checked===true;
        const col=srcColor(e);
        const cr=e._categories.length>0?'cr-'+e._categories[0]:'';
        const sev=messageSeverity(e);
        const c=document.createElement('div');
        c.className=`card ${e.src==='cu'?'cu':e.src} ${cr} sev-${sev}${selected.has(e.id)?' sel':''}${selMode?' sm':''}${openMessages.has(e.id)?' open':''}`;
        c.dataset.id=e.id;
        c.innerHTML=`
<label class="ck"><input type="checkbox" ${selected.has(e.id)?'checked':''}></label>
<div class="ch">
  <div class="cdt"><span class="dy">${esc(dt.day)}</span>${esc(dt.mo)} ${esc(dt.yr)}</div>
  <div class="cm">
    <div class="csb">${esc(sub)}</div>
    <div class="cbg">${severityBadge(e)}${categoryBadges(e)}${attachmentBadge(e,atts,attChecked)}</div>
    <div class="cmet"><b>${esc(SEVERITY_META[sev].label)}</b> · ${esc(severityReason(e))}</div>
    <div class="csp">${esc(e._snippet)}</div>
  </div>
  <div class="crt">
    ${providerBadge(e)}
    ${severityBadge(e)}
    <span class="chv">▾</span>
  </div>
</div>
<div class="cbp">
  <div class="ef">
    <div class="efr"><span class="efk">De</span><span class="efv">${esc(e.from||'')}</span></div>
    <div class="efr"><span class="efk">Para</span><span class="efv">${esc(e.to||'')}</span></div>
    ${e.cc?`<div class="efr"><span class="efk">CC</span><span class="efv">${esc(e.cc)}</span></div>`:''}
    <div class="efr"><span class="efk">Asunto</span><span class="efv">${esc(sub)}</span></div>
    <div class="efr"><span class="efk">Fecha</span><span class="efv">${esc(dt.full)}</span></div>
    ${e._categories.length?`<div class="efr"><span class="efk">Cats</span><span class="efv">${e._categories.map(k=>CATS[k].label).join(' · ')}</span></div>`:''}
    ${attachmentDetail(e,atts,attChecked)}
  </div>
  <div class="ebody">${lnk(e.body||e.snippet||'')}</div>
  <div class="ca-row">
    <a class="ca gm" href="${gurl(e.id)}" target="_blank" rel="noopener">✉ Gmail</a>
    <button class="ca dl" data-id="${e.id}">🙈 Ocultar</button>
  </div>
</div>`;
        c.querySelector('.ch').addEventListener('click',()=>{
          if(selMode){togSel(e.id,c);return;}
          if(openMessages.has(e.id))openMessages.delete(e.id);else openMessages.add(e.id);
          c.classList.toggle('open',openMessages.has(e.id));
          if(openMessages.has(e.id))hydrateMessageAttachments(e);
        });
        c.querySelector('input[type=checkbox]').addEventListener('change',()=>togSel(e.id,c));
        c.querySelector('.dl').addEventListener('click',ev=>{ev.stopPropagation();openDel([e.id]);});
      c.querySelectorAll('.att-open').forEach(a=>a.addEventListener('click',onAttachmentClick));
        sec.appendChild(c);
      });
      list.appendChild(sec);
    });
  }
  const tot=activeEmails.filter(e=>!deleted.has(e.id)).length;
  const base=filteredBySrc().map(itemMeta);
  const sevCounts=fil.reduce((acc,e)=>{acc[messageSeverity(e)]++;return acc;},{high:0,medium:0,low:0});
  document.getElementById('stbar').innerHTML=
    `<span>${fil.length} de ${tot}</span>`+
    `<span class="sseg" style="color:var(--d)">▲ ${sevCounts.high}</span>`+
    `<span class="sseg" style="color:var(--o)">◆ ${sevCounts.medium}</span>`+
    `<span class="sseg" style="color:var(--s)">● ${sevCounts.low}</span>`;
  document.getElementById('total-pill').textContent=`${tot} correos`;
  updateSelCount();updateCatCounts();updateHiddenBar();
}

function updateHiddenBar(){
  const bar=document.getElementById('hidden-bar'),msg=document.getElementById('hidden-msg');
  const n=deleted.size;
  bar.hidden=n===0;
  msg.textContent=`${n} correo${n!==1?'s':''} oculto${n!==1?'s':''} localmente · No afecta a Gmail`;
}

function hiddenTitle(item){
  if(item.status!=='available')return `ID ${item.id}`;
  return item.email?.subject||item.email?.sub||`ID ${item.id}`;
}
function hiddenSelectionStats(){
  const itemsById=new Map(hiddenReviewItems.map(item=>[item.id,item]));
  let available=0;
  let orphan=0;
  let unavailable=0;
  hiddenSelected.forEach(id=>{
    const status=itemsById.get(id)?.status;
    if(status==='available') available++;
    else if(status==='orphan') orphan++;
    else unavailable++;
  });
  return {available, orphan, unavailable};
}
function hiddenOrderIds(){
  return [...deleted];
}
function hiddenIndexMap(){
  const map=new Map();
  hiddenOrderIds().forEach((id,index)=>map.set(id,index));
  return map;
}
function hiddenSelectAllCurrentPage(){
  hiddenReviewItems.forEach(item=>hiddenSelected.add(item.id));
  renderHiddenReview();
}
function hiddenClearSelection(){
  hiddenSelected.clear();
  hiddenRangeAnchorId=null;
  renderHiddenReview();
}
async function purgeOrphanMessages(ids, opts={}){
  const unique=[...new Set((ids||[]).map(id=>String(id||'').trim()).filter(Boolean))];
  if(!unique.length)return 0;
  const idSet=new Set(unique);
  const removedFromVisible=activeEmails.filter(e=>idSet.has(e.id)).length;
  activeEmails=activeEmails.filter(e=>!idSet.has(e.id));
  unique.forEach(id=>{
    deleted.delete(id);
    selected.delete(id);
    openMessages.delete(id);
    hiddenSelected.delete(id);
  });
  hiddenRangeAnchorId=null;
  await flushSaveState();
  render();
  if(!opts.silent){
    toast(`${unique.length} huérfano${unique.length===1?'':'s'} eliminado${unique.length===1?'':'s'} de la app`,'ok');
  }
  return removedFromVisible;
}
function hiddenToggleItem(item,ev){
  const order=hiddenOrderIds();
  const indexById=hiddenIndexMap();
  const id=item.id;
  if(ev.shiftKey && hiddenRangeAnchorId && indexById.has(hiddenRangeAnchorId) && indexById.has(id)){
    const from=indexById.get(hiddenRangeAnchorId);
    const to=indexById.get(id);
    const [start,end]=from<to?[from,to]:[to,from];
    order.slice(start,end+1).forEach(messageId=>hiddenSelected.add(messageId));
  }else if(ev.metaKey||ev.ctrlKey){
    hiddenSelected.has(id)?hiddenSelected.delete(id):hiddenSelected.add(id);
    hiddenRangeAnchorId=id;
  }else{
    hiddenSelected.has(id)?hiddenSelected.delete(id):hiddenSelected.add(id);
    hiddenRangeAnchorId=id;
  }
  renderHiddenReview();
}
function renderHiddenReview(){
  const list=document.getElementById('hidden-list');
  list.innerHTML='';
  if(!hiddenReviewItems.length){
    list.innerHTML='<div class="empty">No hay correos ocultos para revisar.</div>';
  }else{
    hiddenReviewItems.forEach(item=>{
      const row=document.createElement('label');
      row.className='hidden-item'+(hiddenSelected.has(item.id)?' sel':'');
      const meta=item.status==='available'
        ?`${item.email?.from||'Remitente desconocido'} · ${item.email?.date||'Fecha desconocida'}`
        :(item.detail||'No disponible en Gmail');
      const stateClass=item.status==='available'?'':(item.status==='orphan'?'orphan':'unavailable');
      const stateLabel=item.status==='available'?'Disponible':(item.status==='orphan'?'Huérfano':'No disponible');
      row.innerHTML=`<input type="checkbox" ${hiddenSelected.has(item.id)?'checked':''} aria-label="Seleccionar oculto"><div class="hidden-main"><div class="hidden-subject">${esc(hiddenTitle(item))}</div><div class="hidden-meta">${esc(meta)}</div></div><span class="hidden-state ${stateClass}">${stateLabel}</span>`;
      row.querySelector('input').addEventListener('click',ev=>{
        ev.preventDefault();
        ev.stopPropagation();
        hiddenToggleItem(item,ev);
      });
      list.appendChild(row);
    });
  }
  updateHiddenSelection();
  renderHiddenPager();
}
function updateHiddenSelection(){
  const count=hiddenSelected.size;
  const limit=deleteStatus.max_batch||100;
  const {orphan, unavailable}=hiddenSelectionStats();
  const expected=`ELIMINAR PERMANENTEMENTE ${count}`;
  const limitNote=count>limit?`Máximo ${limit} por lote. Reduce la selección para continuar.`:'';
  const localNote=orphan?`${orphan} huérfano${orphan===1?'':'s'} · puedes limpiar su información local.`:'';
  const errorNote=unavailable?`${unavailable} no disponible${unavailable===1?'':'s'} temporalmente.`:'';
  document.getElementById('hidden-selected').textContent=`${count} seleccionado${count===1?'':'s'}`;
  document.getElementById('hidden-limit').textContent=[limitNote, localNote, errorNote].filter(Boolean).join(' ');
  document.getElementById('delete-confirm-label').textContent=count?`Escribe exactamente: ${expected}`:'Selecciona mensajes para generar la confirmación.';
  const input=document.getElementById('delete-confirm');
  input.placeholder=count?expected:'ELIMINAR PERMANENTEMENTE N';
  const canDelete=count>0&&count<=limit&&deleteStatus.enabled&&deleteStatus.authorized&&input.value===expected;
  const canForget=orphan>0;
  document.getElementById('hidden-restore').disabled=count===0;
  document.getElementById('hidden-delete').disabled=!canDelete;
  document.getElementById('hidden-forget').disabled=!canForget;
}
function renderHiddenPager(){
  const info=document.getElementById('hidden-page');
  const prev=document.getElementById('hidden-prev');
  const next=document.getElementById('hidden-next');
  const total=hiddenReviewTotal||hiddenReviewItems.length||0;
  const pages=hiddenReviewPages||1;
  info.textContent=total?`Página ${hiddenReviewPage} de ${pages} · ${total} ocultos`:'Sin ocultos';
  prev.disabled=hiddenReviewLoading||hiddenReviewPage<=1;
  next.disabled=hiddenReviewLoading||hiddenReviewPage>=pages;
}
function renderDeleteStatus(){
  const text=document.getElementById('delete-status');
  const auth=document.getElementById('delete-authorize');
  const revoke=document.getElementById('delete-revoke');
  const state=deleteStatus.state||'disabled';
  const limit=deleteStatus.max_batch||100;
  if(!deleteStatus.available){
    text.textContent='Borrado no disponible: faltan dependencias Gmail o credentials.json.';
    auth.hidden=true;
    revoke.hidden=true;
  }else if(!deleteStatus.enabled){
    text.textContent='Deshabilitado. Reinicia con ENABLE_PERMANENT_DELETE=1 para permitir la autorización.';
    auth.hidden=true;
    revoke.hidden=true;
  }else if(state==='missing'||state==='revoked'){
    text.textContent=state==='revoked'
      ?'Autorización destructiva revocada. Debes volver a autorizar para recuperar el acceso.'
      :'Habilitado, pero falta un token destructivo válido guardado para reutilizar entre sesiones.';
    auth.hidden=false;
    revoke.hidden=true;
  }else if(state==='expired'){
    text.textContent=`Token destructivo caducado pero recuperable. Se refrescará si sigue siendo válido. Máximo ${limit} mensajes por lote. Esta acción no se puede deshacer.`;
    auth.hidden=true;
    revoke.hidden=false;
  }else{
    text.textContent=`Autorizado. Token destructivo guardado entre sesiones. Máximo ${limit} mensajes por lote. Esta acción no se puede deshacer.`;
    auth.hidden=true;
    revoke.hidden=false;
  }
  updateHiddenSelection();
}
async function loadHiddenReviewPage(page=1){
  hiddenReviewLoading=true;
  hiddenReviewPage=Math.max(1, page|0);
  document.getElementById('hidden-list').innerHTML='<div class="empty"><span class="spin"></span>Cargando ocultos…</div>';
  renderHiddenPager();
  try{
    const r=await fetch(`${API}/api/hidden?page=${hiddenReviewPage}`,{signal:AbortSignal.timeout(30000)});
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||d.error||`Error HTTP ${r.status}`);
    hiddenReviewItems=d.messages||[];
    hiddenReviewPage=d.page||hiddenReviewPage;
    hiddenReviewPages=d.pages||1;
    hiddenReviewTotal=d.total||0;
    hiddenReviewPageSize=d.page_size||20;
    const orphanIds=(d.messages||[]).filter(item=>item.status==='orphan').map(item=>item.id);
    if(orphanIds.length && !hiddenOrphanPurgePending){
      hiddenOrphanPurgePending=true;
      try{
        await purgeOrphanMessages(orphanIds,{silent:true});
      }finally{
        hiddenOrphanPurgePending=false;
      }
      await flushSaveState();
      await loadHiddenReviewPage(hiddenReviewPage);
      return;
    }
    renderHiddenReview();
  }catch(e){
    hiddenReviewItems=[];
    hiddenReviewPages=1;
    hiddenReviewTotal=0;
    renderHiddenPager();
    document.getElementById('hidden-list').innerHTML='<div class="empty">No se pudieron cargar los ocultos.</div>';
    toast('No se pudieron resolver los ocultos: '+e.message,'err');
  }finally{
    hiddenReviewLoading=false;
    renderHiddenPager();
  }
}
async function openHiddenReview(){
  document.getElementById('hidden-modal').classList.add('show');
  hiddenSelected.clear();
  hiddenRangeAnchorId=null;
  document.getElementById('delete-confirm').value='';
  hiddenReviewPage=1;
  renderDeleteStatus();
  await loadHiddenReviewPage(1);
}
function closeHiddenReview(){
  document.getElementById('hidden-modal').classList.remove('show');
  hiddenSelected.clear();
  hiddenRangeAnchorId=null;
}
async function restoreHiddenSelection(){
  const count=hiddenSelected.size;
  hiddenSelected.forEach(id=>deleted.delete(id));
  hiddenSelected.clear();
  hiddenRangeAnchorId=null;
  queueSaveState();
  render();
  await loadHiddenReviewPage(hiddenReviewPage);
  toast(`${count} correo${count===1?'':'s'} restaurado${count===1?'':'s'} como visible${count===1?'':'s'}`,'ok');
}
async function forgetHiddenSelection(){
  const ids=[...hiddenSelected];
  const itemsById=new Map(hiddenReviewItems.map(item=>[item.id,item]));
  const orphanIds=ids.filter(id=>itemsById.get(id)?.status==='orphan');
  if(!orphanIds.length)return;
  const count=orphanIds.length;
  if(!confirm(`Vas a eliminar ${count} registro${count===1?'':'s'} local${count===1?'':'es'} huérfano${count===1?'':'s'}. No tocará Gmail. ¿Continuar?`))return;
  await purgeOrphanMessages(orphanIds);
  await flushSaveState();
  await loadHiddenReviewPage(hiddenReviewPage);
  toast(`${count} registro${count===1?'':'s'} local${count===1?'':'es'} eliminado${count===1?'':'s'}`,'ok');
}
async function authorizePermanentDelete(){
  const button=document.getElementById('delete-authorize');
  button.disabled=true;
  try{
    const r=await fetch(`${API}/api/delete-authorize`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||d.error||`Error HTTP ${r.status}`);
    deleteStatus=d.permanent_delete||deleteStatus;
    renderDeleteStatus();
    toast('Autorización destructiva completada','ok');
  }catch(e){
    toast('No se pudo autorizar: '+e.message,'err');
  }finally{button.disabled=false;}
}
async function revokePermanentDelete(){
  const button=document.getElementById('delete-revoke');
  if(!confirm('Vas a revocar la autorización destructiva y borrar el token separado. Gmail readonly seguirá funcionando. ¿Continuar?'))return;
  button.disabled=true;
  try{
    const r=await fetch(`${API}/api/delete-revoke`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||d.error||`Error HTTP ${r.status}`);
    deleteStatus=d.permanent_delete||deleteStatus;
    document.getElementById('delete-confirm').value='';
    hiddenSelected.clear();
    hiddenRangeAnchorId=null;
    renderDeleteStatus();
    toast('Autorización destructiva revocada','ok');
  }catch(e){
    toast('No se pudo revocar: '+e.message,'err');
  }finally{button.disabled=false;}
}
async function permanentlyDeleteHidden(){
  const ids=[...hiddenSelected];
  const confirmation=document.getElementById('delete-confirm').value;
  if(!ids.length)return;
  if(!confirm(`Vas a borrar permanentemente ${ids.length} correo${ids.length===1?'':'s'} de Gmail. No se puede deshacer. ¿Continuar?`))return;
  const button=document.getElementById('hidden-delete');
  button.disabled=true;
  try{
    const r=await fetch(`${API}/api/delete-permanent`,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({ids,confirmation})
    });
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||d.error||`Error HTTP ${r.status}`);
    const successful=new Set((d.results||[]).filter(item=>item.status==='deleted').map(item=>item.id));
    successful.forEach(id=>deleted.delete(id));
    deletionAudit=d.state?.deletion_audit||deletionAudit;
    hiddenSelected.clear();
    hiddenRangeAnchorId=null;
    document.getElementById('delete-confirm').value='';
    render();
    await loadHiddenReviewPage(hiddenReviewPage);
    if(d.audit_error){
      toast(`${d.deleted||0} borrado${d.deleted===1?'':'s'} procesado${d.deleted===1?'':'s'}. ${d.audit_error}`,'err');
    }else{
      toast(`${d.deleted||0} correo${d.deleted===1?'':'s'} eliminado${d.deleted===1?'':'s'} permanentemente`,'ok');
    }
  }catch(e){
    toast('Borrado permanente rechazado: '+e.message,'err');
  }finally{button.disabled=false;updateHiddenSelection();}
}

// ── SELECTION ─────────────────────────────────────────────
function togSel(id,card){selected.has(id)?selected.delete(id):selected.add(id);card.classList.toggle('sel',selected.has(id));const cb=card.querySelector('input[type=checkbox]');if(cb)cb.checked=selected.has(id);updateSelCount();}
function updateSelCount(){document.getElementById('sel-ct').innerHTML=`<b>${selected.size}</b> sel.`;document.getElementById('sel-pill').textContent=`${selected.size} sel.`;document.getElementById('sel-pill').style.display=selected.size>0?'inline-block':'none';}

// ── EXPORT ────────────────────────────────────────────────
function exportItems(scope){
  const source=(scope==='full'?activeEmails:filtered()).filter(e=>!deleted.has(e.id));
  return source.map(itemMeta).sort((a,b)=>{
    const sev=severityRank(a)-severityRank(b);
    if(sev!==0)return sev;
    const da=(b.date||'').localeCompare(a.date||'');
    if(da!==0)return da;
    return providerKey(a).localeCompare(providerKey(b)) || a._summary.localeCompare(b._summary);
  });
}
function exportItemJson(e){
  return {
    id:e.id,
    summary:e._summary,
    source:e._provider,
    date:e._date.full,
    category:(e._categories[0]&&CATS[e._categories[0]].label)||'—',
    categories:e._categories.map(k=>CATS[k].label),
    severity:SEVERITY_META[messageSeverity(e)].label,
    severity_reason:severityReason(e),
    gmailUrl:gurl(e.id),
    attachments:Array.isArray(e.attachments)?e.attachments.length:0,
    snippet:e._snippet,
  };
}
function exportItemMd(e){
  const catsTxt=e._categories.map(k=>CATS[k].label).join(' · ')||'—';
  return [
    `## ${esc(e._summary)}`,
    '',
    `|Campo|Valor|`,
    `|---|---|`,
    `|**Fuente**|${esc(e._provider)}|`,
    `|**Fecha**|${esc(e._date.full)}|`,
    `|**Categoría**|${esc((e._categories[0]&&CATS[e._categories[0]].label)||'—')}|`,
    `|**Categorías**|${esc(catsTxt)}|`,
    `|**Severidad**|${esc(SEVERITY_META[messageSeverity(e)].label)}|`,
    `|**Motivo**|${esc(severityReason(e))}|`,
    `|**Gmail**|[Abrir en Gmail](${gurl(e.id)})|`,
    `|**Extracto**|${esc(e._snippet||'—')}|`,
  ].join('\n');
}
function buildExport(scope,fmt){
  const items=exportItems(scope);
  if(fmt==='json'){
    return JSON.stringify({
      scope,
      generated_at:new Date().toISOString(),
      count:items.length,
      items:items.map(exportItemJson),
    },null,2);
  }
  const title=scope==='full'?'Conjunto completo':'Vista filtrada';
  return [
    `# Informe operativo`,
    '',
    `- Alcance: ${title}`,
    `- Elementos: ${items.length}`,
    '',
    items.map(exportItemMd).join('\n\n'),
  ].join('\n');
}
function setExportScope(scope){
  expScope=scope;
  document.querySelectorAll('#exp-scope .mtb').forEach(t=>t.classList.toggle('on',t.dataset.scope===scope));
  document.querySelectorAll('#exp-scope .mtb').forEach(t=>t.setAttribute('aria-pressed',t.dataset.scope===scope?'true':'false'));
  document.getElementById('exp-ttl').textContent=`Exportar · ${scope==='full'?'conjunto completo':'vista filtrada'}`;
  refreshExportPreview();
}
function setExportFormat(fmt){
  expFmt=fmt;
  document.querySelectorAll('#exp-format .mtb').forEach(t=>t.classList.toggle('on',t.dataset.tab===fmt));
  document.querySelectorAll('#exp-format .mtb').forEach(t=>t.setAttribute('aria-pressed',t.dataset.tab===fmt?'true':'false'));
  refreshExportPreview();
}
function refreshExportPreview(){
  const pre=document.getElementById('exp-pre');
  const copy=document.getElementById('exp-copy');
  const dl=document.getElementById('exp-dl');
  const ready=Boolean(expScope);
  copy.disabled=!ready;
  dl.disabled=!ready;
  document.getElementById('exp-copy').classList.toggle('disabled',!ready);
  document.getElementById('exp-dl').classList.toggle('disabled',!ready);
  if(!ready){
    pre.textContent='Elige alcance para generar la vista previa.';
    return;
  }
  pre.textContent=buildExport(expScope,expFmt);
}
function openExp(){
  expData={};
  expFmt='md';
  expScope=null;
  document.getElementById('exp-modal').classList.add('show');
  document.querySelectorAll('#exp-scope .mtb').forEach(t=>t.classList.remove('on'));
  document.querySelectorAll('#exp-format .mtb').forEach(t=>t.classList.remove('on'));
  document.querySelector('#exp-format .mtb[data-tab="md"]').classList.add('on');
  document.getElementById('exp-ttl').textContent='Exportar informe';
  refreshExportPreview();
}
document.querySelectorAll('#exp-scope .mtb').forEach(t=>{t.addEventListener('click',()=>setExportScope(t.dataset.scope));});
document.querySelectorAll('#exp-format .mtb').forEach(t=>{t.addEventListener('click',()=>setExportFormat(t.dataset.tab));});
document.getElementById('exp-copy').addEventListener('click',()=>{if(!expScope){toast('Elige alcance primero','err');return;}navigator.clipboard.writeText(buildExport(expScope,expFmt)).then(()=>toast('Copiado','ok')).catch(()=>toast('Error','err'));});
document.getElementById('exp-dl').addEventListener('click',()=>{if(!expScope){toast('Elige alcance primero','err');return;}const blob=new Blob([buildExport(expScope,expFmt)],{type:'text/plain;charset=utf-8'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);const scopePart=expScope==='full'?'completo':'filtrado';a.download=`informe_operativo_${scopePart}_${new Date().toISOString().slice(0,10)}.${expFmt}`;a.click();toast(`Descargado .${expFmt}`,'ok');});
['exp-x','exp-cn'].forEach(id=>document.getElementById(id).addEventListener('click',()=>document.getElementById('exp-modal').classList.remove('show')));

// Resúmenes y tendencias: static/summary.js

// ── DELETE ────────────────────────────────────────────────
function openDel(ids){pendingDel=ids;document.getElementById('del-msg').innerHTML=`¿Ocultar <b>${ids.length}</b> correo${ids.length>1?'s':''} de la vista?<br><small>No afecta a Gmail.</small>`;document.getElementById('del-modal').classList.add('show');}
document.getElementById('del-cx').addEventListener('click',()=>{document.getElementById('del-modal').classList.remove('show');pendingDel=[];});
document.getElementById('del-ok').addEventListener('click',()=>{pendingDel.forEach(id=>{deleted.add(id);selected.delete(id);openMessages.delete(id);});document.getElementById('del-modal').classList.remove('show');toast(`${pendingDel.length} ocultado${pendingDel.length>1?'s':''}`,'ok');pendingDel=[];queueSaveState();render();});
document.getElementById('manage-hidden').addEventListener('click',openHiddenReview);
['hidden-x','hidden-cn'].forEach(id=>document.getElementById(id).addEventListener('click',closeHiddenReview));
document.getElementById('hidden-prev').addEventListener('click',()=>{if(hiddenReviewPage>1)loadHiddenReviewPage(hiddenReviewPage-1);});
document.getElementById('hidden-next').addEventListener('click',()=>{if(hiddenReviewPage<hiddenReviewPages)loadHiddenReviewPage(hiddenReviewPage+1);});
document.getElementById('hidden-all').addEventListener('click',hiddenSelectAllCurrentPage);
document.getElementById('hidden-none').addEventListener('click',hiddenClearSelection);
document.getElementById('hidden-restore').addEventListener('click',restoreHiddenSelection);
document.getElementById('hidden-forget').addEventListener('click',forgetHiddenSelection);
document.getElementById('delete-authorize').addEventListener('click',authorizePermanentDelete);
document.getElementById('delete-revoke').addEventListener('click',revokePermanentDelete);
document.getElementById('delete-confirm').addEventListener('input',updateHiddenSelection);
document.getElementById('hidden-delete').addEventListener('click',permanentlyDeleteHidden);

// ── ACTION BAR ────────────────────────────────────────────
document.getElementById('tog-sel').addEventListener('click',()=>{selMode=!selMode;const btn=document.getElementById('tog-sel');btn.textContent=selMode?'✕ Cancelar':'☐ Seleccionar';btn.style.cssText=selMode?'border-color:#f8717166;color:var(--d);background:#f8717112':'border-color:#4a9eff66;color:var(--v);';document.getElementById('actbar').style.display=selMode?'flex':'none';if(!selMode)selected.clear();render();});
document.getElementById('sel-all').addEventListener('click',()=>{filtered().forEach(e=>selected.add(e.id));render();});
document.getElementById('desel').addEventListener('click',()=>{selected.clear();render();});
document.getElementById('exp-open').addEventListener('click',()=>openExp());
document.getElementById('del-sel').addEventListener('click',()=>{if(!selected.size){toast('Selecciona correos','err');return;}openDel([...selected]);});

// ── SRC FILTER ────────────────────────────────────────────
const FC={all:'var(--v)',v:'var(--v)',p:'var(--p)',s:'var(--s)',cu:'var(--o)'};
document.querySelectorAll('.src').forEach(b=>{b.addEventListener('click',()=>{setSrcFilter(b.dataset.f);render();queueSaveState();});});
document.getElementById('srch').addEventListener('input',e=>{cq=e.target.value;render();queueSaveState();});

// ── INIT ──────────────────────────────────────────────────
async function init(){
  await loadState();
  renderSenders();
  renderRules();
  renderCats();
  render();
  const status=await checkStatus();
  if(status&&status.token)await refreshSourcesFromGmail();
}
init();
