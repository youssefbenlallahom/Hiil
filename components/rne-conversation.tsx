'use client';

import {useEffect, useRef, useState} from 'react';
import {ArrowDownToLine, ArrowUpRight, BookOpen, Check, ChevronDown, CircleAlert, FileText, LoaderCircle, Paperclip, Pencil, Send, Sparkles} from 'lucide-react';
import {api} from '@/lib/types';
import Link from 'next/link';
import EvidenceReportView,{EvidenceOverview,EvidenceReport} from './evidence-report';

type Evidence = {origin:'user'|'document';reference_id:string;quote:string;page:number|null};
type Value = {value:string;evidence:Evidence[];confirmed:boolean};
type Reference = {id:string;title:string;page:number|null;url:string|null;text:string};
type State = {
  revision:number;stage:string;values:Record<string,Value>;labels:Record<string,string>;
  modification:string|null;modification_confirmed:boolean;candidates:string[];reason:string;
  cin_document_id:string|null;cin_document_name:string|null;cin_status:string;
  messages:{id:string;role:'user'|'assistant';text:string;source_ids:string[]}[];
  references:Reference[];field_errors:Record<string,string>;blockers:string[];
  ai_configured:boolean;locked:boolean;pdf_revision:number|null;
  report:EvidenceReport;sample:boolean;institution:{submission_id?:string};
};
const choices = [{id:'seat_address', label:'Adresse du siège social'}, {id:'branch_address', label:'Adresse d’une succursale'}, {id:'other', label:'Autre ou plusieurs modifications'}];
const stages:Record<string,string> = {intent:'Votre demande',clarification:'Une précision',identity:'L’identité du déclarant',collecting:'Les informations à compléter',review:'Votre relecture',ready:'Prêt à préparer',prepared:'Formulaire préparé',out_of_scope:'Demande hors du premier parcours'};

export default function RneConversation({caseId,onChanged}:{caseId:string;onChanged:()=>Promise<void>}) {
  const [state,setState]=useState<State|null>(null);
  const [text,setText]=useState('');
  const [busy,setBusy]=useState('');
  const [error,setError]=useState('');
  const [dirty,setDirty]=useState<string[]>([]);
  const [showPdf,setShowPdf]=useState(false);
  const [tab,setTab]=useState<'conversation'|'proofs'>('conversation');
  const file=useRef<HTMLInputElement>(null);
  const history=useRef<HTMLDivElement>(null);
  const inFlight=useRef(false);
  const retry=useRef<{serialized:string;id:string}|null>(null);
  const base=`/cases/${caseId}/rne`;
  useEffect(()=>{let active=true;api<State>(base).then(s=>{if(active)setState(s);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[base]);
  useEffect(()=>{if(history.current)history.current.scrollTop=history.current.scrollHeight;},[state?.messages.length,busy,tab]);
  useEffect(()=>{if(state?.stage!=='prepared')setShowPdf(false);},[state?.stage]);
  async function reload(){try{setState(await api<State>(base));setError('');}catch(e){setError(e instanceof Error?e.message:'Chargement impossible.');}}
  async function turn(payload:Record<string,string>, snapshot=state) {
    if(!snapshot||inFlight.current)return false;
    inFlight.current=true;setBusy(payload.action);setError('');
    const serialized=JSON.stringify({...payload,revision:snapshot.revision});
    if(retry.current?.serialized!==serialized)retry.current={serialized,id:crypto.randomUUID()};
    try {
      const result=await api<State>(base+'/turn',{method:'POST',body:JSON.stringify({...payload,revision:snapshot.revision,request_id:retry.current.id})});
      setState(result);retry.current=null;
      if(payload.action==='message')setText('');
      if(payload.action==='prepare')setShowPdf(true);
      await onChanged().catch(()=>{});
      return true;
    }catch(e){setError(e instanceof Error?e.message:'La demande n’a pas abouti.');return false;}
    finally{inFlight.current=false;setBusy('');}
  }
  async function upload(selected:File|null) {
    if(!selected||!state||inFlight.current)return;
    inFlight.current=true;setBusy('upload');setError('');
    try {
      const data=new FormData();data.append('file',selected);data.append('revision',String(state.revision));data.append('request_id',crypto.randomUUID());
      const result=await api<State>(base+'/cin',{method:'POST',body:data});
      setState(result);await onChanged().catch(()=>{});
    }catch(e){setError(e instanceof Error?e.message:'La CIN n’a pas pu être jointe.');}
    finally{inFlight.current=false;setBusy('');if(file.current)file.current.value='';}
  }
  async function submit(){
    if(!state||inFlight.current)return;inFlight.current=true;setBusy('submit');setError('');
    try{await api(base+'/submit',{method:'POST',body:JSON.stringify({revision:state.revision,signature:state.report.signature})});await reload();await onChanged();}catch(e){setError(e instanceof Error?e.message:'Transmission impossible.');}finally{inFlight.current=false;setBusy('');}
  }
  if(!state)return <section className="panel rne-loading">{error?<><p role="alert">{error}</p><button className="btn secondary" onClick={reload}>Réessayer</button></>:<><LoaderCircle className="spin"/><p>Ouverture de votre déclaration…</p></>}</section>;
  const disabled=!!busy||state.locked;
  const complete=state.modification==='seat_address'&&!!state.cin_document_id&&Object.keys(state.labels).every(k=>state.values[k]&&!state.field_errors[k]);
  const confirmed=state.blockers.length===0;
  const hasPdf=state.pdf_revision===state.revision&&confirmed;
  const fieldDirty=(key:string,value:boolean)=>setDirty(old=>value?Array.from(new Set([...old,key])):old.filter(k=>k!==key));
  return <>
    <div className="page-heading"><div><div className="eyebrow">DÉCLARATION RNE F005</div><h1>Votre déclaration, pas à pas.</h1><p>Expliquez votre changement. Nous préparons le formulaire avec vous.</p></div><a className="btn secondary" href="/api/rne/template" target="_blank" rel="noreferrer"><FileText size={17}/>Voir le formulaire original</a></div>
    {error&&<div className="error-banner" role="alert"><CircleAlert size={18}/><span>{error}</span><button className="btn small secondary" onClick={reload} disabled={!!busy}>Actualiser</button></div>}
    {state.locked&&<p className="soft-note">Ce dossier est en revue. Les informations sont consultables, mais leur modification est suspendue.</p>}
    {state.sample&&<div className="demo-banner"><Sparkles size={17}/><span><strong>Démonstration préanalysée</strong> · Pièces et échange initial fictifs. Les contrôles et les actions sont exécutés par l’application.</span></div>}
    <EvidenceOverview report={state.report}/>
    <div className="rne-tabs" role="tablist" aria-label="Parcours de préparation"><button role="tab" aria-selected={tab==='conversation'} className={tab==='conversation'?'selected':''} onClick={()=>setTab('conversation')}>1. Préciser ma demande</button><button role="tab" aria-selected={tab==='proofs'} className={tab==='proofs'?'selected':''} onClick={()=>setTab('proofs')}>2. Vérifier les preuves{state.report.counts.cross_attention>0&&<span>{state.report.counts.cross_attention}</span>}</button></div>
    <div className="rne-layout">
      {tab==='proofs'&&<EvidenceReportView report={state.report} caseId={caseId} disabled={disabled||!!dirty.length} onRetain={documentId=>turn({action:'use_evidence',key:'company_id',document_id:documentId})}/>}
      {tab==='conversation'&&<section className="panel rne-chat" aria-label="Conversation de préparation">
        <div className="rne-chat-heading"><span className="assistant-icon"><Sparkles size={20}/></span><div><strong>Votre assistant de préparation</strong><small>{stages[state.stage]}</small></div><span className="badge neutral">F005 · v1.1</span></div>
        <div className="rne-messages" ref={history} role="log" aria-live="polite" aria-relevant="additions">
          {state.messages.map(m=><article key={m.id} className={'rne-message '+m.role}><small>{m.role==='user'?'Vous':'Assistant'}</small><p dir="auto">{m.text}</p>{m.source_ids.length>0&&<div className="rne-message-sources">{m.source_ids.map(id=>{const ref=state.references.find(r=>r.id===id);return ref?.url?<a key={id} href={ref.url+(ref.page?'#page='+ref.page:'')} target="_blank" rel="noreferrer"><BookOpen size={12}/>{ref.title}{ref.page?' · p. '+ref.page:''}</a>:ref?<span key={id}>{ref.title}</span>:null;})}</div>}</article>)}
          {state.stage==='out_of_scope'&&<div className="soft-note">La génération est suspendue pour cette demande. Le parcours disponible concerne uniquement l’adresse du siège social.</div>}
          {(!state.modification||state.stage==='out_of_scope')&&<div className="rne-choices" aria-label="Préciser la modification">{choices.filter(c=>!state.candidates.length||state.candidates.includes(c.id)).map(c=><button key={c.id} className="prompt-chip" disabled={disabled} onClick={()=>turn({action:'select_modification',modification:c.id})}>{c.label}<ArrowUpRight size={14}/></button>)}</div>}
          {busy&&<ProcessingSteps action={busy}/>}
        </div>
        <div className="rne-composer">
          {state.cin_document_id&&<div className="rne-attached"><FileText size={16}/><a href={`/api/cases/${caseId}/documents/${state.cin_document_id}/file`} target="_blank" rel="noreferrer">{state.cin_document_name}</a><span>{state.cin_status==='extracted'?'Lue · à vérifier':state.cin_status==='needs_review'?'À relire':'Jointe'}</span></div>}
          {!state.ai_configured&&<p className="soft-note">La conversation IA est indisponible. Vous pouvez remplir et confirmer les rubriques à droite.</p>}
          <form onSubmit={e=>{e.preventDefault();turn({action:'message',message:text});}}><label className="sr-only" htmlFor="rne-message">Votre message</label><textarea id="rne-message" rows={2} value={text} maxLength={3000} disabled={disabled||!state.ai_configured} onChange={e=>setText(e.target.value)} placeholder="Expliquez votre situation, posez une question…" onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();if(text.trim())turn({action:'message',message:text});}}}/><button className="rne-send" type="submit" aria-label="Envoyer le message" disabled={disabled||!state.ai_configured||!text.trim()}><Send size={18}/></button></form>
          <div className="rne-composer-tools"><input ref={file} type="file" accept=".pdf,.png,.jpg,.jpeg" className="sr-only" aria-label="Joindre la CIN du déclarant" onChange={e=>upload(e.target.files?.[0]||null)}/><button className="text-link" disabled={disabled} onClick={()=>file.current?.click()}><Paperclip size={16}/>{state.cin_document_id?'Remplacer la CIN':'Ajouter la CIN'}</button>{state.cin_document_id&&!(state.sample&&state.cin_document_id==='cin')&&<button className="text-link" disabled={disabled||!state.ai_configured} onClick={()=>turn({action:'extract_cin'})}><Sparkles size={15}/>{state.cin_status==='uploaded'?'Lire la CIN':'Relire la CIN'}</button>}<small>PDF ou image · 12 Mo · 2 pages</small></div>
        </div>
      </section>}
      <aside className="panel rne-summary" aria-label="Récapitulatif du formulaire">
        <div className="panel-heading"><div><span className="eyebrow">VOTRE FORMULAIRE PREND FORME</span><h2>Les informations à retenir</h2></div></div>
        <div className="rne-summary-body">
          <label className="form-label">Nature de la modification<select value={state.modification||''} disabled={disabled} onChange={e=>{if(e.target.value)turn({action:'select_modification',modification:e.target.value});}}><option value="">À préciser ensemble</option>{choices.map(c=><option key={c.id} value={c.id}>{c.label}</option>)}</select></label>
          {state.reason&&<p className="rne-reason"><BookOpen size={13}/>{state.reason}</p>}
          {Object.entries(state.labels).map(([key,label])=><FieldRow key={key+':'+(state.values[key]?.value||'')} field={key} label={label} fact={state.values[key]} issue={state.field_errors[key]} caseId={caseId} disabled={disabled||(key.startsWith('representative_')&&state.values.same_person?.value==='yes')} linked={key.startsWith('representative_')&&state.values.same_person?.value==='yes'} save={async value=>{const ok=await turn({action:'edit',key,value});if(ok)fieldDirty(key,false);return ok;}} onDirty={value=>fieldDirty(key,value)}/>)}
        </div>
        <div className="rne-summary-footer">
          {!!dirty.length&&<p className="soft-note">Enregistrez ou annulez vos modifications avant de confirmer.</p>}
          {!complete&&<p className="rne-missing">Complétez les rubriques, joignez la CIN et précisez la modification pour accéder à la confirmation.</p>}
          {!confirmed?<button className="btn primary full" disabled={disabled||!complete||!!dirty.length} onClick={()=>turn({action:'confirm'})}><Check size={17}/>J’ai relu et je confirme</button>:<button className="btn primary full" disabled={disabled||!!dirty.length} onClick={()=>turn({action:'prepare'})}><FileText size={17}/>{hasPdf?'Préparer à nouveau':'Préparer mon F005'}</button>}
          {hasPdf&&<div className="rne-downloads"><button className="btn secondary full" onClick={()=>setShowPdf(!showPdf)}><FileText size={16}/>{showPdf?'Masquer l’aperçu':'Relire le PDF'}</button><a className="btn secondary full" href={`/api/cases/${caseId}/rne/pdf`} download={`${caseId}-RNE-F005.pdf`}><ArrowDownToLine size={16}/>Télécharger le PDF</a></div>}
          {hasPdf&&!state.locked&&<button className="btn primary full rne-submit" disabled={disabled||!!dirty.length||state.report.counts.cross_attention>0||state.report.counts.attention>0} onClick={submit}><Send size={16}/>Transmettre à la revue locale</button>}
          {state.institution.submission_id&&<Link className="btn secondary full rne-submit" href="/institution">Suivre la revue · {state.institution.submission_id}</Link>}
          <small>La date et la signature seront complétées par le déclarant. Aucun dépôt officiel.</small>
        </div>
      </aside>
    </div>
    {showPdf&&hasPdf&&<section className="panel rne-preview"><div className="panel-heading"><h2>Votre formulaire préparé</h2><a className="text-link" href={`/api/cases/${caseId}/rne/pdf`} target="_blank" rel="noreferrer">Ouvrir dans un onglet<ArrowUpRight size={15}/></a></div><iframe key={state.pdf_revision} title="Aperçu du formulaire RNE F005 rempli" src={`/api/cases/${caseId}/rne/pdf`}/></section>}
    <details className="panel rne-references"><summary><BookOpen size={18}/>Ce qui guide l’assistant<ChevronDown size={16}/></summary><div>{state.references.map(r=><article key={r.id}><strong>{r.title}{r.page?' · page '+r.page:''}</strong><p>{r.text}</p>{r.url&&<a className="text-link" href={r.url+(r.page?'#page='+r.page:'')} target="_blank" rel="noreferrer">Consulter la référence<ArrowUpRight size={13}/></a>}</article>)}</div></details>
  </>;
}

const STEP_CONFIGS: Record<string, {steps: string[]; delays: number[]}> = {
  extract_cin: {steps: ['Lecture du document', 'Recherche des informations', 'Vérification des passages'], delays: [0, 2500, 6000]},
  prepare: {steps: ['Lecture des pièces confirmées', 'Vérification de concordance', 'Remplissage du formulaire original'], delays: [0, 1500, 4000]},
  message: {steps: ["L'assistant analyse votre demande", 'Consultation des références', 'Préparation de la réponse'], delays: [0, 2000, 5000]},
};

function ProcessingSteps({action}: {action: string}) {
  const config = STEP_CONFIGS[action] || {steps: ['Traitement en cours…'], delays: [0]};
  const [active, setActive] = useState(0);
  useEffect(() => {
    const timers = config.delays.slice(1).map((delay, i) =>
      setTimeout(() => setActive(i + 1), delay)
    );
    return () => timers.forEach(clearTimeout);
  }, [action]);
  return (
    <div className="processing-steps" role="status" aria-live="polite">
      {config.steps.map((label, i) => (
        <div key={label} className={'processing-step' + (i < active ? ' done' : i === active ? ' active' : '')}>
          <span className="processing-step-indicator">
            {i < active ? <Check size={12}/> : i === active ? <LoaderCircle className="spin" size={12}/> : <span className="processing-step-dot"/>}
          </span>
          <span>{label}</span>
        </div>
      ))}
    </div>
  );
}

function FieldRow({field,label,fact,issue,caseId,disabled,linked,save,onDirty}:{field:string;label:string;fact?:Value;issue?:string;caseId:string;disabled:boolean;linked:boolean;save:(value:string)=>Promise<boolean>;onDirty:(dirty:boolean)=>void}) {
  const [editing,setEditing]=useState(false);
  const [value,setValue]=useState(fact?.value||'');
  const display=field==='same_person'?fact?.value==='yes'?'Oui':fact?.value==='no'?'Non':'':fact?.value;
  return <div className="rne-field"><div className="rne-field-title"><strong>{label}</strong>{fact&&<span className={'badge '+(fact.confirmed?'green':'neutral')}>{fact.confirmed?'Confirmé':'À relire'}</span>}</div>
    {editing?<form onSubmit={async e=>{e.preventDefault();if(await save(value))setEditing(false);}}><label className="sr-only" htmlFor={'rne-'+field}>{label}</label>{field==='same_person'?<select id={'rne-'+field} value={value} onChange={e=>{setValue(e.target.value);onDirty(true);}} required disabled={disabled}><option value="">Choisir</option><option value="yes">Oui, la même personne</option><option value="no">Non, deux personnes différentes</option></select>:<input id={'rne-'+field} dir="auto" required maxLength={180} value={value} onChange={e=>{setValue(e.target.value);onDirty(true);}} type={field==='email'?'email':'text'} inputMode={field.endsWith('_id')?'text':field==='phone'?'tel':undefined} disabled={disabled}/>}<div className="rne-field-buttons"><button className="text-link" type="submit" disabled={disabled}>Enregistrer</button><button className="text-link" type="button" disabled={disabled} onClick={()=>{setEditing(false);setValue(fact?.value||'');onDirty(false);}}>Annuler</button></div></form>:<button className="rne-field-value" disabled={disabled} onClick={()=>{setEditing(true);onDirty(true);}}><span dir="auto">{display||'À compléter'}</span><Pencil size={13}/></button>}
    {linked&&<small>Identité reprise du déclarant, selon votre réponse.</small>}
    {issue&&<p className="assistant-error">{issue}</p>}
    {!!fact?.evidence.length&&<details className="rne-evidence"><summary>{fact.evidence.some(e=>e.origin==='document')?'Voir le passage source':'Information déclarée par vous'}</summary>{fact.evidence.map((e,i)=><div key={i}><blockquote dir="auto">{e.quote}</blockquote>{e.origin==='document'&&<a href={`/api/cases/${caseId}/documents/${e.reference_id}/file#page=${e.page||1}`} target="_blank" rel="noreferrer">Pièce source · page {e.page}<ArrowUpRight size={12}/></a>}</div>)}</details>}
  </div>;
}
