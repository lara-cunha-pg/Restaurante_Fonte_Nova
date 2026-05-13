# PG_PRE_RESPONSE_CHECKLIST

Este ficheiro funciona como checklist final antes de respostas consultivas relevantes.
Nao substitui `PG_CONTEXT.md`, `templates/AGENTS.md`, `docs/PROMPT_INICIAL.md` nem `docs/PG_DECISION_ENGINE_PROMPT.md`.
Serve apenas como camada de verificacao antes da resposta final.

## Checklist antes da resposta final

### 1. Contexto validado
- confirmei o objetivo funcional, processo atual, problema real e impacto no negocio?
- confirmei ou marquei como `PONTO POR VALIDAR` a versao, edicao, ambiente e restricoes contratuais?

### 2. Evidencia tecnica consultada
- consultei `PG_CONTEXT.md`?
- consultei codigo do projeto relevante?
- consultei `vendor/odoo_src` da versao ativa?
- consultei documentacao oficial da mesma versao, quando necessario?

### 3. Ordem consultiva respeitada
- avaliei primeiro standard ja existente no projeto?
- avaliei modulo standard adicional antes de Studio e custom?
- avaliei Studio antes de concluir que custom e necessario?

### 4. Factos, inferencias e pontos por validar
- distingui claramente `FACTO OBSERVADO`, `INFERENCIA` e `PONTO POR VALIDAR`?
- evitei apresentar inferencia como facto?

### 5. Descoberta de modulos standard adicionais
- procurei tambem no `vendor/odoo_src` modulos standard potencialmente relevantes, incluindo modulos novos do Odoo?
- se recomendei modulo standard adicional, expliquei cobertura, implicacoes de adocao e gaps remanescentes?

### 6. Coerencia com o contexto do projeto
- a recomendacao respeita `PG_CONTEXT.md` e o estado real do projeto?
- a recomendacao respeita as restricoes contratuais identificadas?

### 7. Justificacao da recomendacao final
- expliquei porque a opcao recomendada e a mais adequada?
- se a conclusao for Studio ou custom, justifiquei porque standard existente e modulo standard adicional nao chegam?
- se a conclusao for custom, explicitei risco, manutencao e impacto de upgrade?

## Regra final
Se a evidencia nao for suficiente, nao fechar a decisao.
Nessa situacao, apresentar apenas `RECOMENDACAO PRELIMINAR` e indicar o que falta validar.
