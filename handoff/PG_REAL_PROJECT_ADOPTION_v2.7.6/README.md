# PG Real Project Adoption - Start Here

## O que e este bundle

Esta pasta existe apenas como camada de orientacao para a primeira execucao real da framework `_pg_template` e do addon `pg_brodoo` por um colega que nao acompanhou o desenvolvimento da solucao.

Nao e uma copia operativa do `_pg_template`.
Nao deve ser usada como source of truth tecnica.

Regra:
- `handoff/` = orientacao
- raiz do repositorio `_pg_template` = implementacao oficial

Baseline incluida neste handoff:
- `_pg_template v2.7.6`

Este bundle deve ser usado apenas em:
- branch de testes do repositorio do projeto
- branch de staging/teste no Odoo.sh
- base de dados de staging/teste

Nao usar este bundle diretamente em producao.

## Ordem de leitura obrigatoria

1. `docs/PG_REAL_PROJECT_ADOPTION_CONTEXT.md`
2. `docs/PG_REAL_PROJECT_ADOPTION_RUNBOOK.md`
3. `docs/PG_REAL_PROJECT_ADOPTION_CHECKLIST.md`
4. `docs/PG_REAL_PROJECT_ADOPTION_REPORT_TEMPLATE.md`

Se houver duvidas operacionais especificas, consultar os documentos oficiais na raiz do repositorio:
- `docs/PG_AI_DEV_ASSISTANT_OPERATIONS.md`
- `docs/PG_GITHUB_CONTEXT_AUTOMATION.md`
- `docs/PG_FRAMEWORK_ADDON_TEST_GUIDE.md`
- `docs/PG_TROUBLESHOOTING.md`

## O que o executor tem de fazer

O executor deve:
- preparar a branch de testes do repositorio
- alinhar o projeto com a baseline `v2.7.6`
- configurar GitHub, Odoo.sh e a base de staging
- executar onboarding, `scope sync`, `status sync`, fluxo consultivo e dashboard
- recolher evidencias
- devolver o resultado no relatorio

## O que o executor deve devolver no fim

1. checklist preenchida
2. relatorio preenchido
3. SHAs principais
4. screenshots principais
5. output do smoke test final
6. lista curta de problemas encontrados

## Conteudo incluido neste bundle

- `README.md`
- `docs/PG_REAL_PROJECT_ADOPTION_CONTEXT.md`
- `docs/PG_REAL_PROJECT_ADOPTION_RUNBOOK.md`
- `docs/PG_REAL_PROJECT_ADOPTION_CHECKLIST.md`
- `docs/PG_REAL_PROJECT_ADOPTION_REPORT_TEMPLATE.md`

## Nota importante

O executor deve usar sempre:
- scripts na raiz do repositorio `_pg_template`
- codigo do addon na raiz do repositorio `_pg_template`
- documentos oficiais na raiz do repositorio `_pg_template`

Esta pasta existe apenas para reduzir atrito de handoff humano.
