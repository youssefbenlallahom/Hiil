'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import {
  ArrowDownToLine,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Building2,
  Camera,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Eye,
  FileCheck2,
  FileText,
  Fingerprint,
  HelpCircle,
  Info,
  Landmark,
  LoaderCircle,
  Lock,
  Mail,
  MapPin,
  Maximize2,
  PenLine,
  Phone,
  Plus,
  RefreshCw,
  ScanLine,
  Search,
  ShieldCheck,
  Sparkles,
  Tag,
  Upload,
  Users,
  X,
  ZoomIn,
} from 'lucide-react';
import { api, Case } from '@/lib/types';
import { FormCatalog, FormDraft, FormField, Modification, OcrBatch } from '@/lib/form-types';

interface StepMeta {
  index: number;
  title: string;
  subtitle: string;
  badge: string;
  icon: typeof MapPin;
}

const STEPS: StepMeta[] = [
  { index: 0, title: 'Démarche & Objet', subtitle: 'Type de modification à déclarer', badge: 'Formalité', icon: MapPin },
  { index: 1, title: 'L’Entreprise', subtitle: 'Identifiant unique & références', badge: 'Société', icon: Building2 },
  { index: 2, title: 'Les Personnes', subtitle: 'Représentant légal & déclarant', badge: 'Identité', icon: Users },
  { index: 3, title: 'Contact & Date', subtitle: 'Coordonnées officielles de suivi', badge: 'Coordonnées', icon: Mail },
  { index: 4, title: 'Vérification & PDF', subtitle: 'Contrôle final et préparation', badge: 'Validation', icon: FileCheck2 },
];

const STEP_HEADINGS = [
  { kicker: 'ÉTAPE 1 / 05 · OBJET DE LA DÉCLARATION', title: 'Quelle modification', highlight: 'déclarez-vous ?', desc: 'Sélectionnez la ou les formalités applicables à votre entreprise. Les mentions obligatoires du formulaire RNE F005 s’adaptent automatiquement.' },
  { kicker: 'ÉTAPE 2 / 05 · RÉFÉRENCES OFFICIELLES', title: 'Identifiez votre', highlight: 'société.', desc: 'Renseignez l’identifiant unique attribué lors de l’immatriculation au RNE. Ces informations relient formellement votre déclaration à votre dossier fiscal.' },
  { kicker: 'ÉTAPE 3 / 05 · PERSONNES PHYSIQUES', title: 'Qui engage et qui', highlight: 'déclare ?', desc: 'Le représentant légal (gérant/dirigeant) et le déclarant peuvent être la même personne ou deux personnes distinctes. Vous pouvez scanner votre carte CIN pour un remplissage instantané.' },
  { kicker: 'ÉTAPE 4 / 05 · COORDONNÉES ET DÉLAIS', title: 'Où le RNE peut-il', highlight: 'vous joindre ?', desc: 'Ces coordonnées sont utilisées par les services du Registre National des Entreprises pour notifier la recevabilité ou transmettre les demandes d’ajustement.' },
  { kicker: 'ÉTAPE 5 / 05 · FINALISATION DU DOSSIER', title: 'Dernier regard avant', highlight: 'génération.', desc: 'Relisez l’ensemble des mentions reportées sur le document officiel RNE F 005 v1.1. Préparez ensuite votre fichier PDF haute définition prêt pour impression et signature.' },
];

const POPULAR_MODS = [
  { key: 'siege', title: 'Changement d’adresse du siège social', arabic: 'تغيير عنوان المقر الاجتماعي', icon: Building2, desc: 'L’adresse principale et officielle de votre entreprise change.', tag: 'Adresse principale' },
  { key: 'succursale', title: 'Changement d’adresse d’une succursale', arabic: 'تغيير عنوان الفرع', icon: MapPin, desc: 'Un établissement secondaire, bureau ou atelier change de local.', tag: 'Établissement secondaire' },
  { key: 'denomination', title: 'Changement de dénomination ou enseigne', arabic: 'تغيير التسمية الاجتماعية أو الاسم التجاري أو الشارة', icon: Tag, desc: 'Modification du nom officiel de la société, du nom commercial ou de l’enseigne.', tag: 'Identité' },
  { key: 'activite', title: 'Changement ou ajout d’activité', arabic: 'تغيير أو إضافة أو حذف نشاط', icon: Sparkles, desc: 'Extension de l’objet social, modification du code d’activité principale.', tag: 'Activité' },
  { key: 'dirigeants', title: 'Mise à jour des dirigeants', arabic: 'إضافة أو تحيين المسيرين', icon: Users, desc: 'Nomination, démission ou changement de gérant ou d’administrateur.', tag: 'Gouvernance' },
  { key: 'banque', title: 'Modification du compte bancaire', arabic: 'تغيير الحساب البنكي', icon: Landmark, desc: 'Changement de compte bancaire professionnel avec mention du nouveau RIB.', tag: 'Banque' },
];

const blankDraft: FormDraft = {
  revision: 0,
  fields: {},
  modifications: [],
  same_person: false,
  step: 0,
  generated_revision: null,
  imports: [],
  errors: {},
  ready: false,
  has_pdf: false,
};

export default function FormWizard({ c }: { c: Case }) {
  const [catalog, setCatalog] = useState<FormCatalog | null>(null);
  const [draft, setDraft] = useState<FormDraft>(blankDraft);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'dirty' | 'error'>('saved');
  const [activeTab, setActiveTab] = useState<'guide' | 'preview'>('guide');
  const [focusedField, setFocusedField] = useState('identifiant_unique');
  const [previewPage, setPreviewPage] = useState<1 | 2>(1);
  const [searchMod, setSearchMod] = useState('');
  const [showAllMods, setShowAllMods] = useState(false);
  const [reviewed, setReviewed] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrBatch, setOcrBatch] = useState<OcrBatch | null>(null);
  const [ocrSelections, setOcrSelections] = useState<Record<string, number>>({});
  const [showErrors, setShowErrors] = useState(false);

  const revisionRef = useRef(0);
  const latestDraftRef = useRef<FormDraft>(blankDraft);
  const queueRef = useRef(Promise.resolve());
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const epochRef = useRef(0);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const ocrDialogRef = useRef<HTMLDialogElement>(null);
  const previewModalRef = useRef<HTMLDialogElement>(null);

  const baseEndpoint = `/cases/${c.id}/f005`;

  // Initial Load
  useEffect(() => {
    let active = true;
    Promise.all([
      api<FormCatalog>('/f005/catalog'),
      api<FormDraft>(baseEndpoint),
    ])
      .then(([cat, initialDraft]) => {
        if (!active) return;
        setCatalog(cat);
        // Pre-fill company ID if present and draft fields empty
        if (!initialDraft.fields.identifiant_unique && c.id) {
          const matchedDoc = c.documents.flatMap((d) => d.fields).find((f) => f.key === 'company_id');
          if (matchedDoc?.value) {
            initialDraft.fields.identifiant_unique = matchedDoc.value.replace(/[^A-Za-z0-9]/g, '');
          }
        }
        // Default to siege modification if none selected yet
        if (!initialDraft.modifications.length) {
          initialDraft.modifications = ['siege'];
        }
        setDraft(initialDraft);
        latestDraftRef.current = initialDraft;
        revisionRef.current = initialDraft.revision;
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Erreur de chargement');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, [baseEndpoint, c.id, c.documents]);

  // Persist Changes
  function persistDraft(target: FormDraft, currentEpoch: number) {
    setSaveStatus('saving');
    const op = queueRef.current.then(async () => {
      const saved = await api<FormDraft>(baseEndpoint, {
        method: 'POST',
        body: JSON.stringify({
          revision: revisionRef.current,
          fields: target.fields,
          modifications: target.modifications,
          same_person: target.same_person,
          step: target.step,
        }),
      });
      revisionRef.current = saved.revision;
      if (currentEpoch === epochRef.current) {
        setDraft(saved);
        latestDraftRef.current = saved;
        setSaveStatus('saved');
      }
    });

    queueRef.current = op.catch((err) => {
      setError(err instanceof Error ? err.message : 'Erreur d’enregistrement');
      setSaveStatus('error');
    });

    return op;
  }

  function handleDraftChange(patch: Partial<FormDraft>) {
    const next: FormDraft = {
      ...latestDraftRef.current,
      ...patch,
      has_pdf: false,
      generated_revision: null,
    };

    if (next.same_person) {
      next.fields = {
        ...next.fields,
        nom_declarant: next.fields.representant_legal || '',
        identite_declarant: next.fields.identite_representant || '',
      };
    }

    epochRef.current++;
    latestDraftRef.current = next;
    setDraft(next);
    setReviewed(false);
    setSaveStatus('dirty');
    setError('');

    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    const thisEpoch = epochRef.current;
    saveTimerRef.current = setTimeout(() => {
      saveTimerRef.current = null;
      void persistDraft(next, thisEpoch).catch(() => {});
    }, 600);
  }

  async function flushSaveQueue() {
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
      saveTimerRef.current = null;
      await persistDraft(latestDraftRef.current, epochRef.current);
    } else {
      await queueRef.current;
    }
    return latestDraftRef.current;
  }

  async function navigateToStep(targetStep: number, validateCurrent = false) {
    try {
      const saved = await flushSaveQueue();
      if (validateCurrent && catalog) {
        const stepKeys =
          draft.step === 0
            ? ['modifications']
            : catalog.fields.filter((f) => f.step === draft.step).map((f) => f.key);
        const hasError = stepKeys.find((k) => saved.errors[k]);
        if (hasError) {
          setShowErrors(true);
          setFocusedField(hasError);
          document.getElementById(`field-${hasError}`)?.focus();
          return;
        }
      }

      handleDraftChange({ step: targetStep });
      setShowErrors(false);
      setPreviewPage(targetStep >= 3 ? 2 : 1);

      const nextField = catalog?.fields.find((f) => f.step === targetStep);
      if (nextField) setFocusedField(nextField.key);

      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch {
      // Handled via state error
    }
  }

  // OCR Processing
  async function processDocumentFile(file: File, kind = 'representative') {
    setOcrLoading(true);
    setError('');
    try {
      await flushSaveQueue();
      const formData = new FormData();
      formData.append('file', file);
      formData.append('kind', kind);

      const batch = await api<OcrBatch>(`${baseEndpoint}/ocr`, {
        method: 'POST',
        body: formData,
      });

      setOcrBatch(batch);
      // Auto-select top candidate for each unique key
      const initialChoices: Record<string, number> = {};
      batch.candidates.forEach((cand, idx) => {
        if (!(cand.key in initialChoices)) {
          initialChoices[cand.key] = idx;
        }
      });
      setOcrSelections(initialChoices);
      ocrDialogRef.current?.showModal();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Échec de la lecture OCR');
    } finally {
      setOcrLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
      if (cameraInputRef.current) cameraInputRef.current.value = '';
    }
  }

  function applyOcrChoices() {
    if (!ocrBatch) return;
    const updatedFields = { ...latestDraftRef.current.fields };

    Object.values(ocrSelections).forEach((idx) => {
      const candidate = ocrBatch.candidates[idx];
      if (!candidate) return;
      let val = candidate.value.trim();

      if (candidate.key === 'date' && /^\d{2}\s*[/]\s*\d{2}\s*[/]\s*\d{4}$/.test(val)) {
        const parts = val.replaceAll(' ', '').split('/');
        val = `${parts[2]}-${parts[1]}-${parts[0]}`;
      }
      if (['identite_representant', 'identite_declarant', 'identifiant_unique', 'rib'].includes(candidate.key)) {
        val = val.replace(/[\s\-]/g, '');
      }

      updatedFields[candidate.key] = val;
    });

    handleDraftChange({
      fields: updatedFields,
      imports: [...latestDraftRef.current.imports.filter((b) => b.id !== ocrBatch.id), ocrBatch],
    });

    ocrDialogRef.current?.close();
    setNotice(`${Object.keys(ocrSelections).length} renseignement(s) reporté(s) automatiquement depuis votre pièce.`);
  }

  // Final PDF Generation
  async function generateOfficialPdf() {
    setGenerating(true);
    setError('');
    try {
      await flushSaveQueue();
      const result = await api<FormDraft>(`${baseEndpoint}/generate`, {
        method: 'POST',
        body: JSON.stringify({ revision: revisionRef.current, reviewed }),
      });
      latestDraftRef.current = result;
      setDraft(result);
      setNotice('🎉 Votre formulaire officiel RNE F005 est prêt à être téléchargé et signé !');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de générer le formulaire');
    } finally {
      setGenerating(false);
    }
  }

  // Active field lookup
  const activeFieldInfo = catalog?.fields.find((f) => f.key === focusedField);
  const currentStep = draft.step;
  const requiredFields = catalog?.fields.filter((f) => f.required || (f.key === 'rib' && draft.modifications.includes('banque'))) || [];
  const completedFieldsCount = requiredFields.filter((f) => draft.fields[f.key]?.trim() && !draft.errors[f.key]).length;
  const overallProgress = Math.min(100, Math.round(((completedFieldsCount + (draft.modifications.length ? 1 : 0)) / (requiredFields.length + 1)) * 100));

  // Render 8-box segment display for CIN and Unique ID
  function renderBoxSegmentDisplay(val: string, maxBoxes = 8, label = '') {
    const cleanChars = (val || '').replace(/[\s\-]/g, '').slice(0, maxBoxes);
    const boxes = Array.from({ length: maxBoxes }, (_, i) => cleanChars[i] || '');

    return (
      <div className="fw-box-visualizer" aria-label={`Disposition dans les cases officielles : ${label}`}>
        <div className="fw-box-cells">
          {boxes.map((ch, idx) => (
            <div key={idx} className={`fw-box-cell ${ch ? 'has-char' : 'empty'}`}>
              <span>{ch}</span>
              <span className="fw-cell-index">{idx + 1}</span>
            </div>
          ))}
        </div>
        <div className="fw-box-caption">
          <span>Reproduction des {maxBoxes} cases sur le formulaire officiel</span>
          <span>{cleanChars.length} / {maxBoxes}</span>
        </div>
      </div>
    );
  }

  // Render individual input field
  function renderFormField(f: FormField) {
    const isSamePersonDisabled = draft.same_person && ['nom_declarant', 'identite_declarant'].includes(f.key);
    const isInvalid = showErrors && !!draft.errors[f.key];
    const isNeeded = f.required || (f.key === 'rib' && draft.modifications.includes('banque'));
    const isBoxedField = ['identifiant_unique', 'identite_representant', 'identite_declarant'].includes(f.key);
    const boxCount = f.key === 'identifiant_unique' ? 8 : 8;

    return (
      <div
        key={f.key}
        className={`fw-field-container ${focusedField === f.key ? 'is-focused' : ''} ${isInvalid ? 'is-invalid' : ''} ${isSamePersonDisabled ? 'is-disabled' : ''}`}
        onFocus={() => {
          setFocusedField(f.key);
          setActiveTab('guide');
        }}
      >
        <div className="fw-field-header">
          <div className="fw-field-title-group">
            <label htmlFor={`field-${f.key}`} className="fw-field-label">
              {f.label}
              {isNeeded && <span className="fw-required-star" title="Champ obligatoire au RNE">*</span>}
            </label>
            <span className="fw-field-arabic" lang="ar" dir="rtl">
              {f.arabic}
            </span>
          </div>

          <div className="fw-field-actions">
            {f.badge && <span className="fw-badge-pill">{f.badge}</span>}
            <button
              type="button"
              className="fw-field-help-btn"
              onClick={() => {
                setFocusedField(f.key);
                setActiveTab('guide');
              }}
              title="Voir l'explication officielle de ce champ"
              aria-label={`Comprendre le champ ${f.label}`}
            >
              <HelpCircle size={16} />
              <span>Aide</span>
            </button>
          </div>
        </div>

        <div className="fw-input-wrapper">
          {f.key === 'gsm' && (
            <span className="fw-input-prefix" title="Indicatif international Tunisie">
              🇹🇳 +216
            </span>
          )}
          {isSamePersonDisabled && (
            <span className="fw-input-lock" title="Recopié automatiquement du représentant légal">
              <Lock size={15} />
            </span>
          )}
          <input
            id={`field-${f.key}`}
            type={f.input_type}
            value={draft.fields[f.key] || ''}
            onChange={(e) => {
              let val = e.target.value;
              if (f.key === 'identifiant_unique') val = val.toUpperCase().replace(/[^A-Z0-9]/g, '');
              if (['identite_representant', 'identite_declarant'].includes(f.key)) val = val.replace(/\D/g, '');
              handleDraftChange({ fields: { ...draft.fields, [f.key]: val } });
            }}
            placeholder={f.example}
            disabled={isSamePersonDisabled}
            dir={['email', 'tel', 'date'].includes(f.input_type) ? 'ltr' : 'auto'}
            maxLength={f.max_length}
            className="fw-input"
            autoComplete="off"
            aria-invalid={isInvalid}
          />
        </div>

        {/* Visual Box Cell representation for CIN and ID Unique */}
        {isBoxedField && renderBoxSegmentDisplay(draft.fields[f.key] || '', boxCount, f.label)}

        {/* Real-time status / error hint */}
        {isInvalid ? (
          <p className="fw-field-error-msg">
            <CircleAlert size={14} />
            {draft.errors[f.key]}
          </p>
        ) : (
          <p className="fw-field-hint">{f.help}</p>
        )}

        {/* Mobile / Inline expandable guidance */}
        <details className="fw-field-accordion">
          <summary>
            <Info size={14} />
            <span>Comment bien remplir ce champ ? (Où le trouver & Pièges)</span>
          </summary>
          <div className="fw-accordion-body">
            <div className="fw-acc-row">
              <strong>Où le trouver :</strong>
              <span>{f.where}</span>
            </div>
            {f.how && (
              <div className="fw-acc-row">
                <strong>Format attendu :</strong>
                <span>{f.how}</span>
              </div>
            )}
            {f.pitfalls && (
              <div className="fw-acc-row fw-pitfall">
                <strong>Piège à éviter :</strong>
                <span>{f.pitfalls}</span>
              </div>
            )}
            {f.law_ref && (
              <div className="fw-acc-row fw-law">
                <strong>Référence légale :</strong>
                <span>{f.law_ref}</span>
              </div>
            )}
          </div>
        </details>
      </div>
    );
  }

  return (
    <div className="form-studio">
      {/* ── Top Bar ── */}
      <header className="fw-topbar">
        <div className="fw-topbar-left">
          <Link href="/" className="fw-logo">
            <span className="fw-logo-icon">
              <FileText size={20} />
            </span>
            <span className="fw-logo-text">
              Dossier<span className="fw-logo-accent">TN</span>
            </span>
          </Link>
          <div className="fw-topbar-divider" />
          <div className="fw-topbar-breadcrumb">
            <span className="fw-live-indicator" title="Formulaire interactif connecté au RNE" />
            <span className="fw-breadcrumb-sub">Atelier interactif</span>
            <span className="fw-breadcrumb-slash">/</span>
            <strong className="fw-breadcrumb-doc">Déclaration RNE F005 (v1.1)</strong>
          </div>
        </div>

        <div className="fw-topbar-right">
          <div className={`fw-save-badge ${saveStatus}`}>
            {saveStatus === 'saving' && <LoaderCircle size={14} className="spin" />}
            {saveStatus === 'saved' && <CheckCheck size={15} />}
            {saveStatus === 'error' && <CircleAlert size={15} />}
            <span>
              {saveStatus === 'saved'
                ? 'Sauvegardé automatiquement'
                : saveStatus === 'saving'
                ? 'Enregistrement en cours…'
                : saveStatus === 'error'
                ? 'Erreur de sauvegarde'
                : 'Modifications en attente'}
            </span>
          </div>

          <Link href={`/dossiers/${c.id}`} className="fw-back-btn">
            <ArrowLeft size={15} />
            <span>Retour au dossier {c.id}</span>
          </Link>
        </div>
      </header>

      {/* ── Main Studio Grid Layout ── */}
      {loading ? (
        <div className="fw-loading-screen">
          <div className="fw-loading-card">
            <LoaderCircle size={36} className="spin" />
            <h3>Préparation de votre atelier F005…</h3>
            <p>Chargement des exigences réglementaires du Registre National des Entreprises.</p>
          </div>
        </div>
      ) : !catalog ? (
        <div className="fw-error-screen">
          <CircleAlert size={36} />
          <h3>Impossible de charger le formulaire</h3>
          <p>{error || 'Une erreur réseau est survenue lors de l’initialisation.'}</p>
          <button className="fw-btn primary" onClick={() => window.location.reload()}>
            <RefreshCw size={16} />
            Réessayer
          </button>
        </div>
      ) : (
        <div className="fw-studio-grid">
          {/* ── Left Sidebar : Parcour Stepper ── */}
          <aside className="fw-sidebar-journey">
            <div className="fw-company-card">
              <div className="fw-company-avatar">
                <Building2 size={20} />
              </div>
              <div className="fw-company-meta">
                <strong>{c.company}</strong>
                <span>Dossier {c.id} · Personne morale</span>
              </div>
            </div>

            <div className="fw-stepper-title">VOTRE PARCOURS RNE</div>

            <nav className="fw-stepper-nav" aria-label="Étapes de la démarche">
              {STEPS.map((s) => {
                const isActive = currentStep === s.index;
                const isPassed = currentStep > s.index;
                const StepIcon = s.icon;

                return (
                  <button
                    key={s.title}
                    type="button"
                    className={`fw-step-item ${isActive ? 'is-active' : ''} ${isPassed ? 'is-passed' : ''}`}
                    onClick={() => navigateToStep(s.index)}
                    aria-current={isActive ? 'step' : undefined}
                  >
                    <div className="fw-step-num">
                      {isPassed ? <Check size={15} /> : s.index + 1}
                    </div>
                    <div className="fw-step-texts">
                      <span className="fw-step-name">{s.title}</span>
                      <small className="fw-step-sub">{s.subtitle}</small>
                    </div>
                    {isActive && <ChevronRight size={16} className="fw-step-caret" />}
                  </button>
                );
              })}
            </nav>

            {/* Overall Progress Gauge */}
            <div className="fw-progress-card">
              <div className="fw-progress-meta">
                <span>Progression</span>
                <strong>{overallProgress}%</strong>
              </div>
              <div className="fw-progress-bar">
                <div className="fw-progress-fill" style={{ width: `${overallProgress}%` }} />
              </div>
              <p className="fw-progress-caption">
                {completedFieldsCount} sur {requiredFields.length} champs obligatoires validés
              </p>
            </div>

            {/* Reference Source Notice */}
            <div className="fw-legal-card">
              <div className="fw-legal-top">
                <ShieldCheck size={18} />
                <strong>Conformité RNE Tunisie</strong>
              </div>
              <p>
                Formulaire officiel F 005 v1.1 établi en vertu de la loi n° 2018-52. Calque vectoriel de saisie haute précision.
              </p>
              <a href="/api/f005/template" target="_blank" rel="noreferrer" className="fw-legal-link">
                <span>Consulter le formulaire vierge</span>
                <ArrowUpRight size={13} />
              </a>
            </div>
          </aside>

          {/* ── Central Main Pipeline Workspace ── */}
          <main className="fw-center-workspace">
            {/* Header / Eyebrow of step */}
            <div className="fw-step-header">
              <div className="fw-step-kicker">
                {STEP_HEADINGS[currentStep].kicker}
              </div>
              <h1 className="fw-step-title">
                {STEP_HEADINGS[currentStep].title} <em>{STEP_HEADINGS[currentStep].highlight}</em>
              </h1>
              <p className="fw-step-desc">{STEP_HEADINGS[currentStep].desc}</p>
            </div>

            {/* Notification alert banners */}
            {error && (
              <div className="fw-alert fw-alert-error" role="alert">
                <CircleAlert size={18} />
                <span>{error}</span>
                <button type="button" onClick={() => setError('')} aria-label="Fermer l'alerte">
                  <X size={16} />
                </button>
              </div>
            )}
            {notice && (
              <div className="fw-alert fw-alert-success" role="status">
                <CheckCheck size={18} />
                <span>{notice}</span>
                <button type="button" onClick={() => setNotice('')} aria-label="Fermer l'avis">
                  <X size={16} />
                </button>
              </div>
            )}

            {/* ════════════ STEP 0: CHOIX DES MODIFICATIONS ════════════ */}
            {currentStep === 0 && (
              <section className="fw-step-content fw-modifications-step">
                <div className="fw-section-header">
                  <Sparkles size={20} className="fw-sec-icon" />
                  <div>
                    <h2>Sélectionnez vos modifications</h2>
                    <p>Cochez les motifs qui correspondent exactement à votre démarche.</p>
                  </div>
                </div>

                <div className="fw-mod-cards-grid">
                  {POPULAR_MODS.map((item) => {
                    const isChecked = draft.modifications.includes(item.key);
                    const ModIcon = item.icon;

                    return (
                      <button
                        key={item.key}
                        type="button"
                        className={`fw-mod-card ${isChecked ? 'is-checked' : ''}`}
                        onClick={() => {
                          const updated = isChecked
                            ? draft.modifications.filter((k) => k !== item.key)
                            : [...draft.modifications, item.key];
                          handleDraftChange({ modifications: updated });
                        }}
                      >
                        <div className="fw-mod-card-top">
                          <span className="fw-mod-card-icon">
                            <ModIcon size={24} />
                          </span>
                          <span className="fw-mod-checkbox">
                            {isChecked && <Check size={13} />}
                          </span>
                        </div>
                        <div className="fw-mod-card-tag">{item.tag}</div>
                        <h3 className="fw-mod-card-title">{item.title}</h3>
                        <span className="fw-mod-card-arabic" lang="ar" dir="rtl">
                          {item.arabic}
                        </span>
                        <p className="fw-mod-card-desc">{item.desc}</p>
                      </button>
                    );
                  })}
                </div>

                {showErrors && draft.errors.modifications && (
                  <p className="fw-step-error-msg">
                    <CircleAlert size={15} />
                    {draft.errors.modifications}
                  </p>
                )}

                {/* Collapsible section for other 22 RNE modifications */}
                <div className="fw-all-mods-wrapper">
                  <button
                    type="button"
                    className="fw-toggle-all-mods-btn"
                    onClick={() => setShowAllMods(!showAllMods)}
                    aria-expanded={showAllMods}
                  >
                    <Plus size={18} />
                    <span>Consulter les autres modifications RNE (Augmentation capital, Statuts, Liquidation…)</span>
                    <ChevronDown size={18} className={`fw-caret-anim ${showAllMods ? 'open' : ''}`} />
                  </button>

                  {showAllMods && (
                    <div className="fw-all-mods-drawer">
                      <div className="fw-mods-search-box">
                        <Search size={16} />
                        <input
                          type="text"
                          value={searchMod}
                          onChange={(e) => setSearchMod(e.target.value)}
                          placeholder="Rechercher parmi les 28 modifications RNE…"
                        />
                      </div>

                      <div className="fw-mods-list">
                        {catalog.modifications
                          .filter(
                            (m) =>
                              !POPULAR_MODS.map((p) => p.key).includes(m.key) &&
                              `${m.label} ${m.arabic} ${m.group}`.toLowerCase().includes(searchMod.toLowerCase())
                          )
                          .map((m) => {
                            const isChecked = draft.modifications.includes(m.key);
                            return (
                              <label key={m.key} className={`fw-mod-row ${isChecked ? 'selected' : ''}`}>
                                <input
                                  type="checkbox"
                                  checked={isChecked}
                                  onChange={(e) => {
                                    const updated = e.target.checked
                                      ? [...draft.modifications, m.key]
                                      : draft.modifications.filter((k) => k !== m.key);
                                    handleDraftChange({ modifications: updated });
                                  }}
                                />
                                <div className="fw-mod-row-info">
                                  <div className="fw-mod-row-title">
                                    <strong>{m.label}</strong>
                                    <span className="fw-mod-row-group">{m.group}</span>
                                  </div>
                                  <span className="fw-mod-row-ar" lang="ar" dir="rtl">{m.arabic}</span>
                                  <p className="fw-mod-row-help">{m.help}</p>
                                </div>
                              </label>
                            );
                          })}
                      </div>
                    </div>
                  )}
                </div>

                {/* Selected tags list */}
                {draft.modifications.length > 0 && (
                  <div className="fw-selected-mod-tags">
                    <span className="fw-selected-tags-label">Modifications retenues ({draft.modifications.length}) :</span>
                    <div className="fw-tags-flex">
                      {draft.modifications.map((mKey) => {
                        const mObj = catalog.modifications.find((m) => m.key === mKey);
                        return (
                          <span key={mKey} className="fw-tag-badge">
                            {mObj?.label || mKey}
                            <button
                              type="button"
                              onClick={() =>
                                handleDraftChange({
                                  modifications: draft.modifications.filter((k) => k !== mKey),
                                })
                              }
                              title="Retirer cette modification"
                            >
                              <X size={12} />
                            </button>
                          </span>
                        );
                      })}
                    </div>
                  </div>
                )}
              </section>
            )}

            {/* ════════════ STEP 1: L'ENTREPRISE ════════════ */}
            {currentStep === 1 && (
              <section className="fw-step-content">
                {/* Fast OCR Import Banner for Company / Registry document */}
                <div className="fw-ocr-hero-card">
                  <div className="fw-ocr-hero-left">
                    <div className="fw-ocr-hero-icon">
                      <ScanLine size={24} />
                    </div>
                    <div>
                      <h3>Remplissage express via Extrait RNE ou Patente</h3>
                      <p>Importez votre extrait de registre pour extraire automatiquement l’identifiant unique et le représentant légal.</p>
                    </div>
                  </div>
                  <div className="fw-ocr-hero-actions">
                    <button
                      type="button"
                      className="fw-btn secondary"
                      disabled={ocrLoading}
                      onClick={() => fileInputRef.current?.click()}
                    >
                      {ocrLoading ? <LoaderCircle size={16} className="spin" /> : <Upload size={16} />}
                      {ocrLoading ? 'Analyse…' : 'Importer un Extrait RNE'}
                    </button>
                  </div>
                </div>

                <div className="fw-card-panel">
                  <div className="fw-card-panel-header">
                    <Landmark size={22} className="fw-panel-icon" />
                    <div>
                      <h2>Références officielles de l’entreprise</h2>
                      <p>Telles qu’inscrites au Registre National des Entreprises de la République Tunisienne.</p>
                    </div>
                  </div>

                  <div className="fw-fields-stack">
                    {catalog.fields.filter((f) => f.step === 1).map(renderFormField)}
                  </div>
                </div>
              </section>
            )}

            {/* ════════════ STEP 2: LES PERSONNES ════════════ */}
            {currentStep === 2 && (
              <section className="fw-step-content">
                {/* Dedicated Photo & OCR Card for Tunisian CIN */}
                <div className="fw-cin-scanner-card">
                  <div className="fw-cin-scanner-inner">
                    <div className="fw-scanner-illustration">
                      <div className="fw-id-badge-icon">
                        <Fingerprint size={28} />
                      </div>
                    </div>
                    <div className="fw-scanner-details">
                      <div className="fw-scanner-badge">OCR DYNAMIQUE TUNISIE (CIN)</div>
                      <h3>Scanner la Carte d’Identité Nationale</h3>
                      <p>
                        Prenez en photo ou importez le recto de votre carte CIN tunisienne. Le numéro à 8 chiffres et le nom officiel du titulaire seront extraits instantanément.
                      </p>
                      <div className="fw-scanner-buttons">
                        <button
                          type="button"
                          className="fw-btn primary"
                          disabled={ocrLoading}
                          onClick={() => cameraInputRef.current?.click()}
                        >
                          {ocrLoading ? <LoaderCircle size={16} className="spin" /> : <Camera size={16} />}
                          <span>Prendre en photo la CIN</span>
                        </button>

                        <button
                          type="button"
                          className="fw-btn secondary"
                          disabled={ocrLoading}
                          onClick={() => fileInputRef.current?.click()}
                        >
                          <Upload size={15} />
                          <span>Importer scan / fichier</span>
                        </button>
                      </div>
                      <small className="fw-scanner-hint">
                        Formats supportés : JPG, PNG, PDF · Traité localement et de manière confidentielle.
                      </small>
                    </div>
                  </div>
                </div>

                {/* Legal Representative Card */}
                <div className="fw-card-panel">
                  <div className="fw-card-panel-header">
                    <Users size={22} className="fw-panel-icon" />
                    <div>
                      <h2>Le Représentant Légal</h2>
                      <p>Le gérant statutaire ou mandataire social habilité à engager la société.</p>
                    </div>
                  </div>

                  <div className="fw-fields-stack">
                    {catalog.fields
                      .filter((f) => ['representant_legal', 'identite_representant'].includes(f.key))
                      .map(renderFormField)}
                  </div>

                  {/* Checkbox: Declarant is the same person */}
                  <label className={`fw-same-person-switch ${draft.same_person ? 'is-active' : ''}`}>
                    <input
                      type="checkbox"
                      checked={draft.same_person}
                      onChange={(e) => handleDraftChange({ same_person: e.target.checked })}
                    />
                    <div className="fw-switch-body">
                      <strong>Le représentant légal effectue lui-même la déclaration</strong>
                      <p>
                        Cochez cette case si le gérant dépose personnellement. Son nom et son numéro de CIN seront automatiquement recopiés dans les champs du déclarant.
                      </p>
                    </div>
                    {draft.same_person && <CheckCheck size={18} className="fw-switch-check" />}
                  </label>
                </div>

                {/* Declarant Card */}
                <div className={`fw-card-panel ${draft.same_person ? 'is-replicated' : ''}`}>
                  <div className="fw-card-panel-header">
                    <PenLine size={22} className="fw-panel-icon" />
                    <div>
                      <h2>Le Déclarant (Signataire)</h2>
                      <p>
                        {draft.same_person
                          ? 'Identique au représentant légal (champs verrouillés et synchronisés).'
                          : 'La personne qui dépose la formalité au guichet du RNE (joindre une procuration légalisée).'}
                      </p>
                    </div>
                  </div>

                  <div className="fw-fields-stack">
                    {catalog.fields
                      .filter((f) => ['nom_declarant', 'identite_declarant'].includes(f.key))
                      .map(renderFormField)}
                  </div>
                </div>
              </section>
            )}

            {/* ════════════ STEP 3: CONTACT & DATE ════════════ */}
            {currentStep === 3 && (
              <section className="fw-step-content">
                <div className="fw-card-panel">
                  <div className="fw-card-panel-header">
                    <Mail size={22} className="fw-panel-icon" />
                    <div>
                      <h2>Coordonnées pour le suivi du dossier</h2>
                      <p>Ces éléments sont requis par le RNE pour vous notifier la validation de la mise à jour.</p>
                    </div>
                  </div>

                  <div className="fw-fields-stack">
                    {catalog.fields.filter((f) => f.step === 3).map(renderFormField)}
                  </div>
                </div>
              </section>
            )}

            {/* ════════════ STEP 4: VÉRIFICATION & PRÉPARATION ════════════ */}
            {currentStep === 4 && (
              <section className="fw-step-content fw-review-step">
                <div className="fw-review-hero-card">
                  <div className="fw-review-hero-icon">
                    <FileCheck2 size={32} />
                  </div>
                  <div>
                    <span className="fw-badge-pill light">ÉTAPE FINALE</span>
                    <h2>Récapitulatif de votre déclaration</h2>
                    <p>
                      Vérifiez l’exactitude de chaque mention avant de générer le formulaire officiel RNE F005.
                    </p>
                  </div>
                </div>

                {/* Summary by sections */}
                <div className="fw-review-section">
                  <div className="fw-review-section-header">
                    <h3>Modifications déclarées</h3>
                    <button type="button" className="fw-edit-link" onClick={() => navigateToStep(0)}>
                      <PenLine size={13} />
                      Modifier
                    </button>
                  </div>
                  <div className="fw-review-mods-badges">
                    {draft.modifications.map((mKey) => {
                      const mObj = catalog.modifications.find((m) => m.key === mKey);
                      return (
                        <span key={mKey} className="fw-review-mod-badge">
                          <Check size={13} />
                          {mObj?.label || mKey}
                        </span>
                      );
                    })}
                  </div>
                </div>

                {[1, 2, 3].map((stepIdx) => {
                  const stepFields = catalog.fields.filter((f) => f.step === stepIdx);

                  return (
                    <div key={stepIdx} className="fw-review-section">
                      <div className="fw-review-section-header">
                        <h3>{STEPS[stepIdx].title}</h3>
                        <button type="button" className="fw-edit-link" onClick={() => navigateToStep(stepIdx)}>
                          <PenLine size={13} />
                          Modifier
                        </button>
                      </div>

                      <div className="fw-review-grid">
                        {stepFields.map((f) => {
                          const val = draft.fields[f.key];
                          const hasErr = draft.errors[f.key];

                          return (
                            <div key={f.key} className={`fw-review-cell ${hasErr ? 'has-error' : ''}`}>
                              <span className="fw-review-label">{f.label}</span>
                              <strong className="fw-review-val" dir="auto">
                                {val || (f.required ? '⚠️ À compléter' : 'Non renseigné')}
                              </strong>
                              {hasErr && <span className="fw-review-err-hint">{hasErr}</span>}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}

                {/* Signature reminder note */}
                <div className="fw-signature-banner">
                  <PenLine size={24} className="fw-sig-icon" />
                  <div>
                    <h4>Formalisation & Signature</h4>
                    <p>
                      {catalog.guidance.signature ||
                        'Après impression du fichier PDF préparé, le déclarant doit apposer sa signature manuscrite à l’emplacement prévu en page 2.'}
                    </p>
                  </div>
                </div>

                {/* Acknowledgment checkbox */}
                <label className="fw-confirmation-checkbox">
                  <input
                    type="checkbox"
                    checked={reviewed}
                    onChange={(e) => setReviewed(e.target.checked)}
                  />
                  <span>
                    J’ai vérifié l’exactitude de l’ensemble des informations ci-dessus et leur stricte concordance avec mes pièces justificatives.
                  </span>
                </label>

                {/* Action buttons */}
                <div className="fw-final-actions-area">
                  {draft.has_pdf ? (
                    <div className="fw-pdf-ready-box">
                      <div className="fw-pdf-ready-left">
                        <CheckCheck size={26} />
                        <div>
                          <strong>Formulaire officiel RNE F005 généré avec succès !</strong>
                          <span>Page 1 et Page 2 complétées selon les normes du Registre National.</span>
                        </div>
                      </div>
                      <a href={`/api${baseEndpoint}/pdf`} className="fw-btn primary download-btn">
                        <ArrowDownToLine size={18} />
                        <span>Télécharger le PDF officiel à signer</span>
                      </a>
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="fw-btn primary generate-btn"
                      disabled={!reviewed || !draft.ready || generating || saveStatus !== 'saved'}
                      onClick={generateOfficialPdf}
                    >
                      {generating ? <LoaderCircle size={18} className="spin" /> : <FileCheck2 size={18} />}
                      <span>{generating ? 'Génération du document haute définition…' : 'Générer le formulaire officiel RNE F005'}</span>
                    </button>
                  )}
                </div>
              </section>
            )}

            {/* ── Footer Navigation Buttons ── */}
            <footer className="fw-nav-footer">
              <button
                type="button"
                className="fw-btn ghost"
                onClick={() => (currentStep > 0 ? navigateToStep(currentStep - 1) : flushSaveQueue())}
              >
                {currentStep > 0 ? <ArrowLeft size={16} /> : <CheckCheck size={16} />}
                <span>{currentStep > 0 ? 'Étape précédente' : 'Enregistrer maintenant'}</span>
              </button>

              <div className="fw-nav-footer-right">
                {currentStep < 4 ? (
                  <button
                    type="button"
                    className="fw-btn primary"
                    onClick={() => navigateToStep(currentStep + 1, true)}
                  >
                    <span>Continuer vers {STEPS[currentStep + 1].title}</span>
                    <ArrowRight size={17} />
                  </button>
                ) : (
                  <span className="fw-legal-disclaimer-tag">
                    <ShieldCheck size={14} />
                    Préparation numérique certifiée
                  </span>
                )}
              </div>
            </footer>
          </main>

          {/* ── Right-Hand Companion (Le Bon Repère & Aperçu PDF) ── */}
          <aside className="fw-companion-sidebar">
            {/* Tab Toggle */}
            <div className="fw-companion-tabs">
              <button
                type="button"
                className={`fw-tab-btn ${activeTab === 'guide' ? 'active' : ''}`}
                onClick={() => setActiveTab('guide')}
              >
                <HelpCircle size={16} />
                <span>Guide RNE</span>
              </button>
              <button
                type="button"
                className={`fw-tab-btn ${activeTab === 'preview' ? 'active' : ''}`}
                onClick={() => setActiveTab('preview')}
              >
                <Eye size={16} />
                <span>Aperçu PDF Direct</span>
              </button>
            </div>

            {/* TAB 1: Guide RNE & Explication du champ actif */}
            {activeTab === 'guide' && (
              <div className="fw-guide-panel">
                <div className="fw-guide-header">
                  <span className="fw-guide-badge">LE BON REPÈRE RNE</span>
                  <h3 className="fw-guide-title">
                    {currentStep === 0
                      ? 'Type de formalité RNE'
                      : currentStep === 4
                      ? 'Revue finale & Signature'
                      : activeFieldInfo?.label || 'Sélectionnez un champ'}
                  </h3>
                  {activeFieldInfo?.arabic && currentStep > 0 && currentStep < 4 && (
                    <span className="fw-guide-arabic" lang="ar" dir="rtl">
                      {activeFieldInfo.arabic}
                    </span>
                  )}
                </div>

                <div className="fw-guide-content">
                  {currentStep === 0 ? (
                    <>
                      <div className="fw-guide-block">
                        <h4>Pourquoi cette distinction ?</h4>
                        <p>
                          Le formulaire RNE F005 traite 28 types de modifications distinctes. Les deux plus courantes concernent le siège social (adresse principale officielle de la personne morale) et la succursale (bureau ou atelier secondaire).
                        </p>
                      </div>
                      <div className="fw-guide-block">
                        <h4>Frais & Pièces associées</h4>
                        <p>{catalog.guidance.modifications}</p>
                      </div>
                    </>
                  ) : currentStep === 4 ? (
                    <>
                      <div className="fw-guide-block">
                        <h4>Vérification avant impression</h4>
                        <p>
                          Chaque case à cocher et chaque champ de texte ont été positionnés de manière conforme au document original RNE F005.
                        </p>
                      </div>
                      <div className="fw-guide-block">
                        <h4>Dépôt physique ou électronique</h4>
                        <p>{catalog.guidance.documents}</p>
                      </div>
                    </>
                  ) : activeFieldInfo ? (
                    <>
                      {/* Rôle & Pourquoi */}
                      <div className="fw-guide-block">
                        <h4>À quoi sert ce champ ?</h4>
                        <p>{activeFieldInfo.why || activeFieldInfo.help}</p>
                      </div>

                      {/* Où le trouver */}
                      <div className="fw-guide-block fw-doc-source">
                        <h4>Où le trouver sur vos documents ?</h4>
                        <div className="fw-doc-box">
                          <FileText size={16} />
                          <span>{activeFieldInfo.where}</span>
                        </div>
                      </div>

                      {/* Comment bien le remplir */}
                      {activeFieldInfo.how && (
                        <div className="fw-guide-block">
                          <h4>Comment bien le remplir</h4>
                          <p>{activeFieldInfo.how}</p>
                        </div>
                      )}

                      {/* Exemple type */}
                      <div className="fw-guide-block">
                        <h4>Exemple de format attendu</h4>
                        <div className="fw-example-pill" dir="auto">
                          {activeFieldInfo.example}
                        </div>
                      </div>

                      {/* Pièges à éviter */}
                      {activeFieldInfo.pitfalls && (
                        <div className="fw-guide-block fw-warning-box">
                          <div className="fw-warn-title">
                            <CircleAlert size={14} />
                            <strong>Pièges & Erreurs à éviter</strong>
                          </div>
                          <p>{activeFieldInfo.pitfalls}</p>
                        </div>
                      )}

                      {/* Référence légale */}
                      {activeFieldInfo.law_ref && (
                        <div className="fw-guide-block fw-law-ref">
                          <small>RÉFÉRENCE LÉGALE :</small>
                          <p>{activeFieldInfo.law_ref}</p>
                        </div>
                      )}
                    </>
                  ) : null}

                  {/* Official RNE link */}
                  <div className="fw-guide-footer">
                    <a
                      href={
                        currentStep === 0 || currentStep === 4
                          ? catalog.sources.procedures.url
                          : catalog.sources[activeFieldInfo?.source || 'form']?.url || catalog.sources.form.url
                      }
                      target="_blank"
                      rel="noreferrer"
                      className="fw-source-btn"
                    >
                      <BookOpen size={14} />
                      <span>Consulter la source RNE officielle</span>
                      <ArrowUpRight size={13} />
                    </a>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: Aperçu Direct du PDF */}
            {activeTab === 'preview' && (
              <div className="fw-preview-panel">
                <div className="fw-preview-header">
                  <div className="fw-preview-title">
                    <span className="fw-live-dot" />
                    <strong>Aperçu dynamique</strong>
                  </div>
                  <button
                    type="button"
                    className="fw-zoom-btn"
                    onClick={() => previewModalRef.current?.showModal()}
                    title="Agrandir en plein écran"
                  >
                    <Maximize2 size={15} />
                    <span>Agrandir</span>
                  </button>
                </div>

                {/* Visual Document Canvas */}
                <div
                  className="fw-paper-container"
                  onClick={() => previewModalRef.current?.showModal()}
                  role="button"
                  tabIndex={0}
                  aria-label="Cliquer pour agrandir le formulaire"
                >
                  <div className="fw-paper-shadow-sheet" />
                  <div className="fw-paper-sheet">
                    <img
                      src={`/api${baseEndpoint}/preview/${previewPage}?revision=${draft.revision}`}
                      alt={`Aperçu interactif RNE F005 page ${previewPage}`}
                      onError={(e) => {
                        e.currentTarget.alt = 'Aperçu en cours de génération…';
                      }}
                    />
                    <div className="fw-paper-stamp">
                      <span>RNE F005</span>
                      <small>BROUILLON EN TEMPS RÉEL</small>
                    </div>
                  </div>
                </div>

                {/* Page toggle buttons */}
                <div className="fw-page-controls">
                  <div className="fw-page-pills">
                    <button
                      type="button"
                      className={`fw-page-pill ${previewPage === 1 ? 'active' : ''}`}
                      onClick={() => setPreviewPage(1)}
                    >
                      Page 1 (Mentions)
                    </button>
                    <button
                      type="button"
                      className={`fw-page-pill ${previewPage === 2 ? 'active' : ''}`}
                      onClick={() => setPreviewPage(2)}
                    >
                      Page 2 (Date & Signatures)
                    </button>
                  </div>
                </div>
              </div>
            )}
          </aside>
        </div>
      )}

      {/* ── Hidden File Inputs for OCR (File & Camera) ── */}
      <input
        ref={fileInputRef}
        type="file"
        hidden
        accept="application/pdf,image/png,image/jpeg,image/webp"
        onChange={(e) => {
          if (e.target.files?.[0]) {
            void processDocumentFile(e.target.files[0], currentStep === 1 ? 'registry' : 'representative');
          }
        }}
      />
      <input
        ref={cameraInputRef}
        type="file"
        hidden
        accept="image/*"
        capture="environment"
        onChange={(e) => {
          if (e.target.files?.[0]) {
            void processDocumentFile(e.target.files[0], 'representative');
          }
        }}
      />

      {/* ── Modal Dialog: OCR Candidates Review ── */}
      <dialog ref={ocrDialogRef} className="fw-modal-dialog">
        <div className="fw-modal-header">
          <div className="fw-modal-title-group">
            <span className="fw-modal-icon">
              <ScanLine size={24} />
            </span>
            <div>
              <h3>Informations détectées sur votre document</h3>
              <p>Sélectionnez les mentions à reporter directement sur votre formulaire.</p>
            </div>
          </div>
          <button
            type="button"
            className="fw-modal-close-btn"
            onClick={() => ocrDialogRef.current?.close()}
            aria-label="Fermer"
          >
            <X size={20} />
          </button>
        </div>

        {ocrBatch && (
          <div className="fw-modal-body">
            <div className="fw-ocr-source-tag">
              <FileText size={16} />
              <span>{ocrBatch.name}</span>
              <span className="fw-ocr-method-pill">{ocrBatch.method}</span>
            </div>

            {ocrBatch.candidates.length > 0 ? (
              <div className="fw-candidates-list">
                {ocrBatch.candidates.map((cand, idx) => {
                  const isSelected = ocrSelections[cand.key] === idx;
                  const fieldDef = catalog?.fields.find((f) => f.key === cand.key);

                  return (
                    <label key={idx} className={`fw-candidate-item ${isSelected ? 'is-selected' : ''}`}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => {
                          setOcrSelections((prev) => {
                            const updated = { ...prev };
                            if (e.target.checked) updated[cand.key] = idx;
                            else delete updated[cand.key];
                            return updated;
                          });
                        }}
                      />
                      <div className="fw-candidate-text">
                        <span className="fw-cand-label">{fieldDef?.label || cand.key}</span>
                        <strong className="fw-cand-val" dir="auto">{cand.value}</strong>
                        <span className="fw-cand-evidence">Preuve visuelle : {cand.evidence}</span>
                      </div>
                    </label>
                  );
                })}
              </div>
            ) : (
              <div className="fw-ocr-empty-notice">
                <CircleAlert size={24} />
                <p>Aucune information n’a pu être certifiée avec certitude. Vous pouvez continuer la saisie manuelle en vous aidant des explications de chaque champ.</p>
              </div>
            )}

            <div className="fw-modal-actions">
              <button
                type="button"
                className="fw-btn primary fw-full"
                disabled={Object.keys(ocrSelections).length === 0}
                onClick={applyOcrChoices}
              >
                <CheckCheck size={16} />
                <span>Reporter les {Object.keys(ocrSelections).length} information(s) sélectionnée(s)</span>
              </button>
            </div>
          </div>
        )}
      </dialog>

      {/* ── Modal Dialog: High-Res Fullscreen PDF Preview ── */}
      <dialog ref={previewModalRef} className="fw-modal-dialog fw-preview-modal">
        <div className="fw-modal-header">
          <div className="fw-modal-title-group">
            <h3>Aperçu haute fidélité RNE F005</h3>
            <p>Visualisez le rendu réel des cases et pointillés avant finalisation.</p>
          </div>
          <button
            type="button"
            className="fw-modal-close-btn"
            onClick={() => previewModalRef.current?.close()}
            aria-label="Fermer"
          >
            <X size={20} />
          </button>
        </div>

        <div className="fw-modal-preview-controls">
          <button
            type="button"
            className={`fw-btn small ${previewPage === 1 ? 'primary' : 'secondary'}`}
            onClick={() => setPreviewPage(1)}
          >
            Page 1 (Société & Mentions)
          </button>
          <button
            type="button"
            className={`fw-btn small ${previewPage === 2 ? 'primary' : 'secondary'}`}
            onClick={() => setPreviewPage(2)}
          >
            Page 2 (Date & Signature)
          </button>
        </div>

        <div className="fw-modal-img-wrapper">
          <img
            src={`/api${baseEndpoint}/preview/${previewPage}?revision=${draft.revision}`}
            alt={`Formulaire complet page ${previewPage}`}
          />
        </div>
      </dialog>
    </div>
  );
}
