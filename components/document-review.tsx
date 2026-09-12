'use client';

import {useState} from 'react';
import {Check, Plus, Trash2, LoaderCircle} from 'lucide-react';
import {api, Case, Document, Fact} from '@/lib/types';

const labels:Record<string,string> = {company_name:'Dénomination',company_id:'Identifiant',current_address:'Adresse actuelle',new_address:'Nouvelle adresse',representative:'Représentant',decision_date:'Date de décision'};

export default function DocumentReview({c,document,locked,onSave}:{c:Case;document:Document;locked:boolean;onSave:(c:Case)=>void}) {
  const [fields,setFields]=useState<Fact[]>(document.fields);
  const [kind,setKind]=useState(document.kind);
  const [saving,setSaving]=useState(false);
  const [error,setError]=useState('');
  const [saved,setSaved]=useState(false);
  const change=(index:number,patch:Partial<Fact>)=>{setSaved(false);setFields(old=>old.map((f,i)=>i===index?{...f,...patch}:f));};
  async function save(){
    if(saving||locked)return;
    setSaving(true);setError('');setSaved(false);
    try{onSave(await api<Case>(`/cases/${c.id}/documents/${document.id}/review`,{method:'POST',body:JSON.stringify({kind,fields})}));setSaved(true);}
    catch(e){setError(e instanceof Error?e.message:'Impossible d’enregistrer la vérification.');}
    finally{setSaving(false);}
  }
  return <form className="manual-review" onSubmit={e=>{e.preventDefault();save();}}>
    <div className="section-title"><h3>Vérifier les informations de cette pièce</h3><span className="badge neutral">Saisie manuelle</span></div>
    <p>Recopiez les valeurs et leur passage source. Une page scannée doit être vérifiée dans l’original. Cette saisie est enregistrée comme une vérification humaine.</p>
    <label className="form-label">Type de pièce<select value={kind} disabled={locked||saving} onChange={e=>{setKind(e.target.value);setSaved(false);}}><option value="declaration">Déclaration de modification</option><option value="decision">Décision de transfert</option><option value="registry">Extrait de registre</option><option value="other">Autre pièce</option></select></label>
    {fields.map((field,index)=><fieldset className="field-editor" key={index} disabled={locked||saving}>
      <legend>Information {index+1}</legend>
      <div className="field-editor-grid">
        <label className="form-label">Champ<select value={field.key} onChange={e=>change(index,{key:e.target.value})}>{Object.entries(labels).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
        <label className="form-label">Valeur<input required maxLength={500} value={field.value} dir="auto" onChange={e=>change(index,{value:e.target.value})}/></label>
        <label className="form-label">Page<select value={field.page} onChange={e=>change(index,{page:Number(e.target.value)})}>{document.pages.map(p=><option key={p.page} value={p.page}>Page {p.page}</option>)}</select></label>
      </div>
      <label className="form-label">Passage source<textarea required maxLength={4000} rows={2} value={field.evidence} dir="auto" placeholder="Recopiez le passage qui contient cette valeur…" onChange={e=>change(index,{evidence:e.target.value})}/></label>
      <button type="button" className="text-link" onClick={()=>{setFields(old=>old.filter((_,i)=>i!==index));setSaved(false);}}><Trash2 size={14}/>Retirer ce champ</button>
    </fieldset>)}
    {!fields.length&&<div className="soft-note">Aucun champ renseigné. Vous pouvez ajouter les informations utiles ou marquer la pièce comme relue sans champ pertinent.</div>}
    {error&&<div className="error-banner" role="alert">{error}</div>}
    {saved&&<p className="save-success" role="status"><Check size={16}/>Vérification enregistrée. Consultez les points à confirmer dans le dossier.</p>}
    <div className="editor-actions"><button type="button" className="btn secondary" disabled={locked||saving||fields.length>=30} onClick={()=>{setFields(old=>[...old,{key:'company_name',value:'',page:1,evidence:''}]);setSaved(false);}}><Plus size={16}/>Ajouter un champ</button><button className="btn primary" disabled={locked||saving}>{saving?<LoaderCircle className="spin" size={16}/>:<Check size={16}/>}Enregistrer la vérification</button></div>
    <small>Une nouvelle vérification invalide les confirmations précédentes du dossier. L’original et l’historique des champs sont conservés.</small>
  </form>;
}
