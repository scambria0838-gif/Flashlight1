// Council roster. Start lean — 3 to 4 general local models via Ollama — and add
// more once it works. `enabled` is the on/off switch shown in the dashboard.
//
// These are standard instruction-tuned models. Pull them first, e.g.:
//   ollama pull mistral:7b
//   ollama pull openhermes:7b
//   ollama pull llama3.1:8b
//   ollama pull phi3:mini

export const OLLAMA_HOST = process.env.OLLAMA_HOST || 'http://127.0.0.1:11434';

export const models = [
  { id: 'mistral',    label: 'Mistral 7B',   ollama: 'mistral:7b',    color: '#22d3ee', enabled: true,  role: 'reasoning' },
  { id: 'openhermes', label: 'OpenHermes 7B', ollama: 'openhermes:7b', color: '#a78bfa', enabled: true,  role: 'tool-use' },
  { id: 'llama31',    label: 'Llama 3.1 8B', ollama: 'llama3.1:8b',   color: '#34d399', enabled: true,  role: 'debate' },
  { id: 'phi3',       label: 'Phi-3 Mini',   ollama: 'phi3:mini',     color: '#fbbf24', enabled: false, role: 'triage' }
];

// The overseer synthesizes the final answer from the council's debate. It is a
// council member, not a gate that can be removed. Point this at whichever local
// model you trust most for judgement.
export const overseer = {
  id: 'overseer',
  label: 'Safeguard Overseer',
  ollama: process.env.OVERSEER_MODEL || 'llama3.1:8b',
  color: '#f472b6'
};
