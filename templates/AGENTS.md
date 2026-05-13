# AGENTS - Projeto com Framework Partilhado PG

## Papel deste ficheiro
Este `AGENTS.md` e local ao projeto.
Serve para ligar o projeto ao framework partilhado e para registar overrides locais quando existirem.
E tambem a referencia local comum importada por `CLAUDE.md`, para manter Claude e Codex alinhados sem duplicar regras.

## Framework partilhado obrigatorio
Antes de concluir qualquer analise, recomendacao ou proposta tecnica, consultar obrigatoriamente:
1. `.pg_framework/templates/AGENTS_SHARED.md`
2. `PG_CONTEXT.md`
3. codigo do projeto
4. `vendor/odoo_src`
5. documentacao oficial do Odoo da versao ativa registada no `PG_CONTEXT.md`

Quando existirem, usar tambem:
- `PG_SCOPE_INTAKE.yaml`
- `.pg/PG_SCOPE_SYNC.json`
- `.pg/PG_PROJECT_STATUS_SYNC.json`

Se `.pg_framework` nao existir ou nao estiver acessivel, parar e pedir relink do framework partilhado antes de continuar.

## Overrides locais do projeto
- [Sem overrides locais neste momento]
