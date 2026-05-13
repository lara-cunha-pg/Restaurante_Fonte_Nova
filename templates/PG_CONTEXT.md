# PG_CONTEXT - Memoria funcional e decisoria

> Fonte de verdade do estado funcional, tecnico e consultivo do projeto.
> Alguns blocos marcados com `PG_AUTO` podem ser atualizados automaticamente a partir de `PG_SCOPE_INTAKE.yaml`, `.pg/PG_PROJECT_STATUS_SYNC.json` e scripts do template.

## Estado Oficial do Projeto

### Identificacao do projeto
<!-- PG_AUTO:IDENTIFICACAO:START -->
Nome do projeto: [PREENCHER]
Cliente / unidade: [PREENCHER]
Resumo funcional do repositorio: [PREENCHER]
Fase atual do projeto: [PONTO POR VALIDAR]
<!-- PG_AUTO:IDENTIFICACAO:END -->

### Parametros Odoo ativos
Versao do Odoo: [PONTO POR VALIDAR]
Edicao: [PONTO POR VALIDAR]
Ambiente: [PONTO POR VALIDAR]
Path do core: [PONTO POR VALIDAR]
Path source Enterprise: [NAO CONFIGURADO]
Documentacao oficial base: [PONTO POR VALIDAR]
Documentacao Studio: [PONTO POR VALIDAR]
Documentacao Developer: [PONTO POR VALIDAR]
Ultima sincronizacao de ambito: [NAO EXECUTADA]
Fonte do ambito sincronizado: [PONTO POR VALIDAR]
Ultima sincronizacao automatica: [NAO EXECUTADA]

### Restricoes do projeto
<!-- PG_AUTO:RESTRICOES:START -->
Configuracao standard permitida?: [PONTO POR VALIDAR]
Modulos standard adicionais permitidos?: [PONTO POR VALIDAR]
Odoo Studio permitido?: [PONTO POR VALIDAR]
Custom permitido?: [PONTO POR VALIDAR]
Restricoes contratuais adicionais: [PONTO POR VALIDAR]
<!-- PG_AUTO:RESTRICOES:END -->

### Pedido funcional atual
<!-- PG_AUTO:PEDIDO_ATUAL:START -->
Requisito / pedido atual: [Descrever o requisito atual com linguagem de negocio.]
Objetivo de negocio: [PREENCHER]
Trigger: [PREENCHER]
Frequencia: [PREENCHER]
Volumes: [PREENCHER]
Urgencia: [PREENCHER]
Criterios de aceitacao:
- [PREENCHER]
<!-- PG_AUTO:PEDIDO_ATUAL:END -->

### Processo atual
<!-- PG_AUTO:PROCESSO_ATUAL:START -->
Processo atual: [Descrever o processo existente, atores, documentos e etapas.]
Utilizadores / papeis:
- [PREENCHER]
Excecoes conhecidas:
- [PREENCHER]
Aprovacoes:
- [PREENCHER]
Documentos envolvidos:
- [PREENCHER]
Integracoes:
- [PREENCHER]
Reporting esperado:
- [PREENCHER]
O que ja foi tentado ou validado no standard atual:
- [PREENCHER]
Porque foi considerado insuficiente:
- [PREENCHER]
<!-- PG_AUTO:PROCESSO_ATUAL:END -->

### Problema / dor
<!-- PG_AUTO:PROBLEMA_DOR:START -->
Problema / necessidade observada: [Descrever o problema observado ou a necessidade do negocio.]
<!-- PG_AUTO:PROBLEMA_DOR:END -->

### Impacto no negocio
<!-- PG_AUTO:IMPACTO_NEGOCIO:START -->
Impacto de negocio: [Descrever impacto operacional, financeiro, risco, compliance ou UX.]
<!-- PG_AUTO:IMPACTO_NEGOCIO:END -->

## Artefactos Fatuais Publicados

> Esta camada le snapshots oficiais publicados em `.pg/`.
> Os snapshots continuam a ser a source of truth factual primaria; este ficheiro funciona apenas como consolidacao derivada de leitura.

### Ambito factual publicado
<!-- PG_AUTO:SCOPE_ITEMS:START -->
Resumo do scope sincronizado:
- Itens ativos: [PREENCHER]
- Itens validados: [PREENCHER]
- Itens propostos: [PREENCHER]
- Itens diferidos: [PREENCHER]
- Ultima alteracao de task: [PONTO POR VALIDAR]

Itens em ambito:
- [PREENCHER]
<!-- PG_AUTO:SCOPE_ITEMS:END -->

### Estado operacional factual publicado
<!-- PG_AUTO:STATUS_SYNC:START -->
Schema do snapshot: [PONTO POR VALIDAR]
Ultima atualizacao recebida do Odoo: [NAO SINCRONIZADA]
Fase reportada no ultimo sync: [PONTO POR VALIDAR]
Estado geral reportado: [PONTO POR VALIDAR]
Sistema de origem: [PONTO POR VALIDAR]
Modelo Odoo de origem: [PONTO POR VALIDAR]
Record Odoo de origem: [PONTO POR VALIDAR]
URL do record Odoo: [PONTO POR VALIDAR]
Publicado no repositorio em: [PONTO POR VALIDAR]
Publicado por: [PONTO POR VALIDAR]
Trigger de sync: [PONTO POR VALIDAR]
Branch de sync: [PONTO POR VALIDAR]
Milestones:
- [PREENCHER]
Bloqueios:
- [PREENCHER]
Riscos operacionais:
- [PREENCHER]
Proximos passos operacionais:
- [PREENCHER]
Decisoes pendentes:
- [PREENCHER]
Go-live alvo: [PONTO POR VALIDAR]
Owner atual: [PONTO POR VALIDAR]
Fonte Odoo / referencia: [PONTO POR VALIDAR]
<!-- PG_AUTO:STATUS_SYNC:END -->

### Decisoes factuais publicadas

Derivado de `.pg/PG_DECISIONS_SYNC.json` quando esse snapshot existir no projeto bootstrapado.
Este bloco continua de leitura e nao substitui o snapshot factual.

### Riscos factuais publicados

Derivado de `.pg/PG_RISKS_SYNC.json` quando esse snapshot existir no projeto bootstrapado.
Este bloco continua de leitura e nao substitui o snapshot factual.

### Entregaveis, requisitos, plano e budget publicados

Os snapshots `.pg/PG_DELIVERIES_SYNC.json`, `.pg/PG_REQUIREMENTS_SYNC.json`,
`.pg/PG_PROJECT_PLAN_SYNC.json` e `.pg/PG_BUDGET_SYNC.json` continuam a ser os
artefactos factuais primarios. A sua integracao textual neste contexto deve ser
sempre derivada, curta e explicitamente nao canonica.

## Consolidacao e Gaps

### Gaps factuais ainda por consolidar

- [PREENCHER]

### Dependencias de refresh e validacao

- [PREENCHER]

## Curadoria Assistida e Itens Por Promover

> Drafts, chatter e backlog operacional vivem aqui apenas como apoio a curadoria.
> Nada desta secao deve competir com os campos oficiais ou com os snapshots publicados.

### Drafts e sinais em revisao

- [PREENCHER]

### Itens por promover a oficial

- [PREENCHER]

## Analise Consultiva e Decisao

### Analise de solucao

### 1. Standard ja existente no projeto
Estado: [NAO ANALISADO]
Factos observados:
- [PREENCHER]
Inferencias:
- [PREENCHER]
Pontos por validar:
- [PREENCHER]

### 2. Standard adicional Odoo
Estado: [NAO ANALISADO]
Modulos / funcionalidades a avaliar:
- [PREENCHER]
Cobertura do requisito: [PONTO POR VALIDAR]
Implicacoes de adocao:
- [PREENCHER]
Factos observados:
- [PREENCHER]
Inferencias:
- [PREENCHER]
Pontos por validar:
- [PREENCHER]

### 3. Odoo Studio
Estado: [NAO ANALISADO]
Factos observados:
- [PREENCHER]
Inferencias:
- [PREENCHER]
Pontos por validar:
- [PREENCHER]

### 4. Custom
Estado: [NAO ANALISADO]
Escopo minimo se for necessario:
- [PREENCHER]
Factos observados:
- [PREENCHER]
Inferencias:
- [PREENCHER]
Pontos por validar:
- [PREENCHER]

### Decisao atual
Classificacao final: [PONTO POR VALIDAR]
Decisao: [PREENCHER]
Justificacao: [PREENCHER]

### Riscos
- [PREENCHER]

### Proximos passos
- [PREENCHER]

## Referencias e Historico

### Referencias consultadas

#### Documentacao Odoo
- [PREENCHER]

#### Core Odoo
- [PREENCHER]

#### Codigo do projeto
- [PREENCHER]

### Historico de marcos de decisao

#### YYYY-MM-DD - [Titulo curto]
Contexto:
- [PREENCHER]

Decisao:
- [PREENCHER]

Riscos / pendencias:
- [PREENCHER]

Referencias:
- [PREENCHER]
