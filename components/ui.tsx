import Link from 'next/link';
import {ArrowUpRight, Check, CircleAlert, FileText, LoaderCircle} from 'lucide-react';
import type {ReactNode} from 'react';
export function Logo(){return <Link href="/" className="brand" aria-label="Dossier TN, accueil"><span className="brand-mark"><span/><span/><span/></span><strong>Dossier<span>TN</span></strong></Link>;}
export const date=(value?:string|null)=>value?new Intl.DateTimeFormat('fr-TN',{day:'numeric',month:'short',year:'numeric'}).format(new Date(value)):'—';
const labels:Record<string,string>={draft:'En préparation',submitted:'En revue',correction_requested:'À corriger',reviewed:'Revue terminée'};
export function Status({status}:{status:string}){return <span className={'status '+status}><i/>{labels[status]||status}</span>;}
export function Message({children,error=false}:{children:ReactNode;error?:boolean}){return <div className={'message '+(error?'error':'')} role={error?'alert':'status'}>{error?<CircleAlert size={18}/>:<Check size={18}/>}<span>{children}</span></div>;}
export function Loading({text='Chargement de votre espace…'}:{text?:string}){return <div className="loading" role="status"><LoaderCircle size={22} className="spin"/>{text}</div>;}
export function Empty({title,children,action}:{title:string;children:ReactNode;action?:ReactNode}){return <div className="empty"><span className="empty-icon"><FileText size={27}/></span><h2>{title}</h2><p>{children}</p>{action}</div>;}
export function External({href,children}:{href:string;children:ReactNode}){return <a className="text-link" href={href} target="_blank" rel="noreferrer">{children}<ArrowUpRight size={14}/></a>;}

