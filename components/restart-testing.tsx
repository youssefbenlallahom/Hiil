'use client';

import {useEffect, useRef, useState} from 'react';
import {LoaderCircle, RotateCcw, X} from 'lucide-react';
import {api} from '@/lib/types';

function leaveOldWorkspace(){
  try{for(const key of Object.keys(sessionStorage))if(key.startsWith('dossier-recovery:'))sessionStorage.removeItem(key);}catch{}
  window.dispatchEvent(new Event('dossier-testing-reset'));
  window.location.replace('/dossiers');
}

export default function RestartTesting(){
  const dialog=useRef<HTMLDialogElement>(null);
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  useEffect(()=>{const changed=(event:StorageEvent)=>{if(event.key==='dossier-testing-reset'&&event.newValue)leaveOldWorkspace();};window.addEventListener('storage',changed);return()=>window.removeEventListener('storage',changed);},[]);
  async function restart(){
    setBusy(true);setError('');
    try{
      await api('/testing/restart',{method:'POST',body:JSON.stringify({confirmation:'restart-testing'})});
      try{localStorage.setItem('dossier-testing-reset',String(Date.now()));}catch{}
      leaveOldWorkspace();
    }catch(e){setError(e instanceof Error?e.message:'Le redémarrage a échoué. Réessayez.');setBusy(false);}
  }
  return <><button className="nav-item restart-testing" onClick={()=>{setError('');dialog.current?.showModal();}}><RotateCcw size={18}/><span>Restart testing</span></button>
    <dialog ref={dialog} className="modal restart-dialog" aria-labelledby="restart-title" onCancel={e=>{if(busy)e.preventDefault();}}><div className="modal-heading"><RotateCcw size={25}/><button className="icon-btn" disabled={busy} aria-label="Fermer" onClick={()=>dialog.current?.close()}><X size={20}/></button></div><h2 id="restart-title">Recommencer les tests ?</h2><p>Cette action vide tous les dossiers de ce workspace : pièces importées, formulaires, conversations IA, confirmations et décisions de revue.</p><div className="soft-note">Les sources RNE restent disponibles. Une sauvegarde locale des données est conservée pour récupération.</div>{error&&<p className="error-banner" role="alert">{error}</p>}<footer><button className="btn secondary" disabled={busy} onClick={()=>dialog.current?.close()}>Annuler</button><button className="btn primary" disabled={busy} onClick={()=>void restart()}>{busy?<LoaderCircle size={16} className="spin"/>:<RotateCcw size={16}/>} {busy?'Redémarrage…':'Effacer les tests et recommencer'}</button></footer></dialog>
  </>;
}
