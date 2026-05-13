# PG_PROJECT_LEARNINGS

Este ficheiro guarda aprendizagens consultivas reutilizaveis observadas em projetos Odoo.
Serve para acelerar triagem, reconhecer sinais recorrentes e evitar erros repetidos.
Nao substitui a validacao do projeto atual contra `PG_CONTEXT.md`, codigo do projeto, `vendor/odoo_src` e documentacao oficial da versao ativa.

## LEARNING 001 - Studio parecia suficiente, mas fragilizou o processo
Contexto:
- pedido de campos, regras e automacoes cresceu iterativamente sobre o mesmo fluxo

Sinal inicial:
- a solucao parecia "leve" e rapida porque cada alteracao isolada era pequena

O que aconteceu:
- a soma das pequenas regras criou dependencia de Studio dificil de manter e explicar

Aprendizagem:
- Studio e bom para extensoes moderadas e bem delimitadas, nao para substituir desenho funcional consistente

Heuristica reutilizavel:
- se o requisito atravessa varios modelos, varios estados e varias excecoes, reavaliar cedo se Studio continua adequado

## LEARNING 002 - Modulo standard adicional evitou custom desnecessario
Contexto:
- pedido parecia exigir desenvolvimento para approvals e governance operacional

Sinal inicial:
- a equipa assumiu que o modulo principal nao cobria o caso

O que aconteceu:
- um modulo standard adicional do Odoo cobria a maior parte do requisito com adaptacao de processo aceitavel

Aprendizagem:
- limitar a analise aos modulos ja instalados aumenta risco de customizacao prematura

Heuristica reutilizavel:
- quando o gap parece estrutural, procurar primeiro modulos standard adicionais no `vendor/odoo_src` da versao ativa

## LEARNING 003 - O pedido era preferencia, nao necessidade real
Contexto:
- cliente pediu alteracao funcional com forte componente de interface e conforto operativo

Sinal inicial:
- a justificacao vinha em termos de preferencia e nao de risco, custo ou compliance

O que aconteceu:
- a necessidade real foi resolvida com configuracao e treino, sem alterar o comportamento base

Aprendizagem:
- nem toda a friccao operacional e gap funcional do sistema

Heuristica reutilizavel:
- antes de avaliar custom, perguntar sempre que decisao de negocio falha sem a alteracao pedida

## LEARNING 004 - Parecia documental, mas era operacional
Contexto:
- pedido foi descrito como necessidade de anexos, documentos e assinatura

Sinal inicial:
- a conversa focava ficheiros e templates, mas os erros aconteciam no handoff entre equipas

O que aconteceu:
- o problema principal estava no fluxo operacional, nao na camada documental

Aprendizagem:
- sintomas documentais podem esconder falha de processo, aprovacao ou ownership

Heuristica reutilizavel:
- se ha muitos anexos e excecoes, validar primeiro o processo que gera esses documentos

## LEARNING 005 - Workflow parecia complexo, mas o problema era de processo
Contexto:
- equipa pediu multiplos estados, aprovacoes e validacoes adicionais

Sinal inicial:
- cada interveniente queria um checkpoint proprio no sistema

O que aconteceu:
- a complexidade vinha da indefinicao de responsabilidade e nao de limite real do Odoo

Aprendizagem:
- desenhar workflow custom sobre processo mal definido cristaliza ineficiencia

Heuristica reutilizavel:
- se o pedido de estados cresce depressa, parar e clarificar ownership, excecoes e criterio de decisao antes de modelar o fluxo

## LEARNING 006 - Reporting falhou por dados, nao por falta de dashboard
Contexto:
- pedido para dashboards executivos mais ricos e relatorios adicionais

Sinal inicial:
- havia pressao para ver melhor, mas pouca confianca nos numeros de origem

O que aconteceu:
- o gargalo principal estava em classificacao, completude e disciplina de registo de dados

Aprendizagem:
- dashboard novo nao corrige semantica de dados inconsistente

Heuristica reutilizavel:
- antes de recomendar reporting adicional, validar definicoes de KPI, campos obrigatorios e qualidade dos dados base
