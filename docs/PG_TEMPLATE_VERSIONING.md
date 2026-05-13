# PG_TEMPLATE_VERSIONING

## Objetivo do documento
Este documento define uma convencao simples para versionar a evolucao do `_pg_template`.
O objetivo e permitir melhorias controladas sem perder coerencia, filosofia consultiva nem estabilidade de uso.

## Estado atual do template
- ultima release fechada: `_pg_template v2.9.0`
- linha operativa dominante: `PG AI Assistant V1 mirror redesign`
- leitura de prontidao atualmente registada: `READY WITH GUARDRAILS`

## Significado das versoes
- `v1.0`: primeira versao pronta para uso
- `v1.1`: correcoes pequenas e melhorias compativeis
- `v1.x`: melhorias incrementais sem quebra de filosofia
- `v2.0`: mudanca estrutural relevante no template
- `v2.x`: melhorias incrementais apos a mudanca estrutural do template

## Regras para evoluir o template
- manter a filosofia consultiva do template
- evitar alteracoes desnecessarias fora do objetivo da iteracao
- preservar coerencia entre templates, docs e configuracao
- documentar cada nova versao no `CHANGELOG.md`
- sempre que a evolucao mudar comportamento, linguagem ou estrutura de forma relevante, rever o impacto global antes de editar
- seguir a politica operacional definida em `docs/PG_RELEASE_POLICY.md` quando a baseline for promovida a release

## Quando criar nova versao menor
Criar nova versao menor quando houver:
- correcoes pequenas de texto ou alinhamento documental
- reforcos de clareza sem alterar filosofia do template
- melhorias incrementais compativeis com a estrutura atual
- nova documentacao de apoio que nao altera a base do sistema

## Quando criar nova versao maior
Criar nova versao maior quando houver:
- mudanca estrutural relevante na organizacao do template
- alteracao significativa da filosofia de decisao consultiva
- substituicao ou redefinicao de documentos centrais
- quebra de compatibilidade com a forma atual de uso do template

## Boas praticas antes de alterar o template
- analisar primeiro a estrutura atual do repositorio
- confirmar o objetivo exato da alteracao
- manter o escopo minimo necessario
- verificar coerencia com `README.md`, `templates/AGENTS.md` e restantes docs centrais
- evitar criar burocracia sem ganho real de uso

## Registo da release fechada e da linha operativa atual
- release fechada: `_pg_template v2.9.0`
- estado da release fechada: baseline historica validada da linha anterior
- linha operativa atual: `PG AI Assistant V1 mirror redesign`
- estado da linha operativa atual: piloto V1 fechado com `READY WITH GUARDRAILS`
- resumo da release fechada: framework consultivo Odoo com referencia local `.pg_framework/` ao metodo partilhado, `git clone` do source oficial do Odoo em `vendor/odoo_src`, wrapper local de `AGENTS.md`, intake estruturado do projeto, contratos validados de scope e status sync, troubleshooting operativo documentado, suite automatizada minima do addon Odoo 19, politica formal de release, smoke test semantico com higiene textual basica, documento operacional dedicado ao addon, `status sync` manual-only explicitado com indicador de stale state, bootstrap assistido, backlog formal da `v2.6` fechado, workflow GitHub para regenerar `PG_CONTEXT.md` a partir dos snapshots `.pg`, drafts factuais de status com aplicacao manual ao estado oficial, wizard de onboarding do addon para GitHub e projeto, fluxo consultivo guiado na task para discovery, fit-gap, recomendacao final e gate, dashboard operacional centralizado para projetos, runs e tasks com atencao, gate consultivo minimo antes de AI, classificacao final obrigatoria `standard -> modulo adicional -> Studio -> custom`, separacao explicita entre `approved_scope` e backlog operacional, trilho minimo de decisao consultiva na task, checklist executavel de primeira adocao real para brownfield, runbook A a Z com template de relatorio, draft heuristico de enriquecimento de scope na task para `Scope Summary`, `Acceptance Criteria` e `Scope Kind`, geracao e aplicacao assistida em massa desses drafts ao nivel do projeto, dashboard brownfield para consolidacao inicial de campos de scope em falta e casos `needs_review`, draft operacional reforcado para brownfield com sinais de backlog operacional, enriquecimento de scope em falta, drafts `needs_review` e runs com erro, pre-preenchimento consultivo assistido na task com sugestoes separadas da decisao final oficial, pipeline de sinais de chatter com filtro, validacao, grounding e explainability, apoio LLM controlado apenas para mensagens ambiguas do chatter com JSON estrito, validacao forte e fallback deterministico, e backlog da `v2.9` formalmente fechado como release `v2.9.0`
- resumo da linha operativa atual: o foco dominante passa a ser `onboarding + mirror sync + espelho continuo + PG_CONTEXT derivado do espelho`, com o repo do projeto tratado como base factual para consumo por agentes AI; o mecanismo tecnico fica validado e a frente seguinte passa a ser melhoria da qualidade do espelho
