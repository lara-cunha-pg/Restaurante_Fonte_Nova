# PG_CONTENT_HYGIENE

## Objetivo
Este documento define regras simples para manter coerencia semantica e higiene textual nos artefactos factuais da framework.

Nao substitui os contratos tecnicos dos snapshots.
Serve para reduzir ruido operacional em:
- `PG_CONTEXT.md`
- `.pg/PG_SCOPE_SYNC.json`
- `.pg/PG_PROJECT_STATUS_SYNC.json`

## Checklist curta antes de publicar

Antes de publicar `scope sync` ou `status sync`, confirmar:

- nao existem textos com `Ã`, `Â`, `â€` ou `�`
- nao existem placeholders como `[PREENCHER]` ou `[PONTO POR VALIDAR]` em campos que ja deviam estar fechados
- `risks`, `blockers`, `next_steps` e `pending_decisions` nao repetem a mesma frase
- `next_steps` descreve acoes futuras e nao riscos
- `blockers` descreve impedimentos atuais e nao decisoes pendentes
- `pending_decisions` descreve escolhas ainda por tomar e nao tarefas executivas
- o `status` publicado nao contem texto de workflow como `Review this draft`, `Apply the draft` ou `Publish a fresh manual status snapshot`
- depois de um publish real de status, o snapshot nao pode afirmar `No status snapshot has been published yet` nem `Latest status publication status: Never`

## Significado operacional dos campos de status

### `milestones`
- entregas ou marcos ja atingidos ou claramente planeados
- devem ser factuais e curtos

### `blockers`
- impedimentos atuais que travam trabalho
- se o problema ja nao bloqueia, deve sair daqui

### `risks`
- possibilidades de impacto negativo futuro
- um risco nao e um proximo passo

### `next_steps`
- acoes concretas a executar a seguir
- devem preferir verbos operacionais como `validar`, `publicar`, `rever`, `decidir`, `atualizar`

### `pending_decisions`
- escolhas de governance, produto ou arquitetura ainda em aberto
- nao devem ser tarefas executivas

## Regras praticas para evitar incoerencia

- se a mesma frase aparece em `risks` e `next_steps`, provavelmente um dos campos esta mal classificado
- se a mesma frase aparece em `blockers` e `next_steps`, falta distinguir problema atual de acao corretiva
- se `next_steps` comeca por `Risco` ou `Bloqueio`, rever o texto
- se `pending_decisions` comeca por verbos de execucao tecnica, rever o texto

## Encoding e line endings

Na baseline atual:
- os scripts que escrevem `markdown`, `yaml` e `json` usam UTF-8 explicito via `scripts/pg_file_io_common.ps1`
- `.editorconfig` e `.gitattributes` devem permanecer sincronizados nos repositorios bootstrapados

Se aparecer mojibake:
1. corrigir o conteudo na origem
2. republicar o snapshot no Odoo
3. voltar a correr `pg_refresh_pg_context.ps1`

## Como corrigir conteudo mal preenchido

### Caso: `risks` e `next_steps` com o mesmo texto
Correcao:
- manter em `risks` a formulacao do risco
- mover para `next_steps` a acao correspondente

Exemplo:
- `risks`: `Risco de divergencia entre _pg_template e repositorios bootstrapados`
- `next_steps`: `Sincronizar os assets partilhados e validar a baseline no repositorio piloto`

### Caso: placeholders apos publish real
Correcao:
- preencher no Odoo o campo em falta
- publicar novo snapshot
- nao editar manualmente o snapshot no Git, salvo excecao controlada

### Caso: texto corrompido no contexto
Correcao:
- confirmar que a repo tem `.editorconfig` e `.gitattributes`
- usar os scripts atuais do `_pg_template`
- regenerar o `PG_CONTEXT.md` a partir dos snapshots

## Ligacao com o smoke test

O `scripts/pg_smoke_test_repo.ps1` passou a sinalizar:
- mojibake
- placeholders em snapshots publicados
- duplicacoes semanticas dentro de listas
- sobreposicao suspeita entre `blockers`, `risks`, `next_steps` e `pending_decisions`

Esses warnings nao substituem julgamento consultivo, mas ajudam a apanhar ruido antes de tratar o snapshot como evidência limpa.
