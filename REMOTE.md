# Acesso remoto do GeraSet

Aplicativo: https://geraset-celosmg1.fly.dev

O navegador autentica com usuario/senha pelo dialogo do navegador (HTTP Basic sobre HTTPS).
As credenciais iniciais ficam somente em `mt5_bridge/data/acesso-remoto.txt` neste PC.
O token do agente e diferente da senha web e do token do bridge local.

O Fly executa apenas Flask e o relay SQLite, com um volume persistente e uma unica Machine.
O agente Windows inicia conexoes HTTPS de saida e encaminha comandos autorizados ao bridge
em `127.0.0.1:8765`. Nenhuma porta do roteador precisa ser publicada. Relatorios e tarefas
continuam no PC; o relay limpa pedidos/respostas com mais de cinco minutos enquanto o agente consulta.
O estado de conexao usa um heartbeat de ate 15 segundos.

## Iniciar no PC de casa

Execute na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe iniciar-remoto.py
```

O comando reutiliza `iniciar-servicos.py` e o mesmo MT5 atual. Nao cria outra instalacao.
O bridge continua exigindo disponibilidade exclusiva do terminal durante seus testes:
uma instancia externa aberta pode retornar `TERMINAL_BUSY`. Nao encerra instancias externas.
O teste visual abre a janela no desktop do PC de casa; o site nao transmite essa janela.
Nao foi configurada inicializacao automatica ao ligar o Windows.

Logs locais: `mt5_bridge/data/remote-agent.log`. A configuracao e o journal do agente ficam
no mesmo diretorio, ignorado pelo Git e fora da imagem Docker. Para parar apenas a conexao,
encerre o PID registrado em `remote-agent-process.json` depois de conferir o processo.
Parar o agente nao cancela um teste ja entregue; retome a conexao para consultar ou cancelar.

A configuracao local pode conter `bootstrap_ip` com o IPv4 publico atribuido pelo Fly.
Ele e usado apenas se o DNS deste PC ainda nao conhece o dominio novo; o certificado TLS
continua validado pelo nome original. Assim que o DNS responde, o agente volta ao dominio.
Nao ha alteracao do arquivo hosts ou do DNS do Windows. Remova esse campo se o IP mudar.

## Queda de conexao

Cada pedido e reservado uma unica vez em uma transacao SQLite. O agente registra o UUID
antes de chamar o bridge e persiste a resposta antes de envia-la. Reenvios de respostas
sao idempotentes. Pedidos reservados nunca sao redistribuidos, mesmo apos reiniciar.
Isso privilegia evitar execucao duplicada: uma queda no instante da entrega pode deixar
o resultado do pedido incerto. Confira o historico antes de repetir um teste.
Pedidos ainda nao entregues expiram em 25 segundos; o Flask aguarda resposta por 30 segundos.
O historico e a fila real do MT5 permanecem no bridge, independentes desses prazos.

## Publicar alteracoes

```powershell
flyctl deploy --remote-only --ha=false
```

Mantenha uma Machine: o SQLite do relay fica no volume local dessa Machine. Nao aumente
replicas sem substituir o armazenamento e implementar identificacao de multiplos agentes.
Os segredos sao configurados com `flyctl secrets import`, nunca no Dockerfile ou no Git.
O Flask local continua disponivel; o modo remoto so e ativado por `GERASET_REMOTE=1`.
Rascunhos ficam no localStorage de cada navegador e origem. Exporte/importe o `.set` para
levar configuracoes do localhost para o endereco remoto ou para outro dispositivo.

## Validacao em 21/10/2026

- 56 testes Python e 74 testes JavaScript passaram.
- Aplicativo publicado em GRU com uma Machine e volume de 1 GB; health check aprovado.
- Login, status do MT5, historico, resultados, curvas e artefatos consultados pelo HTTPS publico.
- Relatorio XML remoto com 5.258 bytes conferido pelo SHA-256 do manifesto local.
- Novo backtest `a6335b2e-638c-41c6-868b-3f9a815dfd40`, enviado pelo Flask no Fly,
  executado no mesmo MT5: EURUSD/M5, 15 a 16/10/2026, entradas desativadas, concluido.
- Evidencia local em `mt5_bridge/data/fly-backtest-validation.json`.
- O DNS publico respondeu corretamente; o resolvedor deste PC ainda tinha resposta negativa
  do periodo anterior a criacao dos IPs. O agente conectou com o bootstrap TLS descrito acima.
