'use client';

import {useEffect,useState} from 'react';
import {CheckCheck, CircleAlert, Clock3, FileText, ShieldCheck} from 'lucide-react';

type VerifyData = {
  submission_id:string; company:string; status:string; submitted_at:string;
  revision:number; signature:string; engine_version:string;
  counts:{missing:number;attention:number;review:number;confirmed:number;documented:number;declared:number;cross_attention:number};
  scope:string; decision:{action:string;note:string;at:string}|null; mode:string;
};

const statusLabels:Record<string,string> = {submitted:'En revue',reviewed:'Revue terminée',correction_requested:'Correction demandée'};

export default function VerifyPage({params}:{params:Promise<{submission_id:string}>}) {
  const [data,setData] = useState<VerifyData|null>(null);
  const [error,setError] = useState('');
  const [id,setId] = useState('');

  useEffect(() => {
    params.then(p => {
      setId(p.submission_id);
      fetch(`/api/institution/verify/${p.submission_id}`)
        .then(r => r.ok ? r.json() : Promise.reject(new Error(r.status === 404 ? 'Déclaration introuvable.' : 'Erreur de vérification.')))
        .then(d => setData(d))
        .catch(e => setError(e.message));
    });
  }, [params]);

  return (
    <div className="verify-page">
      <div className="verify-card">
        <div className="verify-header">
          <FileText size={32}/>
          <h1>Dossier<span className="brand-tn">TN</span></h1>
        </div>
        <p className="verify-subtitle">Fiche de suivi de préparation</p>

        {error ? (
          <div className="verify-error"><CircleAlert size={20}/><span>{error}</span></div>
        ) : !data ? (
          <p className="verify-loading">Vérification en cours…</p>
        ) : (
          <>
            <div className="verify-id">
              <ShieldCheck size={20}/>
              <span>{data.submission_id}</span>
            </div>

            <dl className="verify-facts">
              <div>
                <dt>Entreprise</dt>
                <dd>{data.company}</dd>
              </div>
              <div>
                <dt>Statut</dt>
                <dd>
                  <span className={'verify-status ' + data.status}>
                    <span className="status-dot"/>
                    {statusLabels[data.status] || data.status}
                  </span>
                </dd>
              </div>
              <div>
                <dt>Transmise le</dt>
                <dd>{new Date(data.submitted_at).toLocaleString('fr-TN')}</dd>
              </div>
              <div>
                <dt>Version</dt>
                <dd>Révision {data.revision}</dd>
              </div>
            </dl>

            <div className="verify-metrics">
              <div><CheckCheck size={16}/><strong>{data.counts.confirmed}</strong><span>confirmés</span></div>
              <div><FileText size={16}/><strong>{data.counts.documented}</strong><span>documentés</span></div>
              <div><Clock3 size={16}/><strong>{data.counts.review}</strong><span>à relire</span></div>
              <div className={data.counts.attention + data.counts.missing > 0 ? 'has-alert' : ''}>
                <CircleAlert size={16}/><strong>{data.counts.attention + data.counts.missing}</strong><span>à résoudre</span>
              </div>
            </div>

            {data.decision && (
              <div className={'verify-decision ' + data.decision.action}>
                <strong>{data.decision.action === 'reviewed' ? 'Revue terminée' : 'Correction demandée'}</strong>
                <p>{data.decision.note}</p>
                <small>{new Date(data.decision.at).toLocaleString('fr-TN')}</small>
              </div>
            )}

            <div className="verify-signature">
              <small>Empreinte du contenu</small>
              <code>{data.signature}</code>
            </div>

            <div className="verify-scope">
              <ShieldCheck size={14}/>
              <small>{data.scope}</small>
            </div>

            <p className="verify-disclaimer">
              Simulation locale · Aucun dépôt officiel n'est attesté par cette page.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
