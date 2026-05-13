# Brodoo — Guia de Uso com Agentes AI

> Para consultores e gestores de projecto que utilizam Claude ou Codex com repositórios espelhados pelo Brodoo.

---

## Índice

1. [Como o Agente AI Lê o Projecto](#1-como-o-agente-ai-lê-o-projecto)
2. [Estrutura de Ficheiros que o Agente Consulta](#2-estrutura-de-ficheiros-que-o-agente-consulta)
3. [AGENTS.md, CLAUDE.md e AGENTS_SHARED.md — O que são](#3-agentsmd-claudemd-e-agents_sharedmd--o-que-são)
4. [PG_CONTEXT.md — Fonte de Verdade](#4-pg_contextmd--fonte-de-verdade)
5. [Restrições Contratuais — Como o Agente as Respeita](#5-restrições-contratuais--como-o-agente-as-respeita)
6. [Ordem Obrigatória de Decisão Técnica](#6-ordem-obrigatória-de-decisão-técnica)
7. [Modelo de Incerteza e Evidência](#7-modelo-de-incerteza-e-evidência)
8. [Formato de Resposta Esperado](#8-formato-de-resposta-esperado)
9. [Como Fazer Boas Perguntas ao Agente](#9-como-fazer-boas-perguntas-ao-agente)
10. [Diferença entre Claude e Codex neste Framework](#10-diferença-entre-claude-e-codex-neste-framework)
11. [Limitações e Pontos de Atenção](#11-limitações-e-pontos-de-atenção)

---

## 1. Como o Agente AI Lê o Projecto

Quando um consultor abre uma sessão com Claude ou Codex num repositório espelhado pelo Brodoo, o agente tem acesso a um conjunto de ficheiros que descrevem o estado real do projecto.

O agente **não tem memória entre sessões**. Cada sessão começa do zero. O que garante continuidade e coerência é o conjunto de ficheiros que o Brodoo mantém actualizados no repositório GitHub.

Fluxo de leitura do agente ao iniciar uma sessão:

```
1. AGENTS.md          → regras locais do projecto + ligação ao framework
2. CLAUDE.md          → wrapper carregado pelo Claude Code e alinhado com AGENTS.md
3. AGENTS_SHARED.md   → regras partilhadas do framework consultivo PG
4. PG_CONTEXT.md      → estado actual: âmbito, contrato, tarefas, plano
5. vendor/odoo_src    → source Odoo da versão activa (referência técnica)
6. código do projecto → código existente no repositório
```

Se o `PG_CONTEXT.md` estiver desactualizado, o agente trabalha com informação incorrecta. **O Brodoo só é útil com syncs regulares.**

---

## 2. Estrutura de Ficheiros que o Agente Consulta

Após o primeiro Mirror Total, o repositório tem esta estrutura:

```
repositorio-do-cliente/
├── AGENTS.md                        ← Regras locais + link para framework
├── CLAUDE.md                        ← Wrapper Claude Code que importa AGENTS.md
├── PG_CONTEXT.md                    ← Contexto consolidado (principal fonte de verdade)
├── PG_SCOPE_INTAKE.yaml             ← Âmbito estruturado em YAML (quando disponível)
├── .pg/
│   ├── project/project.json         ← Dados base: cliente, fase, contrato
│   ├── tasks/tasks.json             ← Tarefas com estado, responsável, prioridade
│   ├── planning/planning.json       ← Milestones e planeamento
│   ├── chatter/chatter.json         ← Mensagens com cliente e notas internas
│   ├── attachments/                 ← Metadata de anexos
│   ├── PG_SCOPE_SYNC.json           ← Âmbito curado das tarefas (scope sync)
│   ├── PG_PROJECT_STATUS_SYNC.json  ← Estado operacional do projecto
│   └── history/events.jsonl         ← Log de syncs anteriores
├── .pg_framework/
│   └── templates/
│       ├── AGENTS_SHARED.md         ← Regras partilhadas do framework PG
│       └── PG_CONTEXT.md            ← Template base do contexto
├── vendor/
│   └── odoo_src/                    ← Source Odoo (read-only, referência técnica)
└── [código do projecto]
```

### Prioridade de consulta

| Fonte | Quando usar |
|---|---|
| `PG_CONTEXT.md` | Sempre. É a memória funcional e decisória do projecto. |
| `AGENTS_SHARED.md` | Regras do framework. O agente aplica-as automaticamente. |
| `.pg/tasks/tasks.json` | Detalhe de tarefas quando PG_CONTEXT.md não chega. |
| `vendor/odoo_src` | Validação técnica — confirmar comportamento do Odoo. |
| `PG_SCOPE_INTAKE.yaml` | Âmbito estruturado, quando preenchido. |
| `.pg/PG_SCOPE_SYNC.json` | Lista curada de itens de âmbito activos. |

---

## 3. AGENTS.md, CLAUDE.md e AGENTS_SHARED.md — O que são

### AGENTS.md (local ao projecto)

Ficheiro criado uma vez por projecto, na raiz do repositório. Tem dois propósitos:

1. **Ligar o projecto ao framework partilhado** — instrui o agente a ler `AGENTS_SHARED.md` e `PG_CONTEXT.md` antes de qualquer análise.
2. **Registar overrides locais** — restrições ou instruções específicas deste projecto que sobrepõem as regras partilhadas.

Exemplo de override local:
```
## Overrides locais do projecto
- Não propor módulos de HR — fora do âmbito contratual deste projecto.
- Toda a comunicação em português europeu.
```

### CLAUDE.md (compatibilidade Claude Code)

Ficheiro criado na raiz do projecto para ser carregado automaticamente pelo Claude Code.
Deve continuar a ser apenas um wrapper: importa `AGENTS.md` e `.pg_framework/templates/AGENTS_SHARED.md`, para que Claude e Codex sigam o mesmo contrato sem duplicacao de regras.

### AGENTS_SHARED.md (framework partilhado)

Ficheiro partilhado entre todos os projectos, em `.pg_framework/templates/AGENTS_SHARED.md`. Contém:

- Fontes de verdade obrigatórias e ordem de consulta
- Ordem de decisão técnica (standard → módulo → Studio → custom)
- Validações obrigatórias antes de recomendar
- Modelo de incerteza (FACTO OBSERVADO / INFERÊNCIA / PONTO POR VALIDAR)
- Classificação obrigatória da recomendação final
- Formato mínimo de resposta

O agente aplica estas regras automaticamente em todos os projectos que usam o framework.

> **Nota:** Se `.pg_framework` não existir ou não estiver acessível no repositório, o agente deve parar e pedir que o framework seja religado antes de continuar.

---

## 4. PG_CONTEXT.md — Fonte de Verdade

O `PG_CONTEXT.md` é gerado automaticamente a cada Mirror Total. Contém quatro secções principais:

### Secção 1 — Contexto Estrutural

Inclui os dados do projecto, cliente, gestor, repositório, fase actual, e a secção crítica:

```
### Contrato e Parâmetros Odoo

> Parâmetros lidos do Odoo. Os agentes AI devem respeitar estas restrições em todas as respostas.

- Versão Odoo: 19.0
- Edição: Enterprise
- Ambiente: Odoo.sh
- Configuração standard: PERMITIDO
- Módulos standard adicionais: PERMITIDO
- Odoo Studio: PERMITIDO
- Desenvolvimento custom: NÃO PERMITIDO
- Restrições adicionais: [texto livre]
```

Esta secção é o que o agente lê para saber o que pode e não pode recomendar.

### Secção 2 — Planeamento

Milestones, próxima etapa, tarefas abertas.

### Secção 3 — Operação Actual

Total de tarefas, go-live alvo, resumo operacional.

### Secção 4 — Comunicações e Histórico

Mensagens recentes com o cliente, notas internas, histórico de syncs.

---

### Quando o PG_CONTEXT.md está desactualizado

Se o consultor fizer alterações significativas no Odoo (novo âmbito, tarefas fechadas, decisões tomadas) e não fizer sync, o agente trabalha com informação antiga.

**Regra prática:** Antes de iniciar uma sessão de análise ou desenvolvimento com o agente, executar **Sincronizar Agora** no Odoo para garantir que o contexto está actualizado.

---

## 5. Restrições Contratuais — Como o Agente as Respeita

As restrições do contrato do cliente são configuradas no Odoo (separador Brodoo → Estado do Projecto) e publicadas automaticamente no `PG_CONTEXT.md` a cada sync.

| Campo no Odoo | Valor | O que o agente faz |
|---|---|---|
| **Custom Allowed** | NÃO PERMITIDO | Não propõe desenvolvimento custom como caminho principal. Se custom for a única opção, alerta e pede confirmação. |
| **Studio Allowed** | NÃO PERMITIDO | Não propõe Odoo Studio. |
| **Additional Modules Allowed** | NÃO PERMITIDO | Limita a análise aos módulos já instalados no projecto. |
| **Standard Allowed** | NÃO PERMITIDO | Não propõe configurações que estejam fora do âmbito instalado. |

Se um campo estiver como **Não definido**, o agente trata como restrição desconhecida e pede clarificação antes de recomendar.

### Exemplo de comportamento esperado

Se `Custom Allowed = NÃO PERMITIDO` e o requisito só pode ser resolvido com custom:

> "O requisito não tem cobertura standard nem via Studio. Uma solução custom resolveria o problema, mas o contrato deste projecto não permite desenvolvimento custom. Recomendo escalar esta decisão ao gestor de projecto antes de prosseguir."

---

## 6. Ordem Obrigatória de Decisão Técnica

O agente segue sempre esta ordem antes de recomendar uma solução:

```
1. Funcionalidade standard já disponível no projecto
      ↓ (se não resolve)
2. Módulo standard Odoo adicional (mesmo que não instalado)
      ↓ (se não resolve)
3. Odoo Studio
      ↓ (se não resolve)
4. Desenvolvimento custom
```

**Nunca saltar etapas.** Se o agente recomendar custom sem analisar os módulos standard disponíveis no `vendor/odoo_src`, a recomendação é inválida.

### Classificação obrigatória da recomendação

Toda a recomendação final deve ser classificada numa das seguintes categorias:

| Categoria | Quando usar |
|---|---|
| `Configuração standard` | Resolvido com configuração do Odoo existente |
| `Módulo standard adicional` | Resolvido com módulo Odoo não instalado |
| `Odoo Studio` | Resolvido com Studio sem código |
| `Customização leve` | Código mínimo, baixo risco de upgrade |
| `Customização estrutural` | Código significativo, impacto em upgrades |
| `Não recomendado / alto risco` | Tecnicamente possível mas não aconselhável |

---

## 7. Modelo de Incerteza e Evidência

O agente deve distinguir explicitamente entre o que sabe com certeza e o que é inferência.

| Marcador | Significado |
|---|---|
| `FACTO OBSERVADO` | Confirmado no código, no `PG_CONTEXT.md` ou na documentação oficial |
| `INFERÊNCIA` | Conclusão provável mas não confirmada |
| `PONTO POR VALIDAR` | Informação necessária antes de decidir |

### Regra prática

Se o agente não citar um path em `vendor/odoo_src` ou um link da documentação oficial, a conclusão técnica é uma inferência — não um facto observado. O consultor deve pedir confirmação antes de implementar.

**O agente não deve adivinhar comportamentos do Odoo.** Se não consegue confirmar com o source, deve declarar explicitamente a incerteza.

---

## 8. Formato de Resposta Esperado

Sempre que houver análise de um requisito, o agente deve incluir no mínimo:

1. **Objectivo funcional** — o que o cliente quer atingir e qual a dor de negócio
2. **Factos observados** — confirmados no código, contexto ou documentação
3. **Inferências** — conclusões prováveis não confirmadas
4. **Pontos por validar** — o que precisa de ser confirmado antes de decidir
5. **Análise das opções** — na ordem obrigatória (standard → módulo → Studio → custom)
6. **Recomendação classificada** — com categoria e justificação
7. **Riscos e próximos passos**
8. **Referências consultadas:**
   - `PG_CONTEXT.md`
   - Paths do código do projecto consultados
   - Paths de `vendor/odoo_src` consultados
   - Links da documentação oficial Odoo da versão activa

---

## 9. Como Fazer Boas Perguntas ao Agente

### Contexto que o agente já tem (não é necessário repetir)

- Estado do projecto, fase, âmbito
- Restrições contratuais (custom, studio, módulos)
- Versão e edição do Odoo
- Tarefas abertas e planeamento

### O que ajuda incluir na pergunta

| O que incluir | Porquê |
|---|---|
| **O processo actual do cliente** | O agente sabe o que existe mas não sabe o que o cliente faz hoje |
| **O problema ou necessidade específica** | Distingue o pedido técnico da dor de negócio real |
| **O que já foi tentado** | Evita que o agente proponha o que já falhou |
| **Urgência ou impacto** | Ajuda a priorizar a solução mais pragmática |

### Exemplos de perguntas eficazes

**Boa:**
> "O cliente precisa de registar aprovações de despesas acima de 500€ com assinatura do director financeiro. Actualmente fazem por email. Quais as opções no Odoo para cobrir este fluxo?"

**Má:**
> "Como funciona a aprovação de despesas no Odoo?"

A pergunta boa dá contexto de negócio e activa a análise consultiva. A pergunta má gera uma resposta genérica sobre o módulo de despesas.

---

### Perguntas de validação técnica

Quando se pretende validar uma solução técnica específica:

> "Confirma se o campo `account.move.line.analytic_distribution` existe na versão 19.0 Enterprise e como é estruturado. Consulta `vendor/odoo_src`."

O agente vai ao source, cita o path e confirma ou corrige.

---

### Actualizar o contexto do agente a meio de sessão

Se durante a sessão houver uma decisão importante (ex: o cliente confirmou que custom é permitido, ou o âmbito mudou), informar o agente directamente:

> "O cliente confirmou que desenvolvimento custom é permitido neste projecto. Podes actualizar a tua análise com base nisto."

Depois da sessão, registar a decisão no Odoo e fazer sync para que fique no `PG_CONTEXT.md`.

---

## 10. Diferença entre Claude e Codex neste Framework

Ambos os agentes lêem os mesmos ficheiros e seguem as mesmas regras do `AGENTS_SHARED.md`. A diferença está no foco típico de uso:

| | **Claude** | **Codex** |
|---|---|---|
| **Foco principal** | Análise consultiva, fit-gap, decisão técnica | Implementação de código, revisão, debugging |
| **Quando usar** | Análise de requisitos, decisões de arquitectura, comunicação com cliente | Escrita de módulos Odoo, correção de bugs, geração de XML/Python |
| **Fonte de verdade** | `PG_CONTEXT.md` + `AGENTS_SHARED.md` | `PG_CONTEXT.md` + `AGENTS_SHARED.md` + código do projecto |
| **Regras contratuais** | Aplica automaticamente — não propõe o que não é permitido | Aplica automaticamente — não implementa o que não é permitido |

Ambos consultam `vendor/odoo_src` para validação técnica. Nenhum deve modificar ficheiros dentro de `vendor/odoo_src`.

---

## 11. Limitações e Pontos de Atenção

### O agente não tem acesso ao Odoo em tempo real

O agente só lê o que está no repositório. Se o estado do Odoo mudou desde o último sync, o agente não sabe. Fazer sync antes de sessões importantes.

### O agente pode estar errado

Mesmo seguindo todas as regras, o agente pode gerar inferências incorrectas. Validar sempre recomendações técnicas contra o source Odoo antes de implementar.

### vendor/odoo_src pode estar desactualizado

Se `vendor/odoo_src` não estiver actualizado para a versão correcta do Odoo, as validações técnicas do agente podem estar erradas. Verificar a versão do source antes de confiar em validações técnicas.

### O agente não faz commit nem push

O agente pode propor código, mas não executa operações de git. O consultor é sempre responsável pela decisão de integrar o código no projecto.

### Restrições contratuais são configuradas pelo gestor

Se `PG_CONTEXT.md` mostrar `Custom Allowed: Não definido`, não é o agente que define a política — é o gestor de projecto que precisa de configurar o campo no Odoo e fazer sync.

---

## Referências

| Documento | Para quê |
|---|---|
| [BRODOO_QUICK_START.md](BRODOO_QUICK_START.md) | Introdução rápida ao Brodoo e fluxo de 5 passos |
| [BRODOO_GUIA_OPERACIONAL.md](BRODOO_GUIA_OPERACIONAL.md) | Referência completa de operação diária |
| [PG_TROUBLESHOOTING.md](PG_TROUBLESHOOTING.md) | Resolução de problemas comuns |
