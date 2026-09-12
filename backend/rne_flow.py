"""One event per HTTP turn; the case store persists each completed Flow atomically.

There is no blocking console input, background wait or second copy of identity data
in CrewAI's default persistence database. A new event hydrates the saved typed state.
"""
import asyncio
from typing import ClassVar
from uuid import uuid4, uuid5, NAMESPACE_URL

# Import before crewai so tracing is disabled before framework initialization.
from backend import rne_agent, store
from crewai.flow.flow import Flow, start, listen, router, or_
from backend.rne_knowledge import LABELS, REFERENCES, blockers, field_error, stage
from backend.rne_models import Evidence, Message, RneRequest, RneState, Value


def load_state(case):
    if case.get('rne'):
        return RneState.model_validate(case['rne'])
    state = RneState(id=str(uuid5(NAMESPACE_URL, 'hiil:rene:' + case['id'])))
    state.messages.append(Message(id='welcome', role='assistant', at=store.now(), text='Bonjour ! Je vous accompagne pour préparer votre déclaration RNE F005. Quel changement souhaitez-vous déclarer pour votre société ? Vous pouvez me l’expliquer avec vos mots.', source_ids=['pilot-scope']))
    return state


def view(state):
    return {**state.model_dump(exclude={'processed_requests'}), 'stage': stage(state),
            'blockers': blockers(state), 'labels': LABELS, 'references': REFERENCES,
            'field_errors': {k: field_error(k, v.value) for k, v in state.values.items() if field_error(k, v.value)}}


def invalidate(state):
    state.pdf_revision = None


def set_value(state, key, value, evidence):
    if key in ('representative_name', 'representative_id') and state.values.get('same_person', Value(value='no')).value == 'yes':
        raise ValueError('Le déclarant et le représentant sont liés. Modifiez le déclarant, ou indiquez qu’il s’agit de deux personnes différentes.')
    if key == 'same_person' and value == 'no' and state.values.get(key, Value(value='no')).value == 'yes':
        state.values.pop('representative_name', None)
        state.values.pop('representative_id', None)
    state.values[key] = Value(value=value.strip(), evidence=evidence)
    if state.values.get('same_person', Value(value='no')).value == 'yes':
        for source, target in [('declarant_name', 'representative_name'), ('declarant_id', 'representative_id')]:
            if source in state.values:
                state.values[target] = Value(value=state.values[source].value,
                    evidence=state.values[source].evidence + state.values['same_person'].evidence)
    invalidate(state)


class DeclarationFlow(Flow[RneState]):
    # CrewAI 1.15 creates a general-purpose memory by default. This flow uses only
    # its case-scoped typed state, never embeddings or a cross-case memory store.
    _skip_auto_memory: ClassVar[bool] = True

    def __init__(self, snapshot: RneState, request: RneRequest, case):
        super().__init__(initial_state=snapshot.model_copy(deep=True), tracing=False, suppress_flow_events=True, max_method_calls=8)
        self.request = request
        self.case = case

    def add_message(self, role, text, sources=None):
        msg = Message(id=str(uuid4()), role=role, text=text, at=store.now(), source_ids=sources or [])
        self.state.messages.append(msg)
        return msg

    @start()
    def begin(self):
        return self.request.action

    @router(begin)
    def dispatch(self, action):
        return action

    @listen('message')
    async def converse(self):
        message = self.request.message.strip()
        if not message:
            raise ValueError('Écrivez votre demande.')
        proposal = await rne_agent.propose(self.state, message)
        msg = self.add_message('user', message)
        # Handle the role before any name/identity updates, independent of model order.
        for update in sorted(proposal.updates, key=lambda u: u.key != 'same_person'):
            if update.key == 'same_person' and update.value not in ('yes', 'no'):
                raise ValueError('La relation entre déclarant et représentant doit être précisée.')
            set_value(self.state, update.key, update.value, [Evidence(origin='user', reference_id=msg.id, quote=update.quote)])
        if proposal.modification:
            self.state.modification = proposal.modification
            self.state.modification_confirmed = False
            self.state.reason = proposal.reason
            self.state.candidates = []
            invalidate(self.state)
        elif proposal.candidates:
            # An unresolved new intention must invalidate a formerly prepared form.
            self.state.modification = None
            self.state.modification_confirmed = False
            self.state.candidates = list(dict.fromkeys(proposal.candidates))
            self.state.reason = proposal.reason
            invalidate(self.state)
        self.state.pending_question = proposal.reply
        self.add_message('assistant', proposal.reply, proposal.source_ids)

    @listen('edit')
    def edit_field(self):
        key, value = self.request.key, self.request.value.strip()
        if not key:
            raise ValueError('Choisissez une rubrique.')
        if error := field_error(key, value):
            raise ValueError(error)
        label_value = {'yes': 'Oui', 'no': 'Non'}.get(value, value) if key == 'same_person' else value
        msg = self.add_message('user', LABELS[key] + ' : ' + label_value)
        set_value(self.state, key, value, [Evidence(origin='user', reference_id=msg.id, quote=msg.text)])
        self.add_message('assistant', 'C’est enregistré dans le récapitulatif. Vous pourrez vérifier cette information avant de confirmer le formulaire.')

    @listen('select_modification')
    def select_intent(self):
        if not self.request.modification:
            raise ValueError('Choisissez une modification.')
        self.state.modification = self.request.modification
        self.state.modification_confirmed = False
        self.state.candidates = []
        self.state.reason = 'Choix explicite de l’utilisateur dans les rubriques du formulaire.'
        invalidate(self.state)
        label = {'seat_address': 'Adresse du siège social', 'branch_address': 'Adresse d’une succursale', 'other': 'Autre ou plusieurs modifications'}[self.request.modification]
        self.add_message('user', 'Je souhaite déclarer : ' + label + '.')
        if self.request.modification == 'seat_address':
            reply = 'D’accord, nous préparons le changement d’adresse du siège social. '
            reply += 'Joignez la CIN du déclarant avec le bouton « Ajouter la CIN » pour proposer son identité.' if not self.state.cin_document_id else 'La CIN est déjà jointe. Complétons les rubriques manquantes dans le récapitulatif.'
        else:
            reply = 'Le formulaire prévoit ce type de demande, mais ce premier parcours prépare seulement le changement d’adresse du siège social. Je conserve votre choix ; la génération est suspendue pour éviter un formulaire inadapté.'
        self.add_message('assistant', reply, ['f005-choices', 'pilot-scope'])

    @listen('extract_cin')
    async def extract_identity(self):
        doc = next((d for d in self.case['documents'] if d['id'] == self.state.cin_document_id), None)
        if not doc:
            raise ValueError('Joignez d’abord la CIN du déclarant.')
        fields, pages, method = await rne_agent.extract_cin(store.document_path(doc).read_bytes(), doc['content_type'], doc['pages'])
        def evidence(f):
            return Evidence(origin='document', reference_id=doc['id'], page=f.page, quote=f.evidence)
        found = {f.key: f for f in fields}
        # Never replace a human correction by an automatic extraction on retry.
        if 'first_name' in found and 'last_name' in found and 'declarant_name' not in self.state.values:
            names = [found['first_name'], found['last_name']]
            set_value(self.state, 'declarant_name', ' '.join(f.value for f in names), [evidence(f) for f in names])
        if 'cin_number' in found and 'declarant_id' not in self.state.values:
            set_value(self.state, 'declarant_id', found['cin_number'].value, [evidence(found['cin_number'])])
        self.state.cin_status = 'extracted' if len(found) == 3 else 'needs_review'
        doc['pages'], doc['text'], doc['method'] = pages, '\n\n'.join(p['text'] for p in pages), method
        doc['identity_fields'] = [f.model_dump() for f in fields]
        self.add_message('assistant', 'La lecture de la CIN est terminée. Les valeurs lisibles sont proposées à droite avec leurs passages sources ; vérifiez-les sur l’original. ' + ('Les noms et le numéro restent à confirmer.' if len(found) == 3 else 'Certaines informations restent illisibles ou non reconnues : vous pouvez les recopier depuis l’original.'), ['pilot-scope'])
        invalidate(self.state)

    @listen('confirm')
    def confirm_fields(self):
        trial = self.state.model_copy(deep=True)
        trial.modification_confirmed = True
        for fact in trial.values.values():
            fact.confirmed = True
        if problems := blockers(trial):
            raise ValueError(' '.join(problems))
        self.state.modification_confirmed = True
        for fact in self.state.values.values():
            fact.confirmed = True
        invalidate(self.state)
        self.add_message('user', 'J’ai relu les rubriques et la nature de la modification. Je confirme les informations du récapitulatif.')
        self.add_message('assistant', 'Votre confirmation est enregistrée. Vous pouvez maintenant préparer le PDF F005. La date et la signature resteront à compléter par le déclarant.', ['f005-instructions'])

    @listen('prepare')
    async def prepare_pdf(self):
        if problems := blockers(self.state):
            raise ValueError(' '.join(problems))
        # Only this confirmed branch can invoke the filling tool. No LLM-generated coordinates.
        await asyncio.to_thread(rne_agent.FillRneTool()._run, self.state.model_dump())
        self.state.pdf_revision = self.state.revision + 1
        self.add_message('assistant', 'Le formulaire F005 est prêt à être relu et téléchargé. La case « changement d’adresse du siège social » est cochée. La date et la signature sont laissées libres ; aucun dépôt n’a été effectué.', ['f005-fields', 'f005-instructions'])

    @listen(or_(converse, edit_field, select_intent, extract_identity, confirm_fields, prepare_pdf))
    def finish(self):
        old_revision = self.state.revision
        self.state.revision += 1
        # A question that changes no fact keeps the prepared snapshot current.
        if self.state.pdf_revision == old_revision:
            self.state.pdf_revision = self.state.revision
        self.state.stage = stage(self.state)
        self.state.processed_requests = (self.state.processed_requests + [self.request.request_id])[-100:]
        return self.state
