'use client';

import {useEffect, useRef, useState, type ReactNode} from 'react';
import {ArrowUpRight, BookOpen, CheckCheck, LoaderCircle, Send, Sparkles} from 'lucide-react';
import {api, type Answer, type Case, type Health, type Source} from '@/lib/types';
import type {FormDraft, FormField} from '@/lib/form-types';

type Proposal = {id:string;question:string;text:string;state:string;revision:number;at:string;sources:Source[];
  modifications:{key:string;label:string;evidence:string;help:string}[];
  fields:{key:string;label:string;value:string;evidence:string}[]};

export default function JourneyChat({c,draft,health,next,flush,onCommit,onRefresh,children}:{
  c:Case;draft:FormDraft;health:Health|null;next?:FormField;flush:()=>Promise<FormDraft>;
  onCommit:(draft:FormDraft)=>Promise<void>;onRefresh:()=>Promise<void>;children:ReactNode;
}) {
  const [messages,setMessages]=useState<Proposal[]>([]),[value,setValue]=useState('');
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[loading,setLoading]=useState(true);
  const messageArea=useRef<HTMLDivElement>(null);
  const locked=['submitted','reviewed'].includes(c.status);
  useEffect(()=>{let active=true;api<Proposal[]>(`/cases/${c.id}/journey`).then(data=>{if(active)setMessages(data);}).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[c.id]);
  useEffect(()=>{if(messages.length&&messageArea.current)messageArea.current.scrollTo({top:messageArea.current.scrollHeight,behavior:'smooth'});},[messages,busy]);
  async function send(text=value){if(!text.trim()||busy)return;setBusy(true);setError('');try{
    await flush();
    const result=await api<Proposal>(`/cases/${c.id}/journey`,{method:'POST',body:JSON.stringify({message:text,active_field:next?.key})});
    setMessages(old=>[...old,result]);setValue('');
  }catch(e){setError(e instanceof Error?e.message:'Réponse indisponible.');}finally{setBusy(false);}}
  async function confirm(id:string){setBusy(true);setError('');try{
    const saved=await flush();
    const result=await api<{draft:FormDraft;messages:Proposal[]}>(`/cases/${c.id}/journey/${id}/confirm`,{method:'POST',body:JSON.stringify({revision:saved.revision})});
    setMessages(result.messages);await onCommit(result.draft);
  }catch(e){setError(e instanceof Error?e.message:'Confirmation indisponible.');}finally{setBusy(false);}}
  return <section className="live-conversation journey-conversation"><header><span className="live-eyebrow">Votre assistant de démarche</span><p><span className="journey-dot"/>{health?.ai_configured?'Comprendre · préparer · vérifier':'IA non connectée · saisie directe disponible'}</p></header>
    <div ref={messageArea} className="live-messages" aria-live="polite" aria-busy={busy}>
      <div className="live-bubble assistant"><span className="live-message-label"><Sparkles size={13}/>Dossier TN</span><p>Qu’est-ce qui change pour <strong>{c.company}</strong> ? Décrivez votre situation avec vos mots, ou joignez vos documents. Je vous proposerai les informations à reprendre, puis nous compléterons ce qui manque.</p></div>
      {!messages.length&&!loading&&<div className="journey-starters">{['Je déménage le siège social de mon entreprise.','Je change le dirigeant et le compte bancaire.','Quelles pièces pour un changement de siège ?'].map(text=><button key={text} disabled={busy||!health?.ai_configured} onClick={()=>void send(text)}>{text}<ArrowUpRight size={14}/></button>)}</div>}
      {loading&&<p className="journey-thinking">Ouverture de la conversation…</p>}
      {messages.map(m=><article key={m.id}><div className="live-bubble user" dir="auto">{m.question}</div><div className="live-bubble assistant"><span className="live-message-label"><Sparkles size={13}/>Assistant IA</span><p dir="auto">{m.text}</p>
        {(m.modifications.length>0||m.fields.length>0)&&<div className="journey-proposal"><span className="live-eyebrow">Proposition de mise à jour</span>{m.modifications.map(item=><div className="journey-proposal-row" key={item.key}><strong>{item.label}</strong><p>{item.help}</p><small>Votre demande : « {item.evidence} »</small></div>)}{m.fields.map(item=><div className="journey-proposal-row" key={item.key}><span>{item.label}</span><strong dir="auto">{item.value}</strong>{draft.fields[item.key]&&draft.fields[item.key]!==item.value&&m.state==='proposed'&&<small className="live-error">Remplace : {draft.fields[item.key]}</small>}<small>Votre message : « {item.evidence} »</small></div>)}
          {m.state==='confirmed'?<span className="journey-confirmed"><CheckCheck size={14}/>Appliqué à votre dossier</span>:m.revision!==draft.revision?<small>Le dossier a évolué. Décrivez à nouveau le changement pour actualiser cette proposition.</small>:<button className="live-primary" disabled={busy||locked} onClick={()=>void confirm(m.id)}>Confirmer et compléter le dossier</button>}
        </div>}
        {m.sources.map((s,i)=><details className="live-proof" key={s.id+i}><summary><BookOpen size={12}/>{s.title}{s.page?` · page ${s.page}`:''}</summary><blockquote>{s.quote}</blockquote><a href={s.url} target="_blank" rel="noreferrer">Ouvrir la référence <ArrowUpRight size={12}/></a></details>)}
      </div></article>)}
      {!locked&&draft.modifications.length>0&&<div className="journey-next-question"><span className="live-eyebrow">{next?'Ce qui manque encore':'Prêt pour votre relecture'}</span>{next?<><strong>{next.label}</strong><p>{next.help}</p><small>Vous pouvez répondre ici ou importer la pièce qui contient cette information.</small></>:<p>Les champs nécessaires sont renseignés. Vérifiez le dossier et ses pièces avant de préparer le PDF.</p>}</div>}
      <EvidenceConflicts c={c} onRefresh={onRefresh}/>
      {busy&&<div className="journey-thinking"><LoaderCircle size={16} className="spin"/>Lecture du contexte et préparation de la réponse…</div>}
      {error&&<div className="live-alert" role="alert">{error}</div>}
    </div>
    <footer className="live-composer">{children}<form onSubmit={e=>{e.preventDefault();void send();}}><label htmlFor="journey-message" className="sr-only">Votre message à l’assistant</label><textarea id="journey-message" value={value} onChange={e=>setValue(e.target.value)} maxLength={2000} rows={2} placeholder="Décrivez le changement, donnez une information ou posez une question…" disabled={busy||loading||!health?.ai_configured} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();void send();}}}/><button aria-label="Envoyer à l’assistant" disabled={busy||loading||!value.trim()||!health?.ai_configured}><Send size={17}/></button></form><small><BookOpen size={12}/>L’IA propose. Vous confirmez avant toute mise à jour.</small></footer>
  </section>;
}

function EvidenceConflicts({c,onRefresh}:{c:Case;onRefresh:()=>Promise<void>}) {
  const [busy,setBusy]=useState(''),[error,setError]=useState('');
  async function confirm(key:string,value:string){setBusy(key);setError('');try{await api(`/cases/${c.id}/confirm`,{method:'POST',body:JSON.stringify({key,value})});await onRefresh();}catch(e){setError(e instanceof Error?e.message:'Confirmation indisponible.');}finally{setBusy('');}}
  return <>{c.checks.issues.map(issue=><section className="journey-conflict" key={issue.key}><span className="live-eyebrow">{issue.resolved?'Écart confirmé':'Les pièces se contredisent'}</span><h3>{issue.label}</h3><p>{issue.resolved?'La valeur retenue est conservée avec les originaux.':'Quelle information faut-il retenir ? Comparez les passages avant de confirmer.'}</p>{issue.evidence.map((e,i)=><div key={i}><a href={`/api/cases/${c.id}/documents/${e.document_id}/file`} target="_blank" rel="noreferrer">{e.document_name} · p. {e.page}<ArrowUpRight size={12}/></a><blockquote dir="auto">{e.evidence}</blockquote>{!['submitted','reviewed'].includes(c.status)&&<button disabled={!!busy} className="live-secondary" onClick={()=>void confirm(issue.key,e.value)}>{issue.confirmation?.value===e.value?'Valeur retenue':'Retenir cette valeur'} : {e.value}</button>}</div>)}</section>)}{error&&<p role="alert" className="live-error">{error}</p>}</>;
}

export function ReviewBrief({c}:{c:Case}) {
  const [answer,setAnswer]=useState<Answer|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [snapshot,setSnapshot]=useState('');
  async function generate(){setBusy(true);setError('');try{const result=await api<Answer>(`/cases/${c.id}/review-brief`,{method:'POST'});setAnswer(result);setSnapshot(c.updated_at);}catch(e){setError(e instanceof Error?e.message:'Synthèse indisponible.');}finally{setBusy(false);}}
  return <section className="journey-review-brief"><span className="live-eyebrow"><Sparkles size={13}/>Pré-analyse IA</span><h3>Les points à examiner.</h3><p>Une synthèse des pièces avec les passages qui l’étayent, pour préparer votre revue.</p><button className="live-secondary" disabled={busy} onClick={()=>void generate()}>{busy?<LoaderCircle size={15} className="spin"/>:<Sparkles size={15}/>} {busy?'Analyse des pièces…':answer?'Actualiser la synthèse':'Préparer la synthèse IA'}</button>{error&&<p className="live-error" role="alert">{error}</p>}{answer&&<div className="journey-brief-result">{snapshot!==c.updated_at&&<small className="live-error">Le dossier a changé depuis cette synthèse. Actualisez-la.</small>}<p dir="auto">{answer.text||answer.message}</p>{answer.sources.map((s,i)=><details className="live-proof" key={s.id+i}><summary><BookOpen size={12}/>{s.title} · p. {s.page}</summary><blockquote>{s.quote}</blockquote><a href={s.url} target="_blank" rel="noreferrer">Consulter la pièce <ArrowUpRight size={12}/></a></details>)}<small>Analyse à vérifier par l’agent. Aucune décision automatique.</small></div>}</section>;
}
