// ── SHARED SURFACE (consumida por summary.js) ──────────────
// Vía el objeto global `App` (definido en static/shared.js):
//   App.api            ← API           (Fase 32 · Stage B)
//   App.state.deleted  ← Set de ocultos (Fase 32 · Stage B)
// Todavía leídas como global desnudo por summary.js (pendiente Stage C):
//   activeEmails, aiStatus, CATS       (se reasignan en este archivo)
// Funciones helper compartidas (nivel superior en este archivo):
//   esc, toast, gurl, itemMeta, messageSeverity, severityRank, severityReason
// Orden de carga: shared.js → app.js → summary.js
// ──────────────────────────────────────────────────────────

// ── CONFIG DEL SERVIDOR LOCAL ──────────────────────────────
const API = '';
App.api = API;
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

// ── CONFIGURACIÓN (UNIFICADA) ─────────────────────────────
let CATS={};
let SEVERITY_META={};
let SEVERITY_ORDER={};
let CATEGORY_SEVERITY={};
let CATEGORY_SEVERITY_REASON={};

async function loadBaseConfig(){
  try {
    const r=await fetch(`${API}/api/config`);
    const d=await r.json();
    if(!r.ok) throw new Error(d.error||'Error cargando config');
    const c=d.config;
    CATS=c.categories;
    SEVERITY_META=c.severity_meta;
    SEVERITY_ORDER=c.severity_order.reduce((acc,s,i)=>{acc[s]=i;return acc;},{});
    CATEGORY_SEVERITY=c.category_severity;
    CATEGORY_SEVERITY_REASON=c.category_severity_reason;

    // Poblar selector de categorías en el modal de reglas si está vacío
    const sel=document.getElementById('rule-category');
    if(sel && !sel.options.length){
      Object.entries(CATS).filter(([key])=>key!=='all').forEach(([key,value])=>{
        const option=document.createElement('option');
        option.value=key;option.textContent=value.label.replace(/^[^\p{L}\p{N}]+\s*/u,'');
        sel.appendChild(option);
      });
    }
  } catch(e) {
    toast('Error cargando configuración base: '+e.message,'err');
    // Fallback mínimo para que la app no rompa
    CATS={all:{label:'🌐 Todos',color:'var(--v)'}};
    SEVERITY_META={low:{label:'Baja',color:'var(--s)'}};
  }
}

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
App.state.deleted=deleted;
// Gmail limita batchModify a 1000 IDs; avisamos antes en lotes grandes.
const MAX_GMAIL_BATCH=1000,BIG_BATCH_WARN=200;
function guardBatchSize(ids,verb){
  if(ids.length>MAX_GMAIL_BATCH){toast(`Máximo ${MAX_GMAIL_BATCH} correos por lote. Reduce la selección.`,'err');return false;}
  if(ids.length>BIG_BATCH_WARN)return confirm(`Vas a ${verb} ${ids.length} correos en Gmail. La operación se trocea internamente y puede tardar unos segundos. ¿Continuar?`);
  return true;
}
let pendingDel=[],expData=null,expFmt='md',expScope=null;
let stateReady=false,saveTimer=null,saveInFlight=false,savePending=false,editingRuleId=null;
let ruleSearch='';
let emailModalEmail=null;
const groupSearches={};
let aiSuggestionsEnabled=false, currentAiSuggestions=[];
let hiddenReviewItems=[],deletionAudit=[];
const hiddenSelected=new Set();
let hiddenReviewPage=1,hiddenReviewPages=1,hiddenReviewTotal=0,hiddenReviewPageSize=20,hiddenReviewLoading=false,hiddenRangeAnchorId=null;
let hiddenOrphanPurgePending=false;
let hiddenSearchQuery='';

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
    preferences:{
      source_filter:cf,
      category_filter:activeCat,
      search_query:cq,
      ai_suggestions_enabled:aiSuggestionsEnabled
    }
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
  const savedCat=p.category_filter||'all';
  activeCat=(savedCat==='all'||CATS[savedCat]||savedCat.startsWith('__rule__'))?savedCat:'all';
  aiSuggestionsEnabled=Boolean(p.ai_suggestions_enabled);
  document.getElementById('ai-sugg-toggle').checked=aiSuggestionsEnabled;
  updateAiSuggUI();
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
    if(emailModalEmail&&sources.some(s=>s.id===emailModalEmail.id))renderEmailModal();
  }
}

// ── BÚSQUEDA REAL EN GMAIL ────────────────────────────────
async function searchGmail(params={},opts={}){
  const busy=opts.busy!==false,showErr=opts.errors!==false;
  const btn=document.getElementById('snd-add');
  if(busy){
    btn.disabled=true;
    btn.innerHTML='<span class="spin"></span>Buscando…';
  }
  try{
    const qs=new URLSearchParams();
    if(params.sender) qs.set('sender', params.sender);
    if(params.q) qs.set('q', params.q);
    if(params.after) qs.set('after', params.after);
    if(params.before) qs.set('before', params.before);
    qs.set('max', '30');

    const r=await fetch(`${API}/api/search?${qs.toString()}`);
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
  const val=raw?raw.trim().toLowerCase().replace(/^@/,''):'';
  const literal=document.getElementById('snd-q').value.trim();
  const after=document.getElementById('snd-after').value;
  const before=document.getElementById('snd-before').value;

  if(!val && !literal && !after && !before){
    toast('Indica remitente, texto o fechas','err');
    return;
  }
  
  let dom='', label='', query='';
  if(val){
    dom=val.includes('@')?val.split('@')[1]:val;
    query=val.includes('@')?val:dom;
    const validDom=/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$/;
    const validEmail=/^[a-z0-9._%+-]+@[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$/;
    if(!validDom.test(val)&&!validEmail.test(val)){
      toast('Usa un dominio o email válido','err');
      return;
    }
    const known=KNOWN.find(k=>dom.includes(k.dom)||k.dom.includes(dom));
    label=known?known.label:dom;
  }

  // Buscar en Gmail en tiempo real
  toast(`Localizando correos en Gmail…`,'ok');
  const emails=await searchGmail({sender:val, q:literal, after, before});
  if(emails===null)return;
  if(emails.length===0){
    toast(`No se encontraron correos con esos filtros`,'err');
    return;
  }

  // Normalizar campo subject → sub
  const normalized=emails.map(e=>({...e,sub:e.subject||e.sub||'(sin asunto)'}));

  // Añadir solo los nuevos
  const existing=new Set(activeEmails.map(e=>e.id));
  const nuevos=normalized.filter(e=>!existing.has(e.id));
  activeEmails=[...activeEmails,...nuevos];

  if(val && ![...FIXED,...customSrcs].some(s=>s.dom===dom)){
    const known=KNOWN.find(k=>dom.includes(k.dom)||k.dom.includes(dom));
    const color=known?known.color:PAL[customSrcs.length%PAL.length];
    customSrcs.push({dom,label,color,fixed:false});
    document.getElementById('cu-btn').style.display='';
    focusSender(dom);
    renderSenders();
  } else if (!val) {
    setSrcFilter('all');
  }

  document.getElementById('snd-inp').value='';
  // Colapsar panel de búsqueda y mostrar resultados
  document.getElementById('p-snd').classList.add('col');
  document.getElementById('p-cat').classList.remove('col');
  renderCats();
  render();
  queueSaveState();
  toast(`✓ Encontrados: ${emails.length} correos; ${nuevos.length} incorporados`,'ok');
}

// ── RENDER SENDERS ────────────────────────────────────────
function renderSenders(){
  const grid=document.getElementById('snd-chips');grid.innerHTML='';
  [...FIXED,...customSrcs].forEach(s=>{
    const cnt=activeEmails.filter(e=>!deleted.has(e.id)&&e.from&&e.from.includes(s.dom)).length;
    if(cnt===0)return;
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
['snd-inp','snd-q','snd-after','snd-before'].forEach(id=>{
  document.getElementById(id).addEventListener('keydown',e=>{if(e.key==='Enter')addSrc(document.getElementById('snd-inp').value);});
});

// ── REGLAS PERSONALIZADAS ────────────────────────────────
function renderRules(){
  const list=document.getElementById('rule-list');
  list.innerHTML='';
  document.getElementById('rules-tag').textContent=customRules.length;
  const q=ruleSearch.toLowerCase().trim();
  const toShow=q?customRules.filter(r=>
    r.label.toLowerCase().includes(q)||
    r.provider.toLowerCase().includes(q)||
    r.keywords.some(kw=>kw.includes(q))
  ):customRules;
  if(!toShow.length){
    list.innerHTML=q?'<div class="empty">Sin reglas que coincidan con la búsqueda.</div>':'<div class="empty">Sin reglas personalizadas. Se aplican las reglas base.</div>';
    return;
  }
  toShow.forEach(rule=>{
    const item=document.createElement('div');
    item.className='rule-item';
    const conditions=[rule.provider?`Proveedor: ${rule.provider}`:'',rule.keywords.length?`Texto (${rule.keyword_operator==='all'?'todas':'alguna'}): ${rule.keywords.join(', ')}`:''].filter(Boolean).join(' · ');
    const labelInfo=rule.gmail_label_id ? ` · 🏷 ${gmailLabels.find(l=>l.id===rule.gmail_label_id)?.name||rule.gmail_label_id}` : '';
    const autoInfo=(rule.auto_label||rule.auto_archive) ? ` · ⚡${rule.auto_archive?'📦':''}` : '';
    item.innerHTML=`<div class="rule-main"><div class="rule-name">${esc(rule.label)} · ${esc(CATS[rule.category]?.label||rule.category)} · ${esc(SEVERITY_META[rule.severity]?.label||rule.severity)}${esc(labelInfo)}${esc(autoInfo)}</div><div class="rule-desc">${esc(conditions)}</div></div><div class="rule-actions"><button class="rule-edit" type="button">Editar</button><button class="rule-del" type="button">Eliminar</button></div>`;
    item.querySelector('.rule-edit').addEventListener('click',()=>{
      editingRuleId=rule.id;
      document.getElementById('rule-label').value=rule.label;
      document.getElementById('rule-provider').value=rule.provider;
      document.getElementById('rule-keywords').value=rule.keywords.join(', ');
      document.getElementById('rule-keyword-operator').value=rule.keyword_operator||'any';
      document.getElementById('rule-category').value=rule.category;
      document.getElementById('rule-severity').value=rule.severity;
      document.getElementById('rule-gmail-label').value=rule.gmail_label_id||'';
      document.getElementById('rule-auto-label').checked=rule.auto_label||false;
      document.getElementById('rule-auto-archive').checked=rule.auto_archive||false;
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

function updateAiSuggUI(){
  const box=document.getElementById('ai-sugg-box');
  const btn=document.getElementById('ai-sugg-btn');
  btn.style.display=aiSuggestionsEnabled?'block':'none';
  if(!aiSuggestionsEnabled){
    box.style.display='none';
    currentAiSuggestions=[];
  }
}

async function suggestAiRules(){
  let hiddenEmails=activeEmails.filter(e=>deleted.has(e.id)).map(e=>({from:e.from,sub:e.sub}));

  // Si no hay ocultos en sesión pero sí en el estado persistido, los cargamos de la API
  if(!hiddenEmails.length&&deleted.size>0){
    toast('Cargando correos ocultos para la IA…','ok');
    try{
      // Paginamos hasta 3 páginas para obtener hasta ~60 emails para el análisis
      for(let pg=1;pg<=3&&hiddenEmails.length<60;pg++){
        const r=await fetch(`${API}/api/hidden?page=${pg}`,{signal:AbortSignal.timeout(15000)});
        const d=await r.json();
        if(!r.ok)break;
        const batch=(d.messages||[])
          .filter(m=>m.status==='available'&&m.email)
          .map(m=>({from:m.email.from||'',sub:m.email.subject||m.email.sub||''}));
        hiddenEmails=[...hiddenEmails,...batch];
        if((d.page||1)>=(d.pages||1))break;
      }
    }catch(err){
      // si falla la carga, seguimos con lo que tengamos
    }
  }

  if(!hiddenEmails.length){toast('Oculta algunos correos primero para que la IA aprenda','err');return;}

  const btn=document.getElementById('ai-sugg-btn');
  const box=document.getElementById('ai-sugg-box');
  const list=document.getElementById('ai-sugg-list');

  btn.disabled=true;btn.textContent=`Analizando ${hiddenEmails.length} patrones…`;
  try {
    const r=await fetch(`${API}/api/ai-suggest-rules`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(hiddenEmails)
    });
    const d=await r.json();
    if(!r.ok) throw new Error(d.detail||d.error||'Error en la IA');
    
    currentAiSuggestions=d.suggestions||[];
    if(!currentAiSuggestions.length){
      toast('La IA no ha encontrado patrones claros todavía','err');
      box.style.display='none';
    } else {
      box.style.display='block';
      list.innerHTML='';
      currentAiSuggestions.forEach((s,idx)=>{
        const d=document.createElement('div');
        d.className='cchip on'; d.style.background='var(--card)'; d.style.borderColor='var(--v)'; d.style.color='var(--txt)';
        d.innerHTML=`<span style="font-size:11px;"><b>${esc(s.label)}</b> (@${esc(s.provider)})</span><button class="mab cp" style="padding:2px 6px; font-size:10px; margin-left:8px;">Aplicar</button>`;
        d.querySelector('button').onclick=()=>applyAiSuggestion(idx);
        list.appendChild(d);
      });
      toast(`La IA sugiere ${currentAiSuggestions.length} reglas`,'ok');
    }
  } catch(e) {
    toast('Sugerencias IA: '+e.message,'err');
  } finally {
    btn.disabled=false;btn.textContent='Sugerir reglas ahora';
  }
}

function applyAiSuggestion(idx){
  const s=currentAiSuggestions[idx];
  if(!s)return;
  document.getElementById('rule-label').value=s.label;
  document.getElementById('rule-provider').value=s.provider;
  document.getElementById('rule-keywords').value=(s.keywords||[]).join(', ');
  document.getElementById('rule-category').value=s.category;
  document.getElementById('rule-severity').value=s.severity;
  document.getElementById('rule-auto-label').checked=s.auto_label||false;
  document.getElementById('rule-auto-archive').checked=s.auto_archive||false;
  document.getElementById('rule-label').focus();
  // Scroll al formulario
  document.querySelector('.rule-form').scrollIntoView({behavior:'smooth'});
  toast('Sugerencia cargada en el formulario','ok');
}

document.getElementById('ai-sugg-toggle').addEventListener('change',e=>{
  aiSuggestionsEnabled=e.target.checked;
  updateAiSuggUI();
  queueSaveState();
});
document.getElementById('ai-sugg-btn').addEventListener('click',suggestAiRules);
document.getElementById('ai-sugg-reset').addEventListener('click',()=>{
  currentAiSuggestions=[];
  document.getElementById('ai-sugg-box').style.display='none';
  document.getElementById('ai-sugg-list').innerHTML='';
  toast('Sugerencias eliminadas','ok');
});
function resetRuleForm(){
  editingRuleId=null;
  ['rule-label','rule-provider','rule-keywords'].forEach(id=>document.getElementById(id).value='');
  document.getElementById('rule-keyword-operator').value='any';
  document.getElementById('rule-gmail-label').value='';
  document.getElementById('rule-auto-label').checked=false;
  document.getElementById('rule-auto-archive').checked=false;
  document.getElementById('rule-add').textContent='+ Añadir regla';
}
function addRule(){
  const label=document.getElementById('rule-label').value.trim()||'Regla personalizada';
  const provider=document.getElementById('rule-provider').value.trim().toLowerCase().replace(/^@/,'');
  const keywords=document.getElementById('rule-keywords').value.split(',').map(x=>x.trim().toLowerCase()).filter(Boolean).slice(0,20);
  const keyword_operator=document.getElementById('rule-keyword-operator').value==='all'?'all':'any';
  const category=document.getElementById('rule-category').value;
  const severity=document.getElementById('rule-severity').value;
  const gmail_label_id=document.getElementById('rule-gmail-label').value;
  const auto_label=document.getElementById('rule-auto-label').checked;
  const auto_archive=document.getElementById('rule-auto-archive').checked;
  const validDomain=/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$/;
  if(!provider&&!keywords.length){toast('Indica proveedor, palabras clave o ambos','err');return;}
  if(provider&&!validDomain.test(provider)){toast('Usa un dominio de proveedor válido','err');return;}
  const rule={
    id:editingRuleId||`rule_${Date.now().toString(36)}`,
    label,provider,keywords,keyword_operator,category,severity,
    gmail_label_id,auto_label,auto_archive
  };
  if(editingRuleId)customRules=customRules.map(r=>r.id===editingRuleId?rule:r);
  else customRules.push(rule);
  const action=editingRuleId?'actualizada':'añadida';
  resetRuleForm();
  renderRules();renderCats();render();queueSaveState();
  toast(`Regla "${label}" ${action}`,'ok');
  }

  document.getElementById('rule-add').addEventListener('click',addRule);

document.getElementById('rule-keywords').addEventListener('keydown',e=>{if(e.key==='Enter')addRule();});
document.getElementById('rule-search').addEventListener('input',e=>{ruleSearch=e.target.value;renderRules();});

// ── CAT CHIPS ─────────────────────────────────────────────
function renderCats(){
  const grid=document.getElementById('cat-grid');grid.innerHTML='';
  const base=filteredBySrc();

  Object.entries(CATS).forEach(([k,v])=>{
    const cnt=k==='all'?base.length:base.filter(e=>cats(e).includes(k)).length;
    if(k!=='all'&&cnt===0)return;
    const chip=document.createElement('div');
    chip.className='cchip'+(activeCat===k?' on':'');
    chip.dataset.cat=k;
    chip.style.cssText=`border-color:${v.color}66;color:${v.color};${activeCat===k?`background:${v.color}30`:``}`;
    chip.innerHTML=`${v.label} <span class="cn">${cnt}</span>`;
    chip.addEventListener('click',()=>{activeCat=k;renderCats();render();queueSaveState();});
    grid.appendChild(chip);
  });

  const activeRules=customRules.filter(rule=>
    base.filter(e=>matchingRules(e).some(r=>r.id===rule.id)).length>0
  );
  if(activeRules.length){
    const sep=document.createElement('div');
    sep.style.cssText='width:100%;flex-basis:100%;border-top:1px solid var(--bdr);margin:4px 0;';
    grid.appendChild(sep);
    activeRules.forEach(rule=>{
      const cnt=base.filter(e=>matchingRules(e).some(r=>r.id===rule.id)).length;
      const rk='__rule__'+rule.id;
      const col=CATS[rule.category]?.color||'var(--v)';
      const chip=document.createElement('div');
      chip.className='cchip'+(activeCat===rk?' on':'');
      chip.dataset.cat=rk;
      chip.style.cssText=`border-color:${col}66;color:${col};${activeCat===rk?`background:${col}30`:''}`;
      chip.innerHTML=`⚙ ${esc(rule.label)} <span class="cn">${cnt}</span>`;
      chip.addEventListener('click',()=>{activeCat=rk;renderCats();render();queueSaveState();});
      grid.appendChild(chip);
    });
  }

  renderCatEmailList();
}

function renderCatEmailList(){
  const container=document.getElementById('cat-email-list');
  if(!container)return;
  container.innerHTML='';
  const items=queueItems();
  if(!items.length){
    container.innerHTML='<div class="cat-empty">Sin correos en la vista actual.</div>';
    return;
  }
  items.slice(0,60).forEach(e=>{
    const dt=e._date;
    const col=srcColor(e);
    const row=document.createElement('div');
    row.className='cat-email-row';
    row.innerHTML=`
      <span class="cer-dot" style="background:${col}"></span>
      <span class="cer-from">${esc(providerName(e))}</span>
      <span class="cer-sub">${esc(e._summary)}</span>
      <span class="cer-date">${esc(dt.day+' '+dt.mo)}</span>
    `;
    row.addEventListener('click',()=>{
      const orig=activeEmails.find(ae=>ae.id===e.id)||e;
      openEmailModal(orig);
    });
    container.appendChild(row);
  });
  if(items.length>60){
    const more=document.createElement('div');
    more.className='cat-more';
    more.textContent=`+${items.length-60} más · filtra con los chips de arriba`;
    container.appendChild(more);
  }
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
function filtered(){
  const b=filteredBySrc();
  if(activeCat==='all')return b;
  if(activeCat.startsWith('__rule__')){
    const ruleId=activeCat.slice(8);
    return b.filter(e=>matchingRules(e).some(r=>r.id===ruleId));
  }
  return b.filter(e=>cats(e).includes(activeCat));
}

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

      const grpSearch=document.createElement('input');
      grpSearch.className='ainp grp-search-inp';
      grpSearch.placeholder=`Buscar en ${provider}…`;
      grpSearch.value=groupSearches[provider]||'';
      sec.appendChild(grpSearch);

      const cardsWrap=document.createElement('div');
      cardsWrap.className='grp-cards';

      const gsq=(groupSearches[provider]||'').toLowerCase().trim();
      items.forEach(e=>{
        const sub=e._summary;
        const dt=e._date;
        const atts=Array.isArray(e.attachments)?e.attachments:[];
        const attChecked=e.attachments_checked===true;
        const cr=e._categories.length>0?'cr-'+e._categories[0]:'';
        const sev=messageSeverity(e);
        const c=document.createElement('div');
        const searchStr=[sub,e.body,e.from,e.to,e.cc||'',e.tag].join(' ').toLowerCase();
        c.className=`card ${e.src==='cu'?'cu':e.src} ${cr} sev-${sev}${selected.has(e.id)?' sel':''}${selMode?' sm':''}`;
        c.dataset.id=e.id;
        c.dataset.search=searchStr;
        if(gsq&&!searchStr.includes(gsq))c.style.display='none';
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
    <button class="ca dl card-hide" type="button" title="Ocultar">🙈</button>
  </div>
</div>`;
        c.querySelector('.ch').addEventListener('click',()=>{
          if(selMode){togSel(e.id,c);return;}
          const orig=activeEmails.find(ae=>ae.id===e.id)||e;
          openEmailModal(orig);
        });
        c.querySelector('input[type=checkbox]').addEventListener('change',()=>togSel(e.id,c));
        c.querySelector('.card-hide').addEventListener('click',ev=>{ev.stopPropagation();openDel([e.id]);});
        c.querySelectorAll('.att-open').forEach(a=>a.addEventListener('click',onAttachmentClick));
        cardsWrap.appendChild(c);
      });

      grpSearch.addEventListener('input',ev=>{
        const q=ev.target.value.toLowerCase().trim();
        groupSearches[provider]=q;
        cardsWrap.querySelectorAll('.card').forEach(card=>{
          card.style.display=(!q||card.dataset.search.includes(q))?'':'none';
        });
      });

      sec.appendChild(cardsWrap);
      list.appendChild(sec);
    });
  }
  const tot=activeEmails.filter(e=>!deleted.has(e.id)).length;
  const sevCounts=fil.reduce((acc,e)=>{acc[messageSeverity(e)]++;return acc;},{high:0,medium:0,low:0});
  document.getElementById('stbar').innerHTML=
    `<span>${fil.length} de ${tot}</span>`+
    `<span class="sseg" style="color:var(--d)">▲ ${sevCounts.high}</span>`+
    `<span class="sseg" style="color:var(--o)">◆ ${sevCounts.medium}</span>`+
    `<span class="sseg" style="color:var(--s)">● ${sevCounts.low}</span>`;
  document.getElementById('total-pill').textContent=`${tot} correos`;
  updateSelCount();renderCats();updateHiddenBar();
}

// ── EMAIL MODAL ───────────────────────────────────────────
function openEmailModal(emailOrig){
  emailModalEmail=emailOrig;
  renderEmailModal();
  document.getElementById('email-modal').classList.add('show');
  if(!emailOrig.attachments_checked)hydrateMessageAttachments(emailOrig);
}

function renderEmailModal(){
  if(!emailModalEmail)return;
  const e=emailModalEmail;
  const eM=itemMeta(e);
  const dt=eM._date;
  const eCategories=eM._categories;
  const atts=Array.isArray(e.attachments)?e.attachments:[];
  const attChecked=e.attachments_checked===true;
  const sev=messageSeverity(e);

  document.getElementById('email-modal-sub').textContent=normSub(e);
  document.getElementById('email-modal-badges').innerHTML=
    severityBadge(eM)+categoryBadges(eM)+providerBadge(eM);

  const ef=document.getElementById('email-modal-ef');
  ef.innerHTML=`
    <div class="efr"><span class="efk">De</span><span class="efv">${esc(e.from||'')}</span></div>
    <div class="efr"><span class="efk">Para</span><span class="efv">${esc(e.to||'')}</span></div>
    ${e.cc?`<div class="efr"><span class="efk">CC</span><span class="efv">${esc(e.cc)}</span></div>`:''}
    <div class="efr"><span class="efk">Asunto</span><span class="efv">${esc(normSub(e))}</span></div>
    <div class="efr"><span class="efk">Fecha</span><span class="efv">${esc(dt.full)}</span></div>
    ${eCategories.length?`<div class="efr"><span class="efk">Cats</span><span class="efv">${eCategories.map(k=>CATS[k].label).join(' · ')}</span></div>`:''}
    ${attachmentDetail(e,atts,attChecked)}
  `;
  ef.querySelectorAll('.att-open').forEach(a=>a.addEventListener('click',onAttachmentClick));

  document.getElementById('email-modal-body').innerHTML=lnk(e.body||e.snippet||'');

  const actions=document.getElementById('email-modal-actions');
  actions.innerHTML=`
    <a class="ca gm" href="${gurl(e.id)}" target="_blank" rel="noopener">✉ Gmail</a>
    <button class="ca dl" id="email-modal-hide">🙈 Ocultar</button>
  `;
  document.getElementById('email-modal-hide').addEventListener('click',()=>{
    closeEmailModal();
    openDel([e.id]);
  });
}

function closeEmailModal(){
  document.getElementById('email-modal').classList.remove('show');
  emailModalEmail=null;
}

document.getElementById('email-modal-x').addEventListener('click',closeEmailModal);

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
    const qParam=hiddenSearchQuery?`&q=${encodeURIComponent(hiddenSearchQuery)}`:'';
    const r=await fetch(`${API}/api/hidden?page=${hiddenReviewPage}${qParam}`,{signal:AbortSignal.timeout(30000)});
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
  hiddenSearchQuery='';
  document.getElementById('hidden-search').value='';
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

async function exportEml(){
  const ids=[...selected];
  if(!ids.length){toast('Selecciona correos primero','err');return;}
  const btn=document.getElementById('exp-eml');
  const oldText=btn.textContent;
  btn.disabled=true;
  btn.innerHTML='<span class="spin"></span>Exportando…';
  try{
    const r=await fetch(`${API}/api/messages/export`,{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message_ids:ids})
    });
    const d=await r.json();
    if(!r.ok){
      const errBody=await r.json().catch(()=>({error:'Error HTTP '+r.status}));
      throw new Error(errBody.detail||errBody.error||`Error HTTP ${r.status}`);
    }
    
    toast(`📦 Guardado en /exports: ${d.file}`,'ok');
    loadLocalExports();
  }catch(e){
    toast('Error exportando: '+e.message,'err');
  }finally{
    btn.disabled=false;
    btn.textContent=oldText;
  }
}
document.getElementById('exp-eml').addEventListener('click',exportEml);

async function archiveSelection(){
  const ids=[...selected];
  if(!ids.length){toast('Selecciona correos primero','err');return;}
  if(!guardBatchSize(ids,'archivar'))return;
  const btn=document.getElementById('archive-sel');
  const oldText=btn.textContent;
  btn.disabled=true;
  btn.innerHTML=`<span class="spin"></span>Archivando ${ids.length>BIG_BATCH_WARN?ids.length+' correos… ':''}`;
  try{
    const r=await fetch(`${API}/api/messages/archive`,{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message_ids:ids})
    });
    const d=await r.json();
    if(!r.ok){
      if(r.status===403) throw new Error('Permisos insuficientes. Borra token.json y vuelve a autorizar.');
      throw new Error(d.detail||d.error||`Error HTTP ${r.status}`);
    }
    // Ocultar localmente
    ids.forEach(id=>{
      deleted.add(id);
      selected.delete(id);
      openMessages.delete(id);
    });
    render();
    toast(`📦 ${ids.length} correo${ids.length>1?'s':''} archivado${ids.length>1?'s':''} y ocultado${ids.length>1?'s':''}`,'ok');
  }catch(e){
    toast('Error archivando: '+e.message,'err');
  }finally{
    btn.disabled=false;
    btn.textContent=oldText;
  }
}
document.getElementById('archive-sel').addEventListener('click',archiveSelection);

let gmailLabels=[],selectedLabelId=null,labelFilter='';
// Poblar el <select> de etiquetas en el formulario de reglas
function populateRuleGmailLabelSelect(){
  const sel=document.getElementById('rule-gmail-label');
  if(!sel)return;
  const current=sel.value;
  sel.innerHTML='<option value="">(Ninguna)</option>';
  gmailLabels.forEach(l=>{
    const opt=document.createElement('option');
    opt.value=l.id;opt.textContent=l.name;
    sel.appendChild(opt);
  });
  // Restaurar selección previa si sigue siendo válida
  sel.value=current;
}
// Carga las etiquetas de Gmail y rellena el selector de reglas (sin tocar el modal)
async function fetchGmailLabels(){
  try{
    const r=await fetch(`${API}/api/labels`);
    const d=await r.json();
    if(!r.ok)throw new Error(d.error||'Error cargando etiquetas');
    gmailLabels=d.labels||[];
    populateRuleGmailLabelSelect();
  }catch(e){
    // Fallo silencioso al arrancar: el selector queda con (Ninguna)
    console.warn('[Labels] No se pudieron cargar las etiquetas:', e.message);
  }
}
async function loadLabels(){
  const list=document.getElementById('lbl-list');
  list.innerHTML='<div class="empty"><span class="spin"></span>Cargando etiquetas…</div>';
  try{
    // Reusar cache si ya tenemos etiquetas; si no, recargar
    if(!gmailLabels.length){
      const r=await fetch(`${API}/api/labels`);
      const d=await r.json();
      if(!r.ok)throw new Error(d.error||'Error cargando etiquetas');
      gmailLabels=d.labels||[];
      populateRuleGmailLabelSelect();
    }
    renderLabels();
  }catch(e){
    list.innerHTML=`<div class="empty err">${e.message}</div>`;
  }
}
function renderLabels(){
  const list=document.getElementById('lbl-list');list.innerHTML='';
  const filtered=gmailLabels.filter(l=>l.name.toLowerCase().includes(labelFilter.toLowerCase()));
  
  // Opción dinámica para crear nueva etiqueta
  if(labelFilter.trim()){
    const exactMatch=gmailLabels.find(l=>l.name.toLowerCase()===labelFilter.toLowerCase().trim());
    if(!exactMatch){
      const d=document.createElement('div');
      d.className='hidden-item sel';
      d.style.cssText='cursor:pointer; border-color:var(--v); background:rgba(74,158,255,0.05); margin-bottom:8px;';
      d.innerHTML=`<div class="hidden-main"><div class="hidden-subject" style="color:var(--v)">✨ Crear etiqueta "${labelFilter.trim()}"</div></div>`;
      d.onclick=()=>createLabelFlow(labelFilter.trim());
      list.appendChild(d);
    }
  }

  if(!filtered.length && !labelFilter.trim()){list.innerHTML='<div class="empty">No hay etiquetas disponibles</div>';return;}
  if(!filtered.length && labelFilter.trim()){/* Ya se muestra la opción de crear */}

  filtered.forEach(l=>{
    const d=document.createElement('div');
    d.className='hidden-item'+(selectedLabelId===l.id?' sel':'');
    d.style.cursor='pointer';
    d.innerHTML=`<div class="hidden-main"><div class="hidden-subject">🏷 ${l.name}</div></div>`;
    d.onclick=()=>{selectedLabelId=l.id;renderLabels();document.getElementById('lbl-ok').disabled=false;};
    list.appendChild(d);
  });
}
async function openLabelModal(){
  if(!selected.size){toast('Selecciona correos primero','err');return;}
  document.getElementById('lbl-modal').classList.add('show');
  selectedLabelId=null;labelFilter='';
  document.getElementById('lbl-search').value='';
  document.getElementById('lbl-ok').disabled=true;
  await loadLabels();
}
async function applySelectedLabel(){
  const ids=[...selected];
  if(!guardBatchSize(ids,'etiquetar'))return;
  const archive=document.getElementById('lbl-archive-too').checked;
  const btn=document.getElementById('lbl-ok');
  btn.disabled=true;btn.innerHTML=`<span class="spin"></span>Aplicando ${ids.length>BIG_BATCH_WARN?'a '+ids.length+' correos… ':''}`;
  try{
    const r=await fetch(`${API}/api/messages/label`,{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message_ids:ids,label_id:selectedLabelId,archive})
    });
    const d=await r.json();
    if(!r.ok)throw new Error(d.detail||d.error||`Error HTTP ${r.status}`);
    if(archive) ids.forEach(id=>{deleted.add(id);selected.delete(id);openMessages.delete(id);});
    document.getElementById('lbl-modal').classList.remove('show');
    render();
    const lbl=gmailLabels.find(l=>l.id===selectedLabelId)?.name||'Etiqueta';
    toast(`✓ ${ids.length} correo${ids.length>1?'s':''} con etiqueta "${lbl}"${archive?' y archivado(s)':''}`,'ok');
  }catch(e){
    toast('Error etiquetando: '+e.message,'err');
    btn.disabled=false;btn.textContent='Aplicar etiqueta';
  }
}

async function createLabelFlow(name){
  const okBtn=document.getElementById('lbl-ok');
  okBtn.disabled=true;
  toast(`Creando etiqueta "${name}"…`,'ok');
  try {
    const r=await fetch(`${API}/api/labels`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({name})
    });
    const d=await r.json();
    if(!r.ok) throw new Error(d.detail||d.error||'Error creando etiqueta');
    
    const newLabel=d.label;
    gmailLabels.push(newLabel);
    selectedLabelId=newLabel.id;
    labelFilter=''; // Limpiar filtro para ver la nueva lista
    document.getElementById('lbl-search').value='';
    renderLabels();
    populateRuleGmailLabelSelect(); // Sincronizar selector de reglas
    okBtn.disabled=false;
    toast(`✓ Etiqueta "${name}" creada`,'ok');
  } catch(e) {
    toast('No se pudo crear: '+e.message,'err');
    okBtn.disabled=true;
  }
}

document.getElementById('lbl-sel').addEventListener('click',openLabelModal);
['lbl-x','lbl-cn'].forEach(id=>document.getElementById(id).addEventListener('click',()=>document.getElementById('lbl-modal').classList.remove('show')));
document.getElementById('lbl-search').addEventListener('input',e=>{labelFilter=e.target.value;renderLabels();});
document.getElementById('lbl-ok').addEventListener('click',applySelectedLabel);

// ── CREAR ETIQUETA INLINE DESDE FORMULARIO DE REGLAS ──────
(function(){
  const btn   = document.getElementById('rule-new-label-btn');
  const row   = document.getElementById('rule-new-label-row');
  const inp   = document.getElementById('rule-new-label-inp');
  const okBtn = document.getElementById('rule-new-label-ok');
  const cnBtn = document.getElementById('rule-new-label-cancel');

  function openInline(){
    row.style.display='flex';
    inp.value='';
    inp.focus();
    btn.style.display='none';
  }
  function closeInline(){
    row.style.display='none';
    btn.style.display='';
    inp.value='';
  }
  async function createInline(){
    const name=inp.value.trim();
    if(!name){inp.focus();return;}
    okBtn.disabled=true;
    okBtn.textContent='…';
    try{
      const r=await fetch(`${API}/api/labels`,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({name})
      });
      const d=await r.json();
      if(!r.ok)throw new Error(d.detail||d.error||'Error creando etiqueta');
      const newLabel=d.label;
      gmailLabels.push(newLabel);
      populateRuleGmailLabelSelect();
      document.getElementById('rule-gmail-label').value=newLabel.id;
      closeInline();
      toast(`✓ Etiqueta "${name}" creada y seleccionada`,'ok');
    }catch(e){
      toast('No se pudo crear: '+e.message,'err');
    }finally{
      okBtn.disabled=false;
      okBtn.textContent='✓';
    }
  }

  btn.addEventListener('click',openInline);
  cnBtn.addEventListener('click',closeInline);
  okBtn.addEventListener('click',createInline);
  inp.addEventListener('keydown',e=>{
    if(e.key==='Enter'){e.preventDefault();createInline();}
    if(e.key==='Escape'){closeInline();}
  });
})();


// ── EXPORTACIONES LOCALES Y LECTOR ──────────────────────
let localExports=[];
async function loadLocalExports(){
  try{
    const r=await fetch(`${API}/api/exports`);
    const d=await r.json();
    localExports=d.files||[];
    renderLocalExports();
  }catch(e){console.error('Error cargando exportaciones:', e);}
}
function renderLocalExports(){
  const list=document.getElementById('exp-local-list');
  const tag=document.getElementById('exp-tag');
  tag.textContent=localExports.length;
  if(!localExports.length){
    list.innerHTML='<div class="empty">No hay archivos exportados todavía.</div>';
    return;
  }
  list.innerHTML='';
  localExports.forEach(f=>{
    const d=document.createElement('div');
    d.className='hidden-item'; d.style.cursor='pointer';
    const date=new Date(f.mtime*1000).toLocaleString();
    d.innerHTML=`<div class="hidden-main">
      <div class="hidden-subject">${f.type==='zip'?'📦':'✉'} ${f.name}</div>
      <div class="hidden-meta">${(f.size/1024).toFixed(1)} KB · ${date}</div>
    </div>`;
    d.onclick=()=>{
      if(f.type==='eml') openEmlReader(f.name);
      else toast('Los archivos .zip deben abrirse desde la carpeta /exports','err');
    };
    list.appendChild(d);
  });
}

// Convierte los adjuntos EML (con data base64) en chips descargables
function buildEmlAttachmentChips(attachments, container){
  container.innerHTML='';
  attachments.forEach(a=>{
    const chip=document.createElement('a');
    chip.className='cchip on';
    chip.style.cssText='background:var(--card);cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:4px;';
    chip.title=`Descargar ${a.filename}`;
    chip.innerHTML=`<span style="font-size:11px;">📎 ${esc(a.filename)} (${(a.size/1024).toFixed(0)} KB)</span>`;
    if(a.data){
      // Crear blob desde base64 y forzar descarga
      chip.addEventListener('click', ev=>{
        ev.preventDefault();
        const bytes=Uint8Array.from(atob(a.data), c=>c.charCodeAt(0));
        const blob=new Blob([bytes],{type:a.mime_type||'application/octet-stream'});
        const url=URL.createObjectURL(blob);
        const dl=document.createElement('a');
        dl.href=url; dl.download=a.filename;
        dl.click();
        setTimeout(()=>URL.revokeObjectURL(url),2000);
      });
    }
    container.appendChild(chip);
  });
}
async function openEmlReader(filename, externalPath=''){
  const modal=document.getElementById('reader-modal');
  const frame=document.getElementById('reader-frame');
  const txt=document.getElementById('reader-text');
  const atts=document.getElementById('reader-attachments');
  
  modal.classList.add('show');
  document.getElementById('reader-subject').textContent='Cargando…';
  atts.innerHTML=''; frame.style.display='none'; txt.style.display='none';
  
  try{
    const qs=new URLSearchParams();
    if(externalPath) qs.set('path', externalPath);
    else qs.set('file', filename);
    
    const r=await fetch(`${API}/api/read-eml?${qs.toString()}`);
    const d=await r.json();
    if(!r.ok) throw new Error(d.error||'Error leyendo correo');
    
    const m=d.data;
    document.getElementById('reader-subject').textContent=m.subject;
    document.getElementById('reader-from').textContent=m.from;
    document.getElementById('reader-to').textContent=m.to;
    document.getElementById('reader-date').textContent=m.date;
    
    if(m.attachments.length) buildEmlAttachmentChips(m.attachments, atts);
    
    if(m.body_html){
      frame.style.display='block';
      frame.srcdoc=m.body_html;
    } else {
      txt.style.display='block';
      txt.textContent=m.body_text;
    }
  }catch(e){
    document.getElementById('reader-subject').textContent='Error';
    txt.style.display='block'; txt.textContent=e.message;
  }
}

document.getElementById('exp-import-btn').addEventListener('click',()=>document.getElementById('exp-import-file').click());
document.getElementById('exp-import-file').addEventListener('change',async e=>{
  const file=e.target.files[0];
  if(!file)return;
  
  const modal=document.getElementById('reader-modal');
  const frame=document.getElementById('reader-frame');
  const txt=document.getElementById('reader-text');
  const atts=document.getElementById('reader-attachments');
  
  modal.classList.add('show');
  document.getElementById('reader-subject').textContent='Parseando archivo local…';
  atts.innerHTML=''; frame.style.display='none'; txt.style.display='none';

  try {
    // Leemos el archivo como ArrayBuffer para enviarlo al servidor
    const buffer = await file.arrayBuffer();
    const r=await fetch(`${API}/api/read-eml`, {
      method: 'POST',
      headers: {'Content-Type': 'application/octet-stream'},
      body: buffer
    });
    const d=await r.json();
    if(!r.ok) throw new Error(d.error||'Error parseando archivo');
    
    const m=d.data;
    document.getElementById('reader-subject').textContent=m.subject;
    document.getElementById('reader-from').textContent=m.from;
    document.getElementById('reader-to').textContent=m.to;
    document.getElementById('reader-date').textContent=m.date;
    
    if(m.attachments.length) buildEmlAttachmentChips(m.attachments, atts);
    
    if(m.body_html){
      frame.style.display='block';
      frame.srcdoc=m.body_html;
    } else {
      txt.style.display='block';
      txt.textContent=m.body_text;
    }
    toast(`Archivo "${file.name}" cargado`,'ok');
  } catch(e) {
    document.getElementById('reader-subject').textContent='Error';
    txt.style.display='block'; txt.textContent=e.message;
    toast('Error: '+e.message,'err');
  }
  e.target.value=''; // Reset input
});

['reader-x','reader-close'].forEach(id=>document.getElementById(id).addEventListener('click',()=>document.getElementById('reader-modal').classList.remove('show')));

// Resúmenes y tendencias: static/summary.js

// ── DELETE ────────────────────────────────────────────────
function openDel(ids){pendingDel=ids;document.getElementById('del-msg').innerHTML=`¿Ocultar <b>${ids.length}</b> correo${ids.length>1?'s':''} de la vista?<br><small>No afecta a Gmail.</small>`;document.getElementById('del-modal').classList.add('show');}
document.getElementById('del-cx').addEventListener('click',()=>{document.getElementById('del-modal').classList.remove('show');pendingDel=[];});
document.getElementById('del-ok').addEventListener('click',()=>{pendingDel.forEach(id=>{deleted.add(id);selected.delete(id);openMessages.delete(id);});document.getElementById('del-modal').classList.remove('show');toast(`${pendingDel.length} ocultado${pendingDel.length>1?'s':''}`,'ok');pendingDel=[];queueSaveState();render();});
document.getElementById('manage-hidden').addEventListener('click',openHiddenReview);
['hidden-x','hidden-cn'].forEach(id=>document.getElementById(id).addEventListener('click',closeHiddenReview));
document.getElementById('hidden-prev').addEventListener('click',()=>{if(hiddenReviewPage>1)loadHiddenReviewPage(hiddenReviewPage-1);});
document.getElementById('hidden-next').addEventListener('click',()=>{if(hiddenReviewPage<hiddenReviewPages)loadHiddenReviewPage(hiddenReviewPage+1);});
document.getElementById('hidden-search').addEventListener('keydown',e=>{
  if(e.key==='Enter'){
    hiddenSearchQuery=e.target.value.trim();
    loadHiddenReviewPage(1);
  }
});
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
// Cabeceras de panel plegables (antes onclick inline en index.html)
document.querySelectorAll('.ph[data-panel]').forEach(h=>h.addEventListener('click',()=>togglePanel(h.dataset.panel)));

// ── INIT ──────────────────────────────────────────────────
async function init(){
  await loadBaseConfig();
  await loadState();
  await loadLocalExports();
  renderSenders();
  renderRules();
  renderCats();
  render();
  const status=await checkStatus();
  if(status&&status.token){
    await refreshSourcesFromGmail();
    // Cargar etiquetas de Gmail al arrancar para que el selector de reglas esté listo
    fetchGmailLabels();
  }
  
  // Soporte para abrir archivo externo via URL (?view=/path/to/file.eml)
  const viewPath=new URLSearchParams(window.location.search).get('view');
  if(viewPath) openEmlReader('', viewPath);
}
init();
