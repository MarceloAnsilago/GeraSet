# Arquitetura do Bridge MT5

## Fluxo local

```text
Navegador → Flask (sessão + CSRF) → cliente HTTP (token no servidor)
          → FastAPI em loopback → SQLite/fila → worker único
          → INI + set de execução → terminal dedicado → relatórios
          → normalização + artefatos → API → Flask → navegador
```

O navegador reutiliza o serializador atual de `.set`; o Flask não importa MT5 nem executa processos. `flask_version/bridge_client.py` define uma interface de transporte independente. `mt5_bridge/api.py` valida pedidos; `manager.py` governa a fila; `runner.py` controla apenas processos de sua propriedade; `reports.py` interpreta arquivos. O EA de produção não foi alterado para esta integração.

Estados persistidos: `queued → preparing → running → collecting_results → completed`; qualquer etapa ativa pode falhar ou ser cancelada. Falha não é conclusão com resultado vazio. UUID, configuração JSON, hashes, horários, erros, progresso e manifesto ficam no SQLite; arquivos ficam por UUID. A implementação v1 possui uma instalação autorizada (`default`), com exclusão mútua por arquivo e processo. Não pretende ser um escalonador distribuído.

O serviço aceita somente o contrato dos inputs atuais e valores estruturados de teste. Caminhos, executável, instalação e EA são escolhas do operador. Token Bearer, loopback, limite de corpo, taxa e download por manifesto reduzem a superfície exposta. CSRF protege as mutações do proxy Flask. O token nunca participa do estado do setup ou do `.set`.

## Flask hospedado futuramente

Não publicar a porta 8765 na internet. A evolução recomendada é um agente Windows que **inicia conexão de saída** HTTPS com um relay autenticado. O Flask hospedado cria uma tarefa no relay; o agente busca tarefas destinadas ao seu `agent_id`, executa pelo mesmo Manager e publica estado/artefatos. O navegador continua falando apenas com Flask.

Antes dessa evolução, implementar:

1. Identidade e segredo por agente e locatário; autorização explícita de instalações, símbolos e quotas. Não reutilizar o token local como credencial geral do relay.
2. Protocolo versionado com UUID/idempotency key, hash do payload e artefatos, assinatura/autenticação e expiração de pedidos.
3. Reserva com lease/heartbeat, confirmação de recebimento, retries com backoff e deduplicação persistida no agente. Uma reentrega não pode repetir uma otimização concluída.
4. Cancelamento versionado e reconhecido pelo agente; tempo real de aceitação e término separados. Desconexão não equivale a cancelamento.
5. Upload de artefatos com tamanho, checksum, retenção, autorização de download e isolamento entre usuários. Não transportar caminhos locais ou senhas do MT5.
6. Estados de conexão e progresso separados: um agente offline mantém o último estado observado, sem inventar conclusão ou percentual.

Essa infraestrutura não faz parte da versão local. A interface de transporte do cliente Flask permite substituí-la por um cliente relay; Manager e Runner continuam locais. É necessário projetar o protocolo antes de implementar distribuição, não adaptar o endpoint local com exposição de porta.

## Limites de validação

Um `ready=true` confirma caminhos e ausência de processo concorrente. Não comprova conta autorizada, licença do EA, símbolo negociável, histórico ou saída válida do testador. Uma tarefa só é concluída após relatório íntegro e reconhecido. Otimização exige passes no XML; forward exige relatório próprio. Métricas não presentes permanecem nulas.

Detalhes de operação, API e verificação: [README](mt5_bridge/README.md). Evidências e pendências: [VALIDATION](mt5_bridge/VALIDATION.md).
