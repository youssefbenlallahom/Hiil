export type Fact = {key:string; value:string; page:number; evidence:string};
export type Document = {id:string; name:string; filename:string; kind:string; status:string; method:string; text:string; pages:{page:number;text:string}[]; fields:Fact[]; content_type:string; sample:boolean};
export type Issue = {key:string; label:string; type:string; resolved:boolean; confirmation:{value:string}|null; evidence:(Fact & {document_id:string;document_name:string})[]};
export type Case = {id:string;company:string;title:string;sample:boolean;status:string;documents:Document[];confirmations:Record<string,{value:string;at:string;actor:string}>;events:{id:string;label:string;actor:string;detail:string;at:string}[];checks:{issues:Issue[];open_count:number;field_count:number;pending_documents:string[];scope:string};can_submit:boolean;updated_at:string};
export type Source = {id:string;title:string;url:string;type:string;text:string;checked_at:string};
export type Health = {ai_configured:boolean;ocr_configured:boolean;mode:string};

export type ConversationProgress = {
  scenario?: string;
  scenario_label?: string;
  total_fields: number;
  filled_fields: number;
  percentage: number;
};

export type Justification = {
  key: string;
  label: string;
  value: string;
  source: string;
};

export type ConversationResponse = {
  mode: 'llm' | 'guided' | 'unavailable';
  error_code: string | null;
  can_generate: boolean;
  reply: string;
  status: 'greeting' | 'clarifying' | 'gathering' | 'confirming' | 'filling' | 'done' | string;
  collected: Record<string, string>;
  progress: ConversationProgress;
  form_path: string | null;
  justifications: Justification[];
  history?: { role: 'user' | 'assistant'; text: string }[];
};

export async function api<T>(url:string, options?:RequestInit):Promise<T> {
  const response = await fetch('/api'+url, {cache:'no-store', ...options, headers: options?.body instanceof FormData ? options.headers : {'Content-Type':'application/json',...options?.headers}});
  if (!response.ok) {
    const body = await response.json().catch(()=>null);
    throw new Error(typeof body?.detail==='string' ? body.detail : 'La demande n’a pas abouti. Vérifiez que le backend est démarré.');
  }
  return response.json();
}
