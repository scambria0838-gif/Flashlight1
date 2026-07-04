#!/usr/bin/env bash
set -euo pipefail

echo "Building Ollama agent models..."

ollama create local-supervisor -f modelfiles/supervisor.Modelfile
ollama create local-coder -f modelfiles/coder.Modelfile
ollama create local-unreal -f modelfiles/unreal.Modelfile
ollama create local-sysadmin-security -f modelfiles/sysadmin_security.Modelfile
ollama create local-data-analytics -f modelfiles/data_analytics.Modelfile
ollama create local-web-seo -f modelfiles/web_seo.Modelfile
ollama create local-finance-crypto -f modelfiles/finance_crypto.Modelfile
ollama create local-research -f modelfiles/research.Modelfile
ollama create local-media-transcription -f modelfiles/media_transcription.Modelfile
ollama create local-devops-cloud -f modelfiles/devops_cloud.Modelfile
ollama create local-general-assistant -f modelfiles/general_assistant.Modelfile

echo "Done."
ollama list
