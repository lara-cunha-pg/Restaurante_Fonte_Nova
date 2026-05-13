# PG_REAL_PROJECT_ADOPTION_REPORT_TEMPLATE

## Identificacao do teste

- Projeto:
- Repositorio GitHub:
- Branch de testes:
- Projeto Odoo.sh:
- Base de dados de staging:
- Data de execucao:
- Executor:
- Baseline do template:
- Versao do addon:

## Resultado executivo

- Resultado final:
  - [ ] GO
  - [ ] GO com reservas
  - [ ] NO-GO

- Resumo curto:

## Evidencia tecnica recolhida

### Git / repositorio

- SHA de partida:
- SHA do commit de adocao da baseline:
- SHA do primeiro commit de `scope sync`:
- SHA do primeiro commit de `status sync`:
- SHA do primeiro commit automatico de refresh do `PG_CONTEXT.md`:

### Odoo.sh

- Build da branch de testes:
  - [ ] Success
  - [ ] Failed
- Upgrade do addon:
  - [ ] Success
  - [ ] Failed

### Scope sync

- Primeiro run de scope:
  - [ ] done
  - [ ] skipped
  - [ ] error
- GitHub Action `PG Refresh Context` apos scope:
  - [ ] Success
  - [ ] Failed

### Status sync

- Primeiro run de status:
  - [ ] done
  - [ ] skipped
  - [ ] error
- GitHub Action `PG Refresh Context` apos status:
  - [ ] Success
  - [ ] Failed

### Fluxo consultivo

- `Guided Consultive Flow`:
  - [ ] validado
  - [ ] nao validado
- `Consultive Gate`:
  - [ ] ready
  - [ ] nao ready
- `Prompt Generated`:
  - [ ] sim
  - [ ] nao

### Dashboard

- `PG Operational Dashboard`:
  - [ ] coerente
  - [ ] incoerente

### Smoke test final

- Resultado:
  - [ ] sem erros
  - [ ] com erros

- Output relevante:

## Problemas encontrados

| ID | Tipo | Gravidade | Descricao | Evidencia | Bloqueia adocao? |
|---|---|---|---|---|---|
| 1 | bug / UX / setup / processo | baixa / media / alta | | | sim / nao |

## Atritos operacionais observados

- O que foi confuso para o executor:
- O que exigiu apoio externo:
- O que demorou mais do que o esperado:
- O que parece justificar novo automatismo:

## Tempo gasto

- Preparacao tecnica:
- Odoo.sh e upgrade:
- Consolidacao brownfield:
- Primeiro ciclo factual:
- Primeiro ciclo consultivo:
- Dashboard e fecho:
- Tempo total:

## Avaliacao brownfield

- Numero aproximado de tasks revistas:
- Numero aproximado de tasks marcadas como `approved_scope`:
- Foi necessario reconstruir historico?
  - [ ] nao
  - [ ] pouco
  - [ ] sim, demasiado

- O processo pareceu:
  - [ ] rapido o suficiente
  - [ ] aceitavel com algum atrito
  - [ ] demasiado lento

## Recomendacao final

- Recomendo adotar esta baseline no proximo projeto real?
  - [ ] sim
  - [ ] sim, com reservas
  - [ ] nao

- Justificacao:

## Anexos esperados

- screenshots do onboarding
- screenshots das runs de scope e status
- screenshots da GitHub Action
- screenshots do fluxo consultivo
- screenshot do dashboard
- output do smoke test
