# PG_TEMPLATE_USAGE_GUIDE

## Objetivo do guia
Este documento descreve como utilizar o `_pg_template` no dia a dia de projetos Odoo.
O objetivo e ajudar a aplicar o template de forma consistente, desde o bootstrap inicial ate a resposta consultiva final.

## Principios fundamentais do template
O template foi desenhado para forcar disciplina consultiva antes de desenvolvimento.
Antes de qualquer recomendacao relevante, a decisao deve ser sempre validada contra:
- `PG_CONTEXT.md`
- codigo do projeto
- `vendor/odoo_src`
- documentacao oficial da versao ativa

O template nao existe para acelerar customizacao.
Existe para reduzir suposicoes, melhorar a qualidade consultiva e evitar desenvolvimento desnecessario.

## Fluxo de utilizacao do template num projeto

### 1. Bootstrap do repositorio
Aplicar o template ao repositorio com `scripts/pg_bootstrap_repo.ps1`.
Isto copia os ficheiros base do template para o projeto e prepara a estrutura minima de trabalho.
O bootstrap passa tambem a criar `PG_SCOPE_INTAKE.yaml` e `.pg/PG_PROJECT_STATUS_SYNC.json`.
O bootstrap passa tambem a criar `.pg/PG_SCOPE_SYNC.json`.
O bootstrap passa tambem a criar `.pg_framework/`, que e a referencia local ao framework partilhado.

### 2. Checkout do source Odoo
Preparar o source Odoo com `scripts/pg_clone_odoo_source.cmd`.
Isto cria `vendor/odoo_src/community` e, quando aplicavel, `vendor/odoo_src/enterprise`, permitindo consultar diretamente o source da versao ativa sem instalar o ERP localmente.

Fluxo recomendado:
- `.\scripts\pg_clone_odoo_source.cmd NOME_DO_REPO 19.0 community`
- `.\scripts\pg_clone_odoo_source.cmd NOME_DO_REPO 19.0 enterprise`

O script legado `scripts/pg_link_odoo_core.cmd` continua disponivel apenas como compatibilidade.

### Discovery antes do PG_CONTEXT
Se o pedido ainda estiver incompleto, ambiguo ou pouco maduro para decisao, usar primeiro `docs/PG_DISCOVERY_PROMPT.md`.
Este ficheiro ajuda a qualificar o pedido, pedir evidencia e confirmar se ja existe base suficiente para preencher ou atualizar o `PG_CONTEXT.md`.

### 3. Preenchimento inicial do contexto
Preencher primeiro o `PG_SCOPE_INTAKE.yaml` e depois materializar o `PG_CONTEXT.md`.

Fluxo recomendado:
- inicializar ou rever `PG_SCOPE_INTAKE.yaml`
- correr `scripts/pg_build_pg_context.ps1`
- confirmar no `PG_CONTEXT.md` a informacao inicial do projeto

O intake deve concentrar informacao como:
- versao do Odoo
- edicao
- ambiente
- restricoes contratuais
- pedido funcional atual
- processo atual
- problema e impacto no negocio

### 4. Inicio de sessao com o prompt base
Comecar a interacao com o agente usando `docs/PROMPT_INICIAL.md`.
Este ficheiro alinha o comportamento base do agente com as regras do template.
No repositorio do projeto, o `AGENTS.md` local passa a funcionar como wrapper para `.pg_framework/templates/AGENTS_SHARED.md`.
Para Claude Code, o `CLAUDE.md` local importa `AGENTS.md` e o mesmo `AGENTS_SHARED.md`, mantendo paridade com Codex.

### 5. Analise de requisitos
Para cada requisito, analisar primeiro o contexto funcional, o processo atual, o problema real e a evidencia disponivel.
Se faltar contexto critico, pedir clarificacao antes de fechar recomendacao.

### 6. Fit-gap framing antes da decisao
Quando o discovery ja estiver claro, mas ainda for cedo para fechar recomendacao, usar `docs/PG_FIT_GAP_FRAMING_PROMPT.md`.
Esta etapa ajuda a mapear rapidamente o encaixe no Odoo, distinguir fit de gap e perceber se ja existe base para passar a decisao consultiva.

### 7. Uso do decision engine quando necessario
Quando a analise for mais sensivel, ambigua ou estrutural, usar tambem `docs/PG_DECISION_ENGINE_PROMPT.md`.
Este ficheiro ajuda a aprofundar a decisao consultiva antes de qualquer proposta final.

### 8. Ambito vindo do Odoo
Quando existir um snapshot atualizado em `.pg/PG_SCOPE_SYNC.json`, validar primeiro com `scripts/pg_validate_scope_sync.ps1` e depois aplicar `scripts/pg_apply_scope_sync.ps1`.
Esta etapa atualiza os blocos auto-geridos de ambito no `PG_CONTEXT.md`, sem reescrever a memoria consultiva.
Para implementar o lado Odoo desta integracao, usar tambem `docs/PG_ODOO_SCOPE_SYNC_INTEGRATION.md`.

### 9. Estado operacional vindo do Odoo
Quando existir um snapshot atualizado em `.pg/PG_PROJECT_STATUS_SYNC.json`, validar primeiro com `scripts/pg_validate_project_status_sync.ps1` e depois aplicar `scripts/pg_apply_project_status_sync.ps1`.
Esta etapa atualiza apenas a secao factual de estado operacional no `PG_CONTEXT.md`, sem reescrever a memoria consultiva.
Para implementar o lado Odoo desta integracao, usar tambem `docs/PG_ODOO_PROJECT_STATUS_SYNC_INTEGRATION.md`.

### 10. Consulta de padroes consultivos
Quando o requisito se assemelhar a um caso recorrente, consultar `docs/PG_CONSULTING_DECISION_PATTERNS.md`.
Este ficheiro serve para acelerar triagem e lembrar opcoes normalmente relevantes.

### 11. Consulta de aprendizagens anteriores
Quando for util recuperar experiencia consultiva previa, consultar `docs/PG_PROJECT_LEARNINGS.md`.
Este ficheiro ajuda a evitar erros repetidos e a reconhecer sinais recorrentes.

### 12. Verificacao final antes da resposta
Antes de fechar uma recomendacao consultiva importante, aplicar `docs/PG_PRE_RESPONSE_CHECKLIST.md`.
Esta checklist funciona como camada final de prudencia antes da resposta.

## Avaliacao obrigatoria de solucoes
Em qualquer requisito, a ordem obrigatoria de decisao e:
1. configuracao standard existente
2. modulo standard adicional
3. Odoo Studio
4. custom

Esta ordem nao deve ser saltada.
Na avaliacao de modulo standard adicional, a analise deve considerar tambem o `vendor/odoo_src` da versao ativa, incluindo modulos novos do Odoo.

## Atualizacao de contexto
O `PG_CONTEXT.md` deve ser atualizado sempre que houver alteracao relevante no entendimento do projeto.

Atualizar quando:
- uma decisao consultiva relevante e tomada
- uma restricao contratual e descoberta ou confirmada
- uma analise funcional importante e concluida
- surgem novos riscos, bloqueios ou proximos passos relevantes

## Registo de aprendizagens
Adicionar entradas em `docs/PG_PROJECT_LEARNINGS.md` quando surgir uma aprendizagem reutilizavel com valor para futuros projetos.

Exemplos:
- um modulo standard adicional evitou custom desnecessario
- Studio parecia suficiente mas revelou fragilidade
- o problema real era de processo e nao de funcionalidade
- um pedido aparente de custom era apenas preferencia operacional

## Quando atualizar cada ficheiro

| Ficheiro | Quando atualizar |
|---|---|
| `PG_CONTEXT.md` | Quando houver nova decisao consultiva, nova restricao, conclusao funcional relevante ou mudanca do estado atual do projeto |
| `PG_SCOPE_INTAKE.yaml` | Quando o ambito inicial, restricoes, processo ou input estruturado do projeto mudarem |
| `.pg/PG_SCOPE_SYNC.json` | Quando houver novo snapshot factual de ambito publicado a partir do Odoo |
| `.pg/PG_PROJECT_STATUS_SYNC.json` | Quando houver novo ponto de situacao factual publicado a partir do Odoo ou outro snapshot operacional |
| `PG_PROJECT_LEARNINGS.md` | Quando surgir uma aprendizagem reutilizavel observada em projeto real |
| `PG_CONSULTING_DECISION_PATTERNS.md` | Quando um padrao recorrente novo ficar claro e util para triagem futura |
| `AGENTS.md` | Quando for necessario ajustar regras estruturais de comportamento do agente no template |
| `PROMPT_INICIAL.md` | Quando for necessario reforcar ou simplificar o alinhamento operacional inicial com o agente |

## Regras importantes
- nunca alterar `vendor/odoo_src`
- nunca recomendar custom sem justificar porque as alternativas anteriores falharam
- separar sempre `FACTO OBSERVADO`, `INFERENCIA` e `PONTO POR VALIDAR`
- nunca fechar recomendacao definitiva sem evidencia suficiente
- se a evidencia for insuficiente, apresentar apenas recomendacao preliminar

## Nota sobre versionamento
O template esta atualmente na versao `v2.3`.
Futuras alteracoes devem respeitar as regras definidas em `docs/PG_TEMPLATE_VERSIONING.md`.
As evolucoes relevantes devem ser registadas em `CHANGELOG.md`.
