'use client';

import {useState} from 'react';
import {CircleAlert, Send} from 'lucide-react';
import {api, Case} from '@/lib/types';

export default function CorrectionNotice({c,onUpdate}:{c:Case;onUpdate:(c:Case)=>void}) {
  const [note,setNote]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  if(!c.correction||c.status!=='correction_requested')return null;
  async function respond(){
    if(busy||!note.trim())return;
    setBusy(true);setError('');
    try{onUpdate(await api<Case>(`/cases/${c.id}/correction-response`,{method:'POST',body:JSON.stringify({note})}));setNote('');}
    catch(e){setError(e instanceof Error?e.message:'Réponse non enregistrée.');}
    finally{setBusy(false);}
  }
  return <section className="correction-notice" aria-label="Correction demandée par l’agent"><div className="section-title"><h3><CircleAlert size={18}/>L’agent demande une correction</h3><span className="badge amber">{c.correction.pending?'Réponse attendue':'Réponse enregistrée'}</span></div><blockquote>{c.correction.note}</blockquote>
    {c.correction.pending?<form onSubmit={e=>{e.preventDefault();respond();}}><label className="form-label">Votre réponse à l’agent<textarea required maxLength={2000} rows={2} value={note} onChange={e=>setNote(e.target.value)} placeholder="Après vos modifications, décrivez ce qui a été corrigé ou précisez votre situation…"/></label>{error&&<p role="alert" className="assistant-error">{error}</p>}<button className="btn secondary" disabled={busy||!note.trim()}><Send size={15}/>{busy?'Enregistrement…':'Enregistrer la réponse'}</button></form>:<p><strong>Votre réponse :</strong> {c.correction.response}<br/>Vous pouvez retransmettre depuis la préparation.</p>}
  </section>;
}
