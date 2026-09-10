// ── PERIODIC SUMMARY ───────────────────────────────────────
// Depende de `App.*` (static/shared.js) y de funciones helper de app.js
// (esc, gurl, itemMeta, messageSeverity, severityRank, severityReason, toast,
// CATS). Estado propio de este módulo: summaryDays / summaryData.
let summaryDays=30,summaryData=null;

function countBy(items,keyFn){
  const out={};
  items.forEach(item=>{const key=keyFn(item);if(key)out[key]=(out[key]||0)+1;});
  return Object.entries(out).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]));
}
function periodCutoff(days){
  const date=new Date();
  date.setUTCHours(0,0,0,0);
  date.setUTCDate(date.getUTCDate()-(days-1));
  return date.toISOString().slice(0,10);
}
function dateDaysAgo(days){
  const date=new Date();
  date.setUTCHours(0,0,0,0);
  date.setUTCDate(date.getUTCDate()-days);
  return date.toISOString().slice(0,10);
}
function visibleDatedItems(){
  return activeEmails
    .filter(e=>!App.state.deleted.has(e.id)&&/^\d{4}-\d{2}-\d{2}$/.test(e.date||''))
    .map(itemMeta);
}
function itemsBetween(items,start,end){
  return items.filter(e=>(e.date||'')>=start&&(e.date||'')<=end);
}
function countsMap(items,keyFn){
  return Object.fromEntries(countBy(items,keyFn));
}
function increasingCounts(current,previous,minCount=2){
  return Object.entries(current)
    .map(([key,count])=>[key,count,count-(previous[key]||0)])
    .filter(([,count,delta])=>count>=minCount&&delta>0)
    .sort((a,b)=>b[2]-a[2]||b[1]-a[1]||a[0].localeCompare(b[0]));
}
function recurringSubjectKey(subject){
  return String(subject||'').toLowerCase()
    .replace(/^(re|fw|fwd)\s*:\s*/g,'')
    .replace(/\b\d{1,4}([./:-]\d{1,4})+\b/g,'#')
    .replace(/\b\d+\b/g,'#')
    .replace(/[^\p{L}\p{N}#]+/gu,' ')
    .replace(/\s+/g,' ')
    .trim()
    .slice(0,120);
}
function buildTrendAnalysis(days,allItems){
  const currentStart=dateDaysAgo(days-1);
  const currentEnd=dateDaysAgo(0);
  const previousStart=dateDaysAgo((days*2)-1);
  const previousEnd=dateDaysAgo(days);
  const current=itemsBetween(allItems,currentStart,currentEnd);
  const previous=itemsBetween(allItems,previousStart,previousEnd);
  const currentHigh=current.filter(e=>messageSeverity(e)==='high').length;
  const previousHigh=previous.filter(e=>messageSeverity(e)==='high').length;
  const currentProviders=countsMap(current,e=>e._provider);
  const previousProviders=countsMap(previous,e=>e._provider);
  const currentCategories=countsMap(current.flatMap(e=>e._categories.map(category=>({category}))),item=>item.category);
  const previousCategories=countsMap(previous.flatMap(e=>e._categories.map(category=>({category}))),item=>item.category);
  const subjectGroups={};
  current.forEach(e=>{
    const key=recurringSubjectKey(e._summary);
    if(key.length<5)return;
    const group=subjectGroups[key]||(subjectGroups[key]={label:e._summary,count:0,provider:e._provider});
    group.count++;
  });
  return {
    currentStart,
    currentEnd,
    previousStart,
    previousEnd,
    volume:{current:current.length,previous:previous.length,delta:current.length-previous.length},
    high:{current:currentHigh,previous:previousHigh,delta:currentHigh-previousHigh},
    providerIncreases:increasingCounts(currentProviders,previousProviders),
    categoryIncreases:increasingCounts(currentCategories,previousCategories),
    recurringSubjects:Object.values(subjectGroups).filter(group=>group.count>=2).sort((a,b)=>b.count-a.count||a.label.localeCompare(b.label)).slice(0,8),
  };
}
function buildPeriodicSummary(days){
  const cutoff=periodCutoff(days);
  const allItems=visibleDatedItems();
  const items=allItems
    .filter(e=>(e.date||'')>=cutoff)
    .sort((a,b)=>severityRank(a)-severityRank(b)||(b.date||'').localeCompare(a.date||''));
  const severity=items.reduce((acc,e)=>{acc[messageSeverity(e)]++;return acc;},{high:0,medium:0,low:0});
  const categories=countBy(items.flatMap(e=>e._categories.map(category=>({category}))),item=>item.category);
  return {
    days,
    cutoff,
    generatedAt:new Date().toISOString(),
    count:items.length,
    severity,
    providers:countBy(items,e=>e._provider),
    categories,
    actions:items.filter(e=>messageSeverity(e)==='high').slice(0,8),
    trends:buildTrendAnalysis(days,allItems),
  };
}
function summaryRows(entries,labelFn=value=>value){
  if(!entries.length)return'<div class="sum-row"><span>Sin datos</span><b>0</b></div>';
  return entries.slice(0,6).map(([label,count])=>`<div class="sum-row"><span>${esc(labelFn(label))}</span><b>${count}</b></div>`).join('');
}
function summaryMarkdown(summary){
  const providers=summary.providers.slice(0,10).map(([name,count])=>`- ${name}: ${count}`).join('\n')||'- Sin datos';
  const categories=summary.categories.slice(0,10).map(([key,count])=>`- ${(CATS[key]&&CATS[key].label)||key}: ${count}`).join('\n')||'- Sin datos';
  const actions=summary.actions.map(e=>`- [${e._summary}](${gurl(e.id)}) · ${e._provider} · ${e.date} · ${severityReason(e)}`).join('\n')||'- Sin acciones de severidad alta';
  const providerTrends=summary.trends.providerIncreases.slice(0,10).map(([name,count,delta])=>`- ${name}: ${count} (${formatDelta(delta)})`).join('\n')||'- Sin aumentos relevantes';
  const categoryTrends=summary.trends.categoryIncreases.slice(0,10).map(([key,count,delta])=>`- ${(CATS[key]&&CATS[key].label)||key}: ${count} (${formatDelta(delta)})`).join('\n')||'- Sin aumentos relevantes';
  const recurring=summary.trends.recurringSubjects.map(item=>`- ${item.label} · ${item.provider}: ${item.count} repeticiones`).join('\n')||'- Sin asuntos recurrentes';
  return [
    `# Resumen operativo · últimos ${summary.days} días`,
    '',
    `- Desde: ${summary.cutoff}`,
    `- Generado: ${summary.generatedAt}`,
    `- Correos cargados y visibles: ${summary.count}`,
    `- Severidad alta: ${summary.severity.high}`,
    `- Severidad media: ${summary.severity.medium}`,
    `- Severidad baja: ${summary.severity.low}`,
    '',
    '## Proveedores principales',
    providers,
    '',
    '## Categorías principales',
    categories,
    '',
    '## Acciones prioritarias',
    actions,
    '',
    '## Tendencias frente al período anterior',
    `- Volumen: ${summary.trends.volume.current} frente a ${summary.trends.volume.previous} (${formatDelta(summary.trends.volume.delta)})`,
    `- Severidad alta: ${summary.trends.high.current} frente a ${summary.trends.high.previous} (${formatDelta(summary.trends.high.delta)})`,
    '',
    '### Proveedores al alza',
    providerTrends,
    '',
    '### Categorías al alza',
    categoryTrends,
    '',
    '### Patrones recurrentes',
    recurring,
  ].join('\n');
}
function formatDelta(delta){return delta>0?`+${delta}`:String(delta);}
function trendClass(delta){return delta>0?'trend-up':delta<0?'trend-down':'trend-flat';}
function trendRows(entries,labelFn=value=>value){
  if(!entries.length)return'<div class="sum-row"><span>Sin aumentos relevantes</span><b>—</b></div>';
  return entries.slice(0,6).map(([label,count,delta])=>`<div class="sum-row"><span>${esc(labelFn(label))}</span><b class="trend-up">${count} · ${formatDelta(delta)}</b></div>`).join('');
}
function renderPeriodicSummary(){
  summaryData=buildPeriodicSummary(summaryDays);
  document.getElementById('sum-ttl').textContent=`Resumen · últimos ${summaryDays} días`;
  document.querySelectorAll('#sum-period .mtb').forEach(t=>t.classList.toggle('on',Number(t.dataset.days)===summaryDays));
  const view=document.getElementById('sum-view');
  if(!summaryData.count){
    view.innerHTML=`<div class="sum-empty">No hay correos cargados y visibles desde ${esc(summaryData.cutoff)}.</div>`;
    return;
  }
  view.innerHTML=`
    <div class="sum-grid">
      <div class="sum-card" style="border-color:#f8717155;color:var(--d)"><span>Severidad alta</span><b>${summaryData.severity.high}</b></div>
      <div class="sum-card" style="border-color:#fb923c55;color:var(--o)"><span>Severidad media</span><b>${summaryData.severity.medium}</b></div>
      <div class="sum-card" style="border-color:#34d39955;color:var(--s)"><span>Severidad baja</span><b>${summaryData.severity.low}</b></div>
    </div>
    <div class="sum-sections">
      <section class="sum-section"><h3>Proveedores principales</h3><div class="sum-list">${summaryRows(summaryData.providers)}</div></section>
      <section class="sum-section"><h3>Categorías principales</h3><div class="sum-list">${summaryRows(summaryData.categories,key=>(CATS[key]&&CATS[key].label)||key)}</div></section>
    </div>
    <section class="sum-section" style="margin-bottom:10px"><h3>Acciones prioritarias</h3><div class="sum-actions">${
      summaryData.actions.length
        ?summaryData.actions.map(e=>`<div class="sum-action"><b>${esc(e._summary)}</b><span>${esc(e._provider)} · ${esc(e.date)} · ${esc(severityReason(e))}</span></div>`).join('')
        :'<div class="sum-row"><span>Sin acciones de severidad alta</span></div>'
    }</div></section>
    <section class="sum-section">
      <h3>Tendencias frente al período anterior</h3>
      <p class="trend-note">${esc(summaryData.trends.currentStart)}–${esc(summaryData.trends.currentEnd)} frente a ${esc(summaryData.trends.previousStart)}–${esc(summaryData.trends.previousEnd)}.</p>
      <div class="sum-grid">
        <div class="sum-card"><span>Volumen</span><b class="${trendClass(summaryData.trends.volume.delta)}">${summaryData.trends.volume.current} · ${formatDelta(summaryData.trends.volume.delta)}</b></div>
        <div class="sum-card"><span>Severidad alta</span><b class="${trendClass(summaryData.trends.high.delta)}">${summaryData.trends.high.current} · ${formatDelta(summaryData.trends.high.delta)}</b></div>
        <div class="sum-card"><span>Patrones recurrentes</span><b>${summaryData.trends.recurringSubjects.length}</b></div>
      </div>
      <div class="sum-sections">
        <div><h3>Proveedores al alza</h3><div class="sum-list">${trendRows(summaryData.trends.providerIncreases)}</div></div>
        <div><h3>Categorías al alza</h3><div class="sum-list">${trendRows(summaryData.trends.categoryIncreases,key=>(CATS[key]&&CATS[key].label)||key)}</div></div>
      </div>
      <div><h3>Asuntos recurrentes</h3><div class="sum-list">${
        summaryData.trends.recurringSubjects.length
          ?summaryData.trends.recurringSubjects.map(item=>`<div class="sum-row"><span>${esc(item.label)} · ${esc(item.provider)}</span><b>${item.count}</b></div>`).join('')
          :'<div class="sum-row"><span>Sin asuntos repetidos</span><b>—</b></div>'
      }</div></div>
    </section>`;
}
function openPeriodicSummary(){
  summaryDays=30;
  document.getElementById('sum-modal').classList.add('show');
  renderPeriodicSummary();
}
async function requestAiSummary(){
  if(!aiStatus.configured){
    toast('Configura AI_BASE_URL y AI_MODEL en el servidor','err');
    return;
  }
  if(aiStatus.remote&&!confirm('El resumen operativo se enviará al proveedor AI remoto configurado. ¿Continuar?'))return;
  const button=document.getElementById('sum-ai');
  const result=document.getElementById('sum-ai-result');
  button.disabled=true;
  button.textContent='Resumiendo…';
  try{
    const r=await fetch(`${App.api}/api/ai-summary`,{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({prompt:summaryMarkdown(summaryData||buildPeriodicSummary(summaryDays))})
    });
    const data=await r.json().catch(()=>({error:'Respuesta AI inválida'}));
    if(!r.ok)throw new Error(data.detail||data.error||('Error HTTP '+r.status));
    result.hidden=false;
    result.textContent=data.summary;
    toast(`Resumen AI generado · ${data.model}`,'ok');
  }catch(e){
    toast('Error AI: '+e.message,'err');
  }finally{
    button.disabled=false;
    button.textContent='✦ Resumir con AI';
  }
}
document.getElementById('sum-open').addEventListener('click',openPeriodicSummary);
document.querySelectorAll('#sum-period .mtb').forEach(t=>t.addEventListener('click',()=>{summaryDays=Number(t.dataset.days);renderPeriodicSummary();}));
document.getElementById('sum-ai').addEventListener('click',requestAiSummary);
document.getElementById('sum-copy').addEventListener('click',()=>navigator.clipboard.writeText(summaryMarkdown(summaryData||buildPeriodicSummary(summaryDays))).then(()=>toast('Resumen copiado','ok')).catch(()=>toast('Error copiando resumen','err')));
document.getElementById('sum-dl').addEventListener('click',()=>{const blob=new Blob([summaryMarkdown(summaryData||buildPeriodicSummary(summaryDays))],{type:'text/markdown;charset=utf-8'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`resumen_operativo_${summaryDays}d_${new Date().toISOString().slice(0,10)}.md`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);toast('Resumen descargado','ok');});
['sum-x','sum-cn'].forEach(id=>document.getElementById(id).addEventListener('click',()=>document.getElementById('sum-modal').classList.remove('show')));
