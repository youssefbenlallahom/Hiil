'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import {useRouter} from 'next/navigation';
import {api} from './types';
import type {FormDraft} from './form-types';

export const emptyDraft:FormDraft={revision:0,fields:{},modifications:[],same_person:false,step:0,generated_revision:null,imports:[],errors:{},ready:false,has_pdf:false,provenance:{}};

export function useFormDraft(caseId:string){
  const router=useRouter();
  const endpoint='/cases/'+caseId+'/f005';
  const key='dossier-recovery:'+caseId;
  const [draft,setDraft]=useState<FormDraft>(emptyDraft);
  const [loading,setLoading]=useState(true);
  const [status,setStatus]=useState<'saved'|'saving'|'dirty'|'error'>('saved');
  const [error,setError]=useState('');
  const [recovery,setRecovery]=useState<FormDraft|null>(null);
  const latest=useRef(emptyDraft),revision=useRef(0),epoch=useRef(0);
  const timer=useRef<ReturnType<typeof setTimeout>|null>(null);
  const queue=useRef<Promise<void>>(Promise.resolve());
  const dirty=useRef(false),lastError=useRef('');
  const active=useRef(true);
  const commit=useCallback((next:FormDraft)=>{latest.current=next;revision.current=next.revision;setDraft(next);},[]);
  useEffect(()=>{
    active.current=true;
    api<FormDraft>(endpoint).then(d=>{
      if(!active.current)return;
      commit(d);
      try{const saved=sessionStorage.getItem(key);if(saved){const candidate=JSON.parse(saved) as FormDraft;if(candidate.fields&&candidate.revision===d.revision&&!d.locked)setRecovery(candidate);else sessionStorage.removeItem(key);}}catch{}
    }).catch(e=>{if(active.current)setError(e.message);}).finally(()=>{if(active.current)setLoading(false);});
    return()=>{active.current=false;if(timer.current)clearTimeout(timer.current);};
  },[endpoint,key,commit]);
  const save=useCallback(()=>{
    const target=latest.current,version=epoch.current;
    setStatus('saving');lastError.current='';
    const operation=queue.current.then(async()=>{
      const result=await api<FormDraft>(endpoint,{method:'POST',body:JSON.stringify({revision:revision.current,fields:target.fields,modifications:target.modifications,same_person:target.same_person,step:target.step,provenance:target.provenance})});
      revision.current=result.revision;
      if(version===epoch.current){latest.current=result;dirty.current=false;sessionStorage.removeItem(key);if(active.current){setDraft(result);setStatus('saved');setError('');}}
    }).catch(e=>{lastError.current=e.message;if(active.current){setStatus('error');setError(e.message);}throw e;});
    queue.current=operation.catch(()=>{});
    return operation;
  },[endpoint,key]);
  const flush=useCallback(async()=>{
    if(timer.current){clearTimeout(timer.current);timer.current=null;await save();}
    else {await queue.current;if(dirty.current)await save();}
    if(lastError.current)throw new Error(lastError.current);
    return latest.current;
  },[save]);
  const change=useCallback((patch:Partial<FormDraft>)=>{
    const dataChange=!!(patch.fields||patch.modifications||patch.same_person!==undefined);
    const next={...latest.current,...patch,...(dataChange?{has_pdf:false,generated_revision:null}:{})};
    if(next.same_person){next.fields={...next.fields,nom_declarant:next.fields.representant_legal||'',identite_declarant:next.fields.identite_representant||''};}
    epoch.current++;dirty.current=true;latest.current=next;setDraft(next);setStatus('dirty');setError('');
    try{sessionStorage.setItem(key,JSON.stringify({...next,revision:revision.current}));}catch{}
    if(timer.current)clearTimeout(timer.current);
    timer.current=setTimeout(()=>{timer.current=null;void save().catch(()=>{});},500);
  },[key,save]);
  useEffect(()=>{
    const reset=()=>{dirty.current=false;active.current=false;if(timer.current){clearTimeout(timer.current);timer.current=null;}};
    window.addEventListener('dossier-testing-reset',reset);
    return()=>window.removeEventListener('dossier-testing-reset',reset);
  },[]);
  useEffect(()=>{
    const unload=(e:BeforeUnloadEvent)=>{if(dirty.current){e.preventDefault();e.returnValue='';}};
    const navigate=(e:MouseEvent)=>{
      const anchor=(e.target as HTMLElement).closest?.('a');
      if(!dirty.current||!anchor||anchor.target==='_blank'||anchor.hasAttribute('download')||e.ctrlKey||e.metaKey||e.shiftKey||e.button!==0)return;
      const url=new URL(anchor.href,window.location.href);if(url.origin!==window.location.origin||url.pathname.startsWith('/api/'))return;
      e.preventDefault();e.stopPropagation();void flush().then(()=>router.push(url.pathname+url.search)).catch(()=>{});
    };
    window.addEventListener('beforeunload',unload);document.addEventListener('click',navigate,true);
    return()=>{window.removeEventListener('beforeunload',unload);document.removeEventListener('click',navigate,true);};
  },[flush,router]);
  function restore(){if(recovery){change(recovery);setRecovery(null);}}
  function discard(){sessionStorage.removeItem(key);setRecovery(null);}
  return {draft,loading,status,error,setError,change,flush,commit,recovery,restore,discard};
}
