import express from 'express';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { models as roster, overseer, OLLAMA_HOST } from './config/models.js';
import { ROLES, can, PERMISSIONS } from './config/roles.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();
app.use(express.json());
app.use(express.static(join(__dirname, 'public')));

const PORT = process.env.PORT || 8080;

// In-memory roster copy so the dashboard can toggle models at runtime.
const council = roster.map((m) => ({ ...m }));

// ---------------------------------------------------------------------------
// Ollama chat helper
// ---------------------------------------------------------------------------
async function askModel(ollamaModel, messages) {
  const res = await fetch(`${OLLAMA_HOST}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: ollamaModel, messages, stream: false })
  });
  if (!res.ok) {
    throw new Error(`Ollama ${ollamaModel} responded ${res.status}: ${await res.text()}`);
  }
  const data = await res.json();
  return data.message?.content?.trim() ?? '';
}

// ---------------------------------------------------------------------------
// Council debate: draft -> critique -> overseer synthesis. Streamed over SSE.
// ---------------------------------------------------------------------------
async function runCouncil(prompt, send) {
  const active = council.filter((m) => m.enabled);
  if (active.length === 0) throw new Error('No models enabled.');

  send('status', { phase: 'draft', message: `Dispatching to ${active.length} models` });

  // Round 1 — each model drafts an independent answer.
  const drafts = [];
  for (const m of active) {
    send('status', { phase: 'draft', model: m.id, message: `${m.label} thinking…` });
    const answer = await askModel(m.ollama, [
      { role: 'system', content: `You are ${m.label}, one member of a council answering a user request. Give your best, concise answer.` },
      { role: 'user', content: prompt }
    ]);
    drafts.push({ model: m, answer });
    send('draft', { model: m.id, label: m.label, color: m.color, answer });
  }

  // Round 2 — each model critiques the others' drafts.
  send('status', { phase: 'critique', message: 'Council cross-examination' });
  const critiques = [];
  for (const m of active) {
    const others = drafts
      .filter((d) => d.model.id !== m.id)
      .map((d) => `## ${d.model.label}\n${d.answer}`)
      .join('\n\n');
    const critique = await askModel(m.ollama, [
      { role: 'system', content: `You are ${m.label}. Critique the other council members' answers below. Point out errors and what is strongest. Be brief and specific.` },
      { role: 'user', content: `User request:\n${prompt}\n\nOther answers:\n${others}` }
    ]);
    critiques.push({ model: m, critique });
    send('critique', { model: m.id, label: m.label, color: m.color, critique });
  }

  // Round 3 — the overseer synthesizes a final answer.
  send('status', { phase: 'verdict', message: `${overseer.label} synthesizing verdict` });
  const dossier = drafts
    .map((d) => {
      const c = critiques.find((x) => x.model.id === d.model.id);
      return `### ${d.model.label}\nAnswer: ${d.answer}\nIts critique of others: ${c?.critique ?? '(none)'}`;
    })
    .join('\n\n');
  const verdict = await askModel(overseer.ollama, [
    { role: 'system', content: `You are the ${overseer.label}. Weigh the council's answers and critiques, then produce the single best final answer for the user. If the council proposes any action that would run commands, modify files, or touch the host system, DO NOT execute it — instead flag it clearly as "REQUIRES APPROVAL" and describe exactly what it would do, so a human can decide.` },
    { role: 'user', content: `User request:\n${prompt}\n\nCouncil dossier:\n${dossier}` }
  ]);
  send('verdict', { label: overseer.label, color: overseer.color, verdict });
  send('done', {});
}

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------
app.get('/api/models', (_req, res) => res.json({ council, overseer }));

app.post('/api/models/:id/toggle', (req, res) => {
  const m = council.find((x) => x.id === req.params.id);
  if (!m) return res.status(404).json({ error: 'unknown model' });
  m.enabled = Boolean(req.body?.enabled);
  res.json({ id: m.id, enabled: m.enabled });
});

app.get('/api/roles', (_req, res) => res.json(ROLES));

// Council dispatch — Server-Sent Events so the dashboard streams the debate.
app.get('/api/council', async (req, res) => {
  const prompt = String(req.query.prompt || '').trim();
  if (!prompt) return res.status(400).json({ error: 'prompt required' });

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive'
  });
  const send = (event, data) => res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);

  try {
    await runCouncil(prompt, send);
  } catch (err) {
    send('error', { message: err.message });
  } finally {
    res.end();
  }
});

// Any host-system action is proposed here and must be approved by an overseer.
// Nothing is executed automatically — this endpoint only records the request.
const pendingActions = [];
app.post('/api/actions/propose', (req, res) => {
  const action = { id: Date.now().toString(36), status: 'pending', ...req.body };
  pendingActions.push(action);
  res.json(action);
});
app.post('/api/actions/:id/decide', (req, res) => {
  const { role, decision } = req.body || {};
  if (!can(role, PERMISSIONS.APPROVE_ACTIONS)) {
    return res.status(403).json({ error: 'only the Safeguard Overseer can approve actions' });
  }
  const action = pendingActions.find((a) => a.id === req.params.id);
  if (!action) return res.status(404).json({ error: 'unknown action' });
  action.status = decision === 'approve' ? 'approved' : 'rejected';
  res.json(action);
});
app.get('/api/actions', (_req, res) => res.json(pendingActions));

app.listen(PORT, () => {
  console.log(`Majority AI council on http://localhost:${PORT}`);
  console.log(`Ollama expected at ${OLLAMA_HOST}`);
});
