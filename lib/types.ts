import type {FormDraft, OcrCandidate} from './form-types';
export type Fact = {key:string;value:string;page:number;evidence:string};
export type Document = {id:string;name:string;filename:string;kind:string;status:string;method:string;text:string;pages:{page:number;text:string}[];fields:Fact[];content_type:string;sample:boolean;form_candidates?:OcrCandidate[];warnings?:string[]};
export type Issue = {key:string;label:string;type:string;resolved:boolean;confirmation:{value:string}|null;evidence:(Fact & {document_id:string;document_name:string})[]};
export type Case = {id:string;company:string;title:string;sample:boolean;status:string;documents:Document[];confirmations:Record<string,{value:string;at:string;actor:string}>;events:{id:string;label:string;actor:string;detail:string;at:string}[];checks:{issues:Issue[];open_count:number;field_count:number;pending_documents:string[];scope:string};can_submit:boolean;updated_at:string;form:Pick<FormDraft,'revision'|'has_pdf'|'ready'|'step'|'modifications'|'errors'>};
export type Source = {id:string;title:string;url:string;type:string;text:string;status?:string;retrieved_at?:string|null;checked_at?:string|null;hash?:string|null;page?:number;quote?:string;error?:string|null;provenance?:string;changed?:boolean};
export type Health = {ai_configured:boolean;ocr_configured:boolean;ocr_provider:string|null;mode:string;institutional_connection:boolean};
export type Answer = {text:string;message?:string;mode:string;sources:Source[];references?:Source[]};

export async function api<T>(url:string, options?:RequestInit):Promise<T> {

  const response = await fetch('/api'+url,{cache:'no-store',...options,headers:options?.body instanceof FormData ? options.headers : {'Content-Type':'application/json',...options?.headers}});
  if(!response.ok) {
    const body = await response.json().catch(()=>null);
    throw new Error(typeof body?.detail==='string'?body.detail:'La demande n’a pas abouti. Réessayez ou vérifiez le service de traitement.');
  }
  return response.json();
}

