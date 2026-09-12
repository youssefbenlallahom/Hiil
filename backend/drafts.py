"""Printable preparation sheet. This is deliberately not an official RNE form."""
from html import escape

from backend.rules import prepared_fields


def render_draft(case):
    states = {'confirmed': 'Déclaré / confirmé par l’entreprise', 'extracted': 'À relire avec la pièce', 'missing': 'Non renseigné', 'conflict': 'Écart à résoudre'}
    rows = []
    for field in prepared_fields(case):
        references = '<br>'.join(f'{escape(e["document_name"])} · p. {e["page"]} : {escape(e["evidence"])}' for e in field['evidence'])
        rows.append(f'<tr><th>{escape(field["label"])}</th><td>{escape(field["value"]) or "—"}<small>{states[field["state"]]}</small></td><td>{references or "Déclaration sans passage source"}</td></tr>')
    correction = case.get('correction')
    observations = ''
    if correction:
        observations = f'<h2>Échange avec l’agent</h2><p>{escape(correction["note"])}</p><p>Réponse : {escape(correction.get("response") or "En attente")}</p>'
    pieces = ''.join(f'<li>{escape(d["name"])} — {"démonstration" if d["sample"] else "pièce fournie"}</li>' for d in case['documents'])
    return f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Brouillon — {escape(case['id'])}</title><style>
body{{font:15px/1.6 system-ui,sans-serif;color:#172c35;max-width:1100px;margin:40px auto;padding:24px}}h1{{color:#075d65;line-height:1.3}}.notice{{padding:18px;background:#fff6e5;border:1px solid #e4ce9f}}table{{border-collapse:collapse;width:100%;margin:24px 0;table-layout:fixed}}th,td{{text-align:left;vertical-align:top;padding:14px;border:1px solid #dce5df;overflow-wrap:anywhere}}th{{width:20%;background:#f3f7f5}}small{{display:block;color:#64766c;margin-top:8px}}td:last-child{{font-size:12px}}@media print{{body{{margin:0;padding:0;font-size:11px}}tr{{break-inside:avoid}}@page{{size:A4 landscape;margin:14mm}}}}
</style></head><body><small>DOSSIER TN · FICHE DE PRÉPARATION</small><h1>Changement d’adresse</h1><p>{escape(case['company'])} · {escape(case['id'])}</p>
<p class="notice"><strong>BROUILLON — Aucun dépôt officiel.</strong> Fiche de préparation à relire ; elle ne remplace pas le formulaire RNE F 005. Les informations déclarées, les écarts et les champs manquants restent visibles. Complétude réglementaire et authenticité non vérifiées.</p>
<table><thead><tr><th>Information</th><td>Valeur retenue</td><td>Passages sources</td></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>Pièces du dossier</h2><ul>{pieces or '<li>Aucune pièce</li>'}</ul>{observations}<p>Mis à jour : {escape(case['updated_at'])}</p></body></html>'''
