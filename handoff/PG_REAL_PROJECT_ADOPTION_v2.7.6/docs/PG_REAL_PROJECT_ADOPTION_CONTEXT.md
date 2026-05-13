# PG_REAL_PROJECT_ADOPTION_CONTEXT

## Objetivo deste documento

Este documento resume o ponto de situacao da framework e do addon para que um colega sem contexto previo perceba rapidamente:
- o que ja foi construido
- o que ja foi validado
- o que o teste atual precisa realmente de provar

## O que esta a ser adotado

Baseline em avaliacao:
- `_pg_template v2.7.6`

Objetivo da adocao:
- testar a reproducao controlada da framework num projeto Parametro Global ja existente
- executar o teste numa branch de testes e numa base de staging
- validar se a framework consegue estruturar e automatizar o presente do projeto sem exigir reconstrucao total do historico

## O que a framework ja consegue fazer

### 1. Bootstrap e estrutura de projeto

- preparar um repositorio Odoo com estrutura base da framework
- criar `.pg_framework`
- criar `PG_CONTEXT.md`
- criar `PG_SCOPE_INTAKE.yaml`
- criar `.pg/PG_SCOPE_SYNC.json`
- criar `.pg/PG_PROJECT_STATUS_SYNC.json`
- preparar workflow GitHub para refresh automatico do `PG_CONTEXT.md`

### 2. Scope sync

- publicar o ambito do projeto para `.pg/PG_SCOPE_SYNC.json`
- suportar publish manual
- suportar `event-driven` por alteracao de task
- incluir apenas tasks com `Scope Track = approved_scope`
- refletir esse ambito no `PG_CONTEXT.md`

### 3. Status sync

- gerar draft factual de status
- aplicar draft ao estado do projeto
- publicar `.pg/PG_PROJECT_STATUS_SYNC.json`
- refletir esse estado no `PG_CONTEXT.md`

Regra importante:
- o `status sync` oficial e `manual-only`
- o draft pode ser automatico, o publish oficial nao

### 4. GitHub Action

- quando `.pg/PG_SCOPE_SYNC.json` ou `.pg/PG_PROJECT_STATUS_SYNC.json` mudam no remoto
- o workflow `PG Refresh Context` regenera automaticamente o `PG_CONTEXT.md`

### 5. Fluxo consultivo na task

- a task mostra `Guided Consultive Flow`
- a task exige classificacao final da recomendacao
- a task exige `Consultive Gate`
- o fluxo AI nao deve arrancar antes do gate
- a task regista `Consultive decision history`

### 6. Dashboard operacional

- mostra projetos com atencao de scope
- mostra projetos com atencao de status
- mostra tasks bloqueadas e tasks prontas para AI
- mostra runs falhadas

## O que ja foi validado no piloto `brodoo_v2`

Ja foi validado end-to-end:

- bootstrap do repositorio
- `scope sync` manual
- `scope sync` event-driven
- `status sync` com draft + publish manual
- GitHub Action de refresh do `PG_CONTEXT.md`
- encoding correto do `PG_CONTEXT.md`
- wizard de onboarding
- fluxo consultivo guiado na task
- classificacao obrigatoria da recomendacao
- `Consultive Gate`
- geracao de prompt AI depois do gate
- dashboard operacional
- smoke test final do repositorio sem erros

## O que o teste atual NAO precisa de provar de novo

Este teste nao e para reinventar a framework.
E para verificar se a adocao se reproduz num projeto real com o minimo de friccao.

Nao e necessario:
- redesenhar o fluxo
- rever backlog das versoes anteriores
- provar outra vez todos os detalhes do piloto se a reproducao ficar coerente
- reconstruir historico completo do projeto real

## O que o teste atual precisa de provar

O teste atual precisa de responder a estas perguntas:

1. o repositorio real consegue ser alinhado com a baseline?
2. o addon instala/upgrade sem erro na branch de testes?
3. o projeto real consegue publicar um primeiro `scope sync` util?
4. o projeto real consegue publicar um primeiro `status sync` util?
5. o `PG_CONTEXT.md` atualiza automaticamente no remoto?
6. uma task real consegue passar pelo fluxo consultivo?
7. o dashboard operacional faz sentido no estado real do projeto?
8. a consolidacao inicial brownfield e suficientemente rapida?

## O que significa sucesso

Sucesso nao significa "o projeto ficou perfeito".

Sucesso significa:
- a framework consegue estruturar o presente do projeto
- o PM consegue publicar ambito e status sem friccao excessiva
- o executor nao precisa de arqueologia extensa
- o processo e repetivel noutras adocoes

## O que significa falha relevante

Falha relevante significa:
- a adocao exige classificacao massiva de historico
- o executor nao consegue distinguir facilmente `approved_scope` de backlog
- a infraestrutura falha repetidamente
- a GitHub Action nao estabiliza
- o PM nao consegue operar o `status sync` manual

## Regra operacional principal para projeto antigo

Num projeto ja existente:
- nao tentar reconstruir o passado todo
- consolidar apenas o que esta em curso e e relevante agora

Em termos praticos:
- rever so tasks abertas, recentes ou claramente relevantes
- limitar a primeira ronda a `10-20` tasks
- marcar apenas o necessario para produzir snapshots uteis

## Como usar este handoff

1. ler este contexto
2. seguir o `runbook`
3. usar a `checklist`
4. preencher o `report template`

Se houver duvidas tecnicas detalhadas, consultar os documentos oficiais na raiz do repositorio `_pg_template`.
