# PG_SHARED_VS_LOCAL_MODEL

Este documento clarifica o que deve ser partilhado entre projetos e o que deve permanecer local a cada repositorio.

## Partilhado no framework

Permanecem no `_pg_template`:

- regras partilhadas do agente em `templates/AGENTS_SHARED.md`
- prompts e docs metodologicos em `docs/`
- scripts de bootstrap e automacao em `scripts/`
- configuracao base em `config.toml`
- patterns consultivos
- learnings reutilizaveis curados e desidentificados
- versionamento e changelog do framework

## Local a cada projeto

Permanecem no repositorio do projeto:

- `AGENTS.md`
- `CLAUDE.md`
- `.pg_framework/`
- `PG_CONTEXT.md`
- `PG_SCOPE_INTAKE.yaml`
- `.pg/PG_PROJECT_STATUS_SYNC.json`
- `vendor/odoo_src`
- codigo, configuracao e historico especifico do projeto

## Regra simples

- o metodo e partilhado
- o contexto e local
- a aprendizagem transversal sobe ao framework apenas por curadoria explicita

## Implicacao pratica

`PG_CONTEXT.md` nao deve ser usado como memoria global de multiplos projetos.
`PG_PROJECT_LEARNINGS.md` tambem nao deve receber automaticamente texto bruto de projeto.
`AGENTS.md` no projeto passa a ser um wrapper leve, enquanto as regras partilhadas vivem em `.pg_framework/templates/AGENTS_SHARED.md`.
`CLAUDE.md` deve continuar a ser apenas o wrapper de compatibilidade do Claude Code, importando `AGENTS.md` e as regras partilhadas para manter paridade com Codex.
