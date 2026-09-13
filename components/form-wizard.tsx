'use client';
import {useEffect,useRef,useState} from 'react';
import Link from 'next/link';
import {ArrowDownToLine,ArrowLeft,ArrowRight,ArrowUpRight,BookOpen,Check,CheckCheck,ChevronDown,Eye,FileText,HelpCircle,LoaderCircle,ScanLine,Upload,X} from 'lucide-react';
import {api,type Case,type Health} from '@/lib/types';
import type {FormCatalog,FormField,OcrBatch,Provenance} from '@/lib/form-types';
import {useFormDraft} from '@/lib/use-form-draft';
import {Loading,Message} from './ui';
import Advisor from './advisor';

const steps=['Votre démarche','L’entreprise','Les personnes','Coordonnées','Votre déclaration'];
const subtitles=['Choisissez ce qui change.','Identifiez l’entreprise concernée.','Indiquez qui représente et qui déclare.','Précisez les coordonnées de suivi.','Relisez les informations avant de préparer le PDF.'];
const kinds=[['registry','Extrait RNE / pièce fiscale'],['representative','Identité du représentant'],['declarant','Identité du déclarant'],['bank','Document bancaire'],['reservation','Certificat de réservation'],['form','Formulaire déjà renseigné']];

export default function FormWizard({c,health,onUpdate}:{c:Case;health:Health|null;onUpdate:()=>Promise<void>}){
  const {draft,loading,status,error,setError,change,flush,commit,recovery,restore,discard}=useFormDraft(c.id);
  const [catalog,setCatalog]=useState<FormCatalog|null>(null);
  const [notice,setNotice]=useState(''),[busy,setBusy]=useState(''),[showErrors,setShowErrors]=useState(false);
  const [focused,setFocused]=useState(''),[help,setHelp]=useState<string|null>(null);
  const [query,setQuery]=useState(''),[group,setGroup]=useState('');
  const [kind,setKind]=useState('registry'),[existing,setExisting]=useState('');
  const [batch,setBatch]=useState<OcrBatch|null>(null),[choices,setChoices]=useState<Record<string,number>>({});
  const [reviewed,setReviewed]=useState(false),[page,setPage]=useState(1),[advisor,setAdvisor]=useState(false);
  const input=useRef<HTMLInputElement>(null),ocrDialog=useRef<HTMLDialogElement>(null),preview=useRef<HTMLDialogElement>(null);
  const base='/cases/'+c.id+'/f005';
  const locked=draft.locked||['submitted','reviewed'].includes(c.status);
  useEffect(()=>{let active=true;api<FormCatalog>('/f005/catalog').then(data=>{if(active)setCatalog(data);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[setError]);
  useEffect(()=>{if(batch)ocrDialog.current?.showModal();},[batch]);
  const visible=(f:FormField)=>!f.visible_when||f.visible_when.some(k=>draft.modifications.includes(k));
  const required=(f:FormField)=>f.required||!!f.required_when?.some(k=>draft.modifications.includes(k));
  const activeFields=catalog?.fields.filter(visible)||[];
  const missing=Object.keys(draft.errors);
  const completeCount=activeFields.filter(f=>required(f)&&draft.fields[f.key]?.trim()&&!draft.errors[f.key]).length;
  const requiredCount=activeFields.filter(required).length;
  const modifications=catalog?.modifications.filter(m=>(!group||m.group===group)&&(!query||(m.label+' '+m.arabic+' '+m.help).toLocaleLowerCase().includes(query.toLocaleLowerCase())))||[];
  const selectedMods=catalog?.modifications.filter(m=>draft.modifications.includes(m.key))||[];
  const sourceUrl=(id:string)=>'/api/cases/'+c.id+'/documents/'+id+'/file';
  async function go(step:number,validate=false){
    if(locked){change({step});return;}
    try{
      const saved=await flush();
      const relevant=draft.step===0?['modifications']:activeFields.filter(f=>f.step===draft.step).map(f=>f.key);
      if(validate&&relevant.some(k=>saved.errors[k])){setShowErrors(true);document.getElementById('field-'+relevant.find(k=>saved.errors[k]))?.focus();return;}
      change({step});await flush();setShowErrors(false);setPage(step>=3?2:1);
      if(step===1)setKind('registry');if(step===2)setKind('representative');
      document.getElementById('step-heading')?.focus();
    }catch{}
  }
  function updateField(key:string,value:string){
    const provenance={...draft.provenance};delete provenance[key];
    change({fields:{...draft.fields,[key]:value},provenance});setReviewed(false);
  }
  async function read(file?:File){
    if(!file&&!existing)return;setBusy('ocr');setError('');setNotice('');
    try{
      await flush();let result:OcrBatch;
      if(file){const data=new FormData();data.append('file',file);data.append('kind',kind);result=await api<OcrBatch>(base+'/ocr',{method:'POST',body:data});}
      else result=await api<OcrBatch>(base+'/import',{method:'POST',body:JSON.stringify({document_id:existing,kind})});
      setChoices({});setBatch(result);await onUpdate();
    }catch(e){setError(e instanceof Error?e.message:'Lecture indisponible.');await onUpdate();}
    finally{setBusy('');if(input.current)input.current.value='';}
  }
  function apply(){
    if(!batch)return;const fields={...draft.fields},provenance={...draft.provenance};
    Object.entries(choices).forEach(([key,index])=>{
      const candidate=batch.candidates[index];let value=candidate.value.trim();
      if(['identifiant_unique','rib','identite_representant','identite_declarant'].includes(key))value=value.replace(/[\s-]/g,'');
      if(key==='date'&&/^\d{2}\/\d{2}\/\d{4}$/.test(value)){const parts=value.split('/');value=parts[2]+'-'+parts[1]+'-'+parts[0];}
      fields[key]=value;
      if(batch.document_id)provenance[key]={document_id:batch.document_id,page:candidate.page,evidence:candidate.evidence,value} satisfies Provenance;
    });
    change({fields,provenance,imports:[...draft.imports.filter(b=>b.id!==batch.id),batch]});setReviewed(false);
    setNotice(Object.keys(choices).length+' information(s) reprises. Vérifiez les champs renseignés.');ocrDialog.current?.close();
  }
  async function generate(){
    setBusy('pdf');setError('');
    try{await flush();const result=await api<typeof draft>(base+'/generate',{method:'POST',body:JSON.stringify({revision:draft.revision,reviewed})});commit(result);await onUpdate();setNotice('Votre PDF est prêt. La signature reste à effectuer.');}
    catch(e){setError(e instanceof Error?e.message:'Préparation du PDF indisponible.');}finally{setBusy('');}
  }
  function field(f:FormField){
    const invalid=showErrors&&!!draft.errors[f.key];const proof=draft.provenance[f.key];
    const copied=draft.same_person&&['nom_declarant','identite_declarant'].includes(f.key);
    return <div className={'form-field '+(invalid?'invalid':'')} key={f.key}>
      <div className="field-heading"><label htmlFor={'field-'+f.key}>{f.label}{required(f)&&<span aria-label="nécessaire"> *</span>}</label><button type="button" className="field-help" onClick={()=>{setHelp(help===f.key?null:f.key);setFocused(f.key);}} aria-expanded={help===f.key} aria-controls={'help-'+f.key}><HelpCircle size={16}/><span>Comprendre</span></button></div>
      <span className="field-arabic" lang="ar" dir="rtl">{f.arabic}</span>
      <input id={'field-'+f.key} name={f.key} type={f.input_type} value={draft.fields[f.key]||''} onFocus={()=>setFocused(f.key)} onChange={e=>updateField(f.key,f.key==='identifiant_unique'?e.target.value.toUpperCase():e.target.value)} disabled={!!locked||copied} maxLength={f.max_length} placeholder={f.example} autoComplete={f.key==='email'?'email':f.key==='gsm'?'tel':'off'} inputMode={f.key==='rib'?'numeric':undefined} spellCheck={false} dir={['email','tel','date'].includes(f.input_type)?'ltr':'auto'} aria-invalid={invalid} aria-describedby={'hint-'+f.key}/>
      <p id={'hint-'+f.key} className={invalid?'field-error':'field-hint'}>{invalid?draft.errors[f.key]:copied?'Repris du représentant légal.':f.help}</p>
      {proof&&<a className="provenance" href={sourceUrl(proof.document_id)} target="_blank" rel="noreferrer"><ScanLine size={13}/>Repris d’une pièce · page {proof.page}<ArrowUpRight size={13}/></a>}
      {help===f.key&&<div id={'help-'+f.key} className="inline-help"><strong>Où trouver cette information</strong><p>{f.where}</p><p>{f.tip}</p><a href={catalog?.sources[f.source]?.url} target="_blank" rel="noreferrer">Voir le formulaire de référence <ArrowUpRight size={13}/></a></div>}
    </div>;
  }
  if(loading||!catalog)return error?<Message error>{error}</Message>:<Loading text="Ouverture de votre déclaration…"/>;
  return <>
    <div className="breadcrumb"><Link href={'/dossiers/'+c.id}>{c.company}</Link><span>/</span><span>Déclaration de modification</span></div>
    <div className="form-topline"><div><span className="section-kicker">{catalog.version} · Personne morale</span><h1>Votre déclaration, <span className="serif-word">pas à pas.</span></h1></div><div className={'save-state '+status} role="status">{status==='saving'?<LoaderCircle className="spin" size={15}/>:status==='saved'?<CheckCheck size={16}/>:null}{status==='saved'?'Enregistré':status==='dirty'?'Saisie en cours':status==='saving'?'Enregistrement…':'À enregistrer'}</div></div>
    {error&&<Message error>{error}<button className="text-link" onClick={()=>void flush().catch(()=>{})}>Réessayer l’enregistrement</button></Message>}
    {notice&&<Message>{notice}</Message>}
    {locked&&<Message>Ce dossier est en revue. Vous pouvez consulter la déclaration et télécharger les documents.</Message>}
    {recovery&&<Message>Une saisie non enregistrée est disponible dans cet onglet.<button className="text-link" onClick={restore}>Restaurer</button><button className="text-link" onClick={discard}>Ignorer</button></Message>}
    <nav className="form-stepper" aria-label="Étapes de la déclaration">{steps.map((label,i)=><button key={label} onClick={()=>void go(i)} aria-current={draft.step===i?'step':undefined} className={draft.step===i?'active':''}><span>{i+1}</span>{label}</button>)}</nav>
    <div className="form-grid"><main className="form-sheet" id="form-main">
      <div className="sheet-heading"><span className="section-kicker">Étape {draft.step+1} sur {steps.length}</span><h2 id="step-heading" tabIndex={-1}>{steps[draft.step]}</h2><p>{subtitles[draft.step]}</p></div>
      {draft.step===0&&<>
        <div className="filter-row"><label className="sr-only" htmlFor="mod-search">Rechercher une modification</label><input id="mod-search" type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Rechercher : adresse, dirigeant…"/><label className="sr-only" htmlFor="mod-group">Catégorie</label><select id="mod-group" value={group} onChange={e=>setGroup(e.target.value)}><option value="">Toutes les catégories</option>{Array.from(new Set(catalog.modifications.map(m=>m.group))).map(g=><option key={g}>{g}</option>)}</select></div>
        <div className="modification-list">{modifications.map(m=><label className={'modification '+(draft.modifications.includes(m.key)?'selected':'')} key={m.key}><input type="checkbox" checked={draft.modifications.includes(m.key)} disabled={!!locked} onChange={()=>{change({modifications:draft.modifications.includes(m.key)?draft.modifications.filter(k=>k!==m.key):[...draft.modifications,m.key]});setReviewed(false);}}/><span><strong>{m.label}</strong><small>{m.help}</small><span className="mod-arabic" lang="ar" dir="rtl">{m.arabic}</span></span></label>)}</div>
        {!modifications.length&&<p className="muted">Aucune modification ne correspond à votre recherche.</p>}
        {showErrors&&draft.errors.modifications&&<p className="field-error" role="alert">{draft.errors.modifications}</p>}
        <p className="scope-note">Vous préparez les rubriques du F005. Les pièces et conditions de dépôt dépendent de la formalité choisie. <a href={catalog.sources.procedures.url} target="_blank" rel="noreferrer">Consulter le répertoire RNE</a></p>
      </>}
      {[1,2].includes(draft.step)&&!locked&&<details className="import-panel" open><summary><ScanLine size={20}/><span>Reprendre les informations d’une pièce<small>Importez une fois, confirmez les valeurs utiles.</small></span><ChevronDown size={17}/></summary><div className="import-body">
        <label>Quelle pièce souhaitez-vous lire ?<select value={kind} onChange={e=>setKind(e.target.value)}>{kinds.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
        <div className="import-actions"><button className="button secondary" onClick={()=>input.current?.click()} disabled={!!busy}><Upload size={16}/>{busy==='ocr'?'Lecture en cours…':'Importer un document'}</button><span className="muted small">PDF, JPG, PNG ou TXT · 8 Mo max.</span></div>
        {c.documents.filter(d=>!d.sample).length>0&&<div className="library-reuse"><label htmlFor="existing-document">Ou utiliser une pièce du dossier</label><div><select id="existing-document" value={existing} onChange={e=>setExisting(e.target.value)}><option value="">Choisir une pièce…</option>{c.documents.filter(d=>!d.sample).map(d=><option key={d.id} value={d.id}>{d.name}</option>)}</select><button className="button secondary" disabled={!existing||!!busy} onClick={()=>void read()}>Lire</button></div></div>}
        <p className="processing-note">{health?.ocr_provider?.startsWith('Azure')?'Les documents à lire sont transmis au service Azure configuré.':health?.ocr_provider==='OCR Windows'?'Les images sont lues par le service OCR de cet ordinateur.':'La saisie manuelle reste disponible. Configurez un service OCR pour lire les images.'} Vérifiez les suggestions avant de les reprendre.</p>
      </div></details>}
      {draft.step===1&&<div className="fields-grid">{activeFields.filter(f=>f.step===1).map(field)}</div>}
      {draft.step===2&&<><p className="scope-note" lang="fr">{catalog.guidance.language}</p><div className="field-section"><h3>Représentant de l’entreprise</h3>{activeFields.filter(f=>['representant_legal','identite_representant'].includes(f.key)).map(field)}</div><label className="same-person"><input type="checkbox" checked={draft.same_person} disabled={!!locked} onChange={e=>{change({same_person:e.target.checked});setReviewed(false);}}/><span><strong>Cette personne fait aussi la déclaration</strong><small>Son nom et son identité seront repris ci-dessous.</small></span></label><div className="field-section"><h3>Personne qui déclare</h3>{activeFields.filter(f=>['nom_declarant','identite_declarant'].includes(f.key)).map(field)}</div></>}
      {draft.step===3&&<div className="fields-grid">{activeFields.filter(f=>f.step===3).map(field)}</div>}
      {draft.step===4&&<>
        <div className="review-heading"><FileText size={24}/><div><strong>{c.company}</strong><p>{selectedMods.map(m=>m.label).join(' · ')||'Aucune modification sélectionnée'}</p></div></div>
        <dl className="review-fields">{activeFields.map(f=><div key={f.key}><dt>{f.label}</dt><dd dir="auto">{draft.fields[f.key]||<span className="missing">Non renseigné</span>}</dd>{draft.errors[f.key]&&<button className="text-link" onClick={()=>void go(f.step)}>Compléter <ArrowRight size={13}/></button>}</div>)}</dl>
        <button className="button secondary" onClick={async()=>{await flush().catch(()=>{});preview.current?.showModal();}}><Eye size={16}/>Vérifier l’aperçu du PDF</button>
        {!draft.ready&&<p className="field-error">{missing.length} point(s) à compléter ou corriger avant la préparation du PDF.</p>}
        <p className="scope-note">{catalog.guidance.signature}</p>
        {!locked&&!draft.has_pdf&&<><label className="same-person"><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/><span>J’ai relu les informations et vérifié leur correspondance avec mes pièces.</span></label><button className="button primary full" disabled={!reviewed||!draft.ready||!!busy||status!=='saved'} onClick={()=>void generate()}>{busy==='pdf'?<LoaderCircle size={17} className="spin"/>:<FileText size={17}/>}Préparer mon PDF</button></>}
        {draft.has_pdf&&<div className="download-panel"><CheckCheck size={25}/><h3>Votre déclaration est prête.</h3><p>Conservez le PDF et les pièces dans un même dossier.</p><a className="button primary" href={'/api'+base+'/pdf'}><ArrowDownToLine size={17}/>Télécharger le F005</a><a className="button secondary" href={'/api/cases/'+c.id+'/export'}><ArrowDownToLine size={17}/>Télécharger le dossier complet</a><Link className="text-link" href={'/dossiers/'+c.id+'/preparation'}>Préparer la revue <ArrowRight size={16}/></Link></div>}
      </>}
      <footer className="form-navigation">{draft.step>0?<button className="button quiet" onClick={()=>void go(draft.step-1)}><ArrowLeft size={16}/>Précédent</button>:<Link className="button quiet" href={'/dossiers/'+c.id}><ArrowLeft size={16}/>Dossier</Link>}{draft.step<4&&<button className="button primary" disabled={!!busy} onClick={()=>void go(draft.step+1,true)}>Continuer <ArrowRight size={16}/></button>}</footer>
    </main><aside className="form-companion">
      <div className="folio-note"><span className="section-kicker">Votre dossier</span><h3>{c.company}</h3><div className="completion-number">{completeCount}<span> / {requiredCount}</span></div><p>champs nécessaires renseignés et au format attendu</p><div className="completion-track"><span style={{width:requiredCount?(completeCount/requiredCount*100)+'%':'0%'}}/></div><div className="folio-detail"><span>Pièces réunies</span><strong>{c.documents.length}</strong></div><div className="folio-detail"><span>Modifications choisies</span><strong>{draft.modifications.length}</strong></div><button className="button secondary full" onClick={async()=>{await flush().catch(()=>{});preview.current?.showModal();}}><Eye size={16}/>Voir le formulaire</button></div>
      <div className="help-note"><BookOpen size={22}/><h3>Un repère à chaque étape.</h3><p>« Comprendre » explique chaque champ. Pour une question complémentaire, consultez l’aide avec ses références.</p><button className="text-link" onClick={()=>setAdvisor(true)}>Ouvrir l’aide <ArrowUpRight size={15}/></button></div>
    </aside></div>
    <div className="mobile-form-tools"><button className="button secondary" onClick={()=>preview.current?.showModal()}><Eye size={16}/>Aperçu</button><button className="button secondary" onClick={()=>setAdvisor(true)}><HelpCircle size={16}/>Aide</button></div>
    <input hidden ref={input} type="file" accept=".pdf,.png,.jpg,.jpeg,.txt" onChange={e=>{if(e.target.files?.[0])void read(e.target.files[0]);}}/>
    <dialog ref={ocrDialog} className="dialog ocr-dialog" aria-labelledby="ocr-title"><div className="dialog-heading"><span className="section-kicker">Lecture du document</span><button className="icon-button" aria-label="Fermer les suggestions" onClick={()=>ocrDialog.current?.close()}><X size={20}/></button></div><h2 id="ocr-title">Vérifiez, puis reprenez.</h2><p className="muted">{batch?.name} · {batch?.method}{batch?.cached?' · Lecture réutilisée':''}</p>{batch?.warnings?.map(w=><Message key={w}>{w}</Message>)}
      {batch?.candidates.length===0?<p>Aucune valeur suffisamment étayée n’a été identifiée. Consultez le texte lu ou renseignez les champs manuellement.</p>:batch?.candidates.map((candidate,i)=><label className="candidate" key={candidate.key+i}><input type="checkbox" checked={choices[candidate.key]===i} onChange={()=>setChoices(old=>{const next={...old};if(next[candidate.key]===i)delete next[candidate.key];else next[candidate.key]=i;return next;})}/><span><small>{catalog.fields.find(f=>f.key===candidate.key)?.label}</small><strong dir="auto">{candidate.value}</strong><blockquote dir="auto">{candidate.evidence}</blockquote><span className="muted small">Page {candidate.page}{candidate.confidence!=null?' · Confiance de lecture : '+Math.round(candidate.confidence*100)+' %':''}</span>{draft.fields[candidate.key]&&draft.fields[candidate.key]!==candidate.value&&<span className="field-error">Remplacera : {draft.fields[candidate.key]}</span>}</span></label>)}
      {batch&&<><a className="text-link" href={batch.document_id?sourceUrl(batch.document_id):'/api'+base+'/ocr/'+batch.id} target="_blank" rel="noreferrer">Ouvrir l’original <ArrowUpRight size={15}/></a><details className="raw-text"><summary>Voir le texte lu</summary>{batch.pages.map(p=><pre dir="auto" key={p.page}>{p.text}</pre>)}</details></>}
      <div className="dialog-actions"><button className="button secondary" onClick={()=>ocrDialog.current?.close()}>Fermer</button><button className="button primary" disabled={!Object.keys(choices).length} onClick={apply}>Reprendre {Object.keys(choices).length} information(s)<Check size={16}/></button></div>
    </dialog>
    <dialog ref={preview} className="dialog preview-dialog" aria-labelledby="preview-title"><div className="dialog-heading"><h2 id="preview-title">Aperçu du formulaire</h2><button className="icon-button" aria-label="Fermer l’aperçu" onClick={()=>preview.current?.close()}><X size={20}/></button></div><div className="preview-tabs">{[1,2].map(p=><button className={'button '+(page===p?'primary':'secondary')} key={p} onClick={()=>setPage(p)}>Page {p}</button>)}<span className="muted small">Brouillon non signé</span></div><img src={'/api'+base+'/preview/'+page+'?revision='+draft.revision} width={893} height={1263} alt={'Aperçu F005, page '+page}/></dialog>
    {advisor&&<div className="drawer-backdrop" onClick={()=>setAdvisor(false)}><div className="drawer-panel" onClick={e=>e.stopPropagation()}><Advisor caseId={c.id} field={focused||undefined} health={health} onClose={()=>setAdvisor(false)}/></div></div>}
  </>;
}
