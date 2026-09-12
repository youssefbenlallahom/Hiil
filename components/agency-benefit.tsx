'use client';

import {useEffect, useState} from 'react';
import {
  ArrowRight,
  Check,
  Clock3,
  Copy,
  FileSearch,
  History,
  Pause,
  Play,
  RotateCcw,
  ShieldCheck,
  Timer,
} from 'lucide-react';
import Link from 'next/link';

type RecordedTime = {
  id: string;
  label: string;
  seconds: number;
  at: string;
};

export default function AgencyBenefit() {
  const [volume, setVolume] = useState(500);
  const [before, setBefore] = useState(12);
  const [after, setAfter] = useState(5);
  const [copied, setCopied] = useState(false);

  // Chronometer state for self-timed pilot
  const [timerRunning, setTimerRunning] = useState(false);
  const [timerSeconds, setTimerSeconds] = useState(0);
  const [recordedTimes, setRecordedTimes] = useState<RecordedTime[]>([
    {id: 'rec-1', label: 'Dossier démo 1 (contrôle identité + adresse)', seconds: 195, at: 'Exemple indicatif'},
    {id: 'rec-2', label: 'Dossier démo 2 (relecture F005 complet)', seconds: 270, at: 'Exemple indicatif'},
  ]);

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (timerRunning) {
      interval = setInterval(() => {
        setTimerSeconds(s => s + 1);
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [timerRunning]);

  const hours = ((before - after) * volume) / 60;

  function formatTime(totalSec: number) {
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${mins}m ${secs < 10 ? '0' : ''}${secs}s`;
  }

  function recordCurrentTimer() {
    if (timerSeconds === 0) return;
    const newRecord: RecordedTime = {
      id: 'rec-' + Date.now(),
      label: `Revue test #${recordedTimes.length + 1}`,
      seconds: timerSeconds,
      at: new Date().toLocaleTimeString('fr-TN'),
    };
    const updated = [...recordedTimes, newRecord];
    setRecordedTimes(updated);
    setTimerRunning(false);
    setTimerSeconds(0);

    // Update 'after' with the average in minutes
    const avgSec = updated.reduce((acc, r) => acc + r.seconds, 0) / updated.length;
    setAfter(Math.max(1, Math.round((avgSec / 60) * 10) / 10));
  }

  function copySimulation() {
    const summary = `SIMULATION THE AGENCY BENEFIT (Dossier TN)
- Volume mensuel : ${volume} dossiers
- Durée relecture habituelle : ${before} min / dossier
- Durée estimée avec l'outil : ${after} min / dossier
- Gain théorique brut : ${Math.abs(hours).toFixed(1)} h / mois
- Formule : (${before} - ${after}) min × ${volume} dossiers ÷ 60
- Mesures pilotes enregistrées : ${recordedTimes.length} échantillons (moyenne: ${(recordedTimes.reduce((a, b) => a + b.seconds, 0) / (recordedTimes.length || 1) / 60).toFixed(1)} min)

NOTE : Hypothèses de travail pour protocole pilote B2G. Aucun gain financier ou délai officiel n'est certifié.`;
    navigator.clipboard.writeText(summary).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    });
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">BÉNÉFICE INSTITUTIONNEL & PILOTE</div>
          <h1>The Agency Benefit</h1>
          <p>Une hypothèse de gain mesurable que l’administration peut vérifier avec nous.</p>
        </div>
        <div style={{display: 'flex', gap: '10px'}}>
          <button className="btn secondary" onClick={copySimulation}>
            {copied ? <Check size={16} /> : <Copy size={16} />}
            {copied ? 'Copié !' : 'Exporter les hypothèses'}
          </button>
          <Link href="/institution" className="btn primary">
            Voir la revue
            <ArrowRight size={16} />
          </Link>
        </div>
      </div>

      <section className="panel impact-hero">
        <span className="badge amber">Simulation · hypothèses modifiables</span>
        <h2>
          {Math.abs(hours).toLocaleString('fr-TN', {maximumFractionDigits: 1})}
          <span>heures / mois</span>
        </h2>
        <p>
          {hours >= 0
            ? 'potentiellement libérées pour les agents sur ce volume'
            : 'de traitement supplémentaires avec ces hypothèses'}
        </p>

        <div className="impact-inputs">
          <label>
            Dossiers par mois
            <input
              type="number"
              min={0}
              max={100000}
              value={volume}
              onChange={e => setVolume(Math.min(100000, Math.max(0, Number(e.target.value))))}
            />
          </label>
          <label>
            Revue habituelle · min/dossier
            <input
              type="number"
              min={0}
              max={240}
              step={0.5}
              value={before}
              onChange={e => setBefore(Math.min(240, Math.max(0, Number(e.target.value))))}
            />
          </label>
          <label>
            Revue avec l’outil · min/dossier
            <input
              type="number"
              min={0}
              max={240}
              step={0.5}
              value={after}
              onChange={e => setAfter(Math.min(240, Math.max(0, Number(e.target.value))))}
            />
          </label>
        </div>

        <p className="impact-formula">
          ({before} − {after}) minutes × {volume} dossiers ÷ 60
        </p>
        <small>
          Valeurs illustratives basées sur des hypothèses modifiables. Aucun gain financier ou délai officiel n’est garanti.
        </small>
      </section>

      {/* Chronometer & Self-timed pilot section */}
      <section className="panel pilot-timer-section">
        <div className="panel-heading">
          <div>
            <div className="eyebrow">CHRONOMÈTRE DE RELECTURE · PILOTE RÉEL</div>
            <h2>Mesurez votre propre vitesse de relecture</h2>
            <p>
              Testez en direct le temps nécessaire pour vérifier les pièces et motiver une décision avec l'outil.
            </p>
          </div>
          <Timer size={28} className="text-teal" />
        </div>

        <div className="timer-workbench">
          <div className="timer-display-box">
            <span className="timer-value">{formatTime(timerSeconds)}</span>
            <div className="timer-controls">
              {!timerRunning ? (
                <button className="btn primary" onClick={() => setTimerRunning(true)}>
                  <Play size={16} /> Démarrer le test
                </button>
              ) : (
                <button className="btn secondary" onClick={() => setTimerRunning(false)}>
                  <Pause size={16} /> Suspendre
                </button>
              )}
              <button
                className="btn secondary"
                disabled={timerSeconds === 0}
                onClick={() => {
                  setTimerRunning(false);
                  setTimerSeconds(0);
                }}
              >
                <RotateCcw size={15} /> Réinitialiser
              </button>
              <button
                className="btn primary"
                disabled={timerSeconds < 5}
                onClick={recordCurrentTimer}
                style={{background: 'var(--teal)'}}
              >
                <Check size={16} /> Enregistrer cette mesure
              </button>
            </div>
            <small className="timer-hint">
              Conseil jury : lancez le chronomètre, examinez un dossier dans l'espace agent, puis enregistrez la mesure.
            </small>
          </div>

          <div className="timer-log-box">
            <div className="timer-log-header">
              <History size={16} />
              <strong>Échantillons mesurés ({recordedTimes.length})</strong>
              {recordedTimes.length > 0 && (
                <span className="badge blue">
                  Moyenne :{' '}
                  {(
                    recordedTimes.reduce((acc, r) => acc + r.seconds, 0) /
                    recordedTimes.length /
                    60
                  ).toFixed(1)}{' '}
                  min
                </span>
              )}
            </div>
            <ul className="timer-log-list">
              {recordedTimes.map(record => (
                <li key={record.id} className="timer-log-item">
                  <div>
                    <strong>{record.label}</strong>
                    <small>{record.at}</small>
                  </div>
                  <div className="timer-log-badge">
                    <code>{formatTime(record.seconds)}</code>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <div className="impact-cards">
        <article className="panel">
          <FileSearch size={26} />
          <h3>Moins de recherche manuelle</h3>
          <p>
            Chaque rubrique mène directement à son passage source avec citation exacte et numéro de page vérifié dans le document d'origine.
          </p>
        </article>
        <article className="panel">
          <ShieldCheck size={26} />
          <h3>Décision traçable & opposable</h3>
          <p>
            La version transmise est figée sous empreinte SHA-256. L'agent garde le contrôle exclusif de la décision avec observations motivées.
          </p>
        </article>
        <article className="panel">
          <Clock3 size={26} />
          <h3>Méthodologie d'évaluation rigoureuse</h3>
          <p>
            Faire relire des dossiers comparables en double aveugle avec et sans outil. Mesurer temps actif, taux de détection et retours de correction.
          </p>
        </article>
      </div>

      <div className="soft-note">
        <strong>Protocole expérimental pour le jury</strong>
        <p>
          Pour garantir la rigueur scientifique : 10 à 20 dossiers anonymisés ou fictifs, testés avec deux agents instructeurs en ordre alterné. 
          Les indicateurs clés suivis sont : la médiane du temps de traitement, la précision de détection des discordances d'adresses/identifiants, 
          et la réduction des allers-retours grâce aux fiches de correction ciblées.
        </p>
      </div>
    </>
  );
}
