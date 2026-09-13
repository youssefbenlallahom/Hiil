export type FormField = {key:string;label:string;arabic:string;step:number;required:boolean;max_length:number;help:string;where:string;example:string;tip:string;source:string;input_type:string;visible_when?:string[];required_when?:string[];pattern?:string};
export type Modification = {key:string;label:string;arabic:string;help:string;group:string;source:string};
export type FormCatalog = {version:string;fields:FormField[];modifications:Modification[];guidance:Record<string,string>;sources:Record<string,{title:string;url:string;detail:string}>};
export type OcrCandidate = {key:string;value:string;evidence:string;page:number;confidence?:number|null;polygons?:number[][]};
export type OcrBatch = {id:string;document_id?:string;name:string;kind:string;mime:string;method:string;candidates:OcrCandidate[];pages:{page:number;text:string}[];warnings?:string[];cached?:boolean;duration_ms?:number};
export type Provenance = {document_id:string;page:number;evidence:string;value:string};
export type FormDraft = {revision:number;fields:Record<string,string>;modifications:string[];same_person:boolean;step:number;generated_revision:number|null;imports:OcrBatch[];errors:Record<string,string>;ready:boolean;has_pdf:boolean;provenance:Record<string,Provenance>;locked?:boolean};

