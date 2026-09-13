'use client';
import {useEffect,useRef,useState} from 'react';
import {ArrowUpRight,BookOpen,LoaderCircle,Send,X} from 'lucide-react';
import {api,type Answer,type Health} from '@/lib/types';
import {date} from './ui';

export default function Advisor({caseId,field,health,onClose}:{caseId:string;field?:string;health:Health|null;onClose:()=>void}){
  const [question,setQuestion]=useState('');
  const [messages,setMessages]=useState<{question:string;answer:Answer}[]>([]);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const input=useRef<HTMLInputElement>(null);
  const end=useRef<HTMLDivElement>(null);
  useEffect(()=>{input.current?.focus();},[]);
  useEffect(()=>{end.current?.scrollIntoView({block:'nearest'});},[messages]);
  async function ask(){
    const text=question.trim(); if(!text||busy)return;
    setBusy(true);setError('');
    try{
      const answer=await api<Answer>('/cases/'+caseId+'/assistant',{method:'POST',body:JSON.stringify({question:text,field})});
      setMessages(old=>[...old,{question:text,answer}]);setQuestion('');
    }catch(e){setError(e instanceof Error?e.message:'La réponse est indisponible. Réessayez.');}
    finally{setBusy(false);}
  }
  return <section className="advisor" aria-label="Aide avec les documents">
    <header><span className="section-kicker">Aide contextuelle</span><button className="icon-button" onClick={onClose} aria-label="Fermer l’aide"><X size={19}/></button></header>
    <h2>Une réponse, ses références.</h2>
    <p className="muted">{health?.ai_configured?'L’aide s’appuie sur votre déclaration et les passages disponibles.':'L’assistance IA n’est pas configurée. Les explications des champs restent accessibles.'}</p>
    <div className="advisor-history" aria-live="polite">
      {messages.length===0&&<div className="advisor-empty"><BookOpen size={26}/><p>Posez une question sur un champ, une pièce ou votre prochaine étape.</p></div>}
      {messages.map((m,i)=><article key={i} className="exchange"><p className="question" dir="auto">{m.question}</p><p dir="auto">{m.answer.text||m.answer.message}</p>{m.answer.sources.map((s,j)=><details className="citation" key={s.id+j}><summary><BookOpen size={14}/>{s.title} · page {s.page}</summary><blockquote dir="auto">{s.quote}</blockquote><a href={s.url} target="_blank" rel="noreferrer">Ouvrir la référence <ArrowUpRight size={13}/></a>{s.retrieved_at&&<small>Copie récupérée le {date(s.retrieved_at)}</small>}</details>)}</article>)}
      {busy&&<p className="muted"><LoaderCircle size={15} className="spin"/> Recherche et vérification des passages…</p>}<div ref={end}/>
    </div>
    {error&&<p role="alert" className="field-error">{error}</p>}
    <form onSubmit={e=>{e.preventDefault();void ask();}}><label htmlFor="advisor-question" className="sr-only">Votre question</label><input ref={input} id="advisor-question" name="question" value={question} onChange={e=>setQuestion(e.target.value)} maxLength={2000} placeholder="Votre question…" disabled={busy||!health?.ai_configured}/><button className="icon-button" disabled={busy||!question.trim()||!health?.ai_configured} aria-label="Envoyer la question"><Send size={18}/></button></form>
  </section>;
}

