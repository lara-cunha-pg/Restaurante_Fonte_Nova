# Brodoo — Guia de Início Rápido

> Versão do módulo: `19.0.1.0.0` | Plataforma: Odoo 19

## O que é o Brodoo?

O Brodoo é um módulo Odoo que liga cada projeto de implementação a um repositório GitHub. A partir dessa ligação, o Odoo publica automaticamente um **espelho factual do projeto** — âmbito, planeamento, tarefas, comunicações — num conjunto de ficheiros JSON e Markdown que os agentes AI (Claude, Codex) lêem como contexto.

O resultado prático: o agente AI sabe exactamente em que estado está o projecto, quais são as restrições do contrato do cliente, e o que está incluído ou excluído do âmbito — sem que o consultor tenha de repetir esse contexto em cada sessão.

---

## Conceitos Fundamentais

| Conceito | O que é |
|---|---|
| **Mirror Total** | Publicação completa do estado do projecto no GitHub: âmbito, plano, tarefas, chatter, anexos |
| **PG_CONTEXT.md** | Ficheiro Markdown gerado automaticamente a partir do espelho. É a fonte de verdade que o agente AI lê |
| **Onboarding de Projecto** | Processo de configuração inicial de um projecto no Brodoo: ligar repositório, branch, parâmetros Odoo e contrato |
| **Scope Sync** | Publicação isolada do âmbito (tasks com scope curado) para o GitHub |
| **Branch de desenvolvimento** | Em Odoo.sh, a branch de trabalho de um projecto — **nunca `main`** (produção) |
| **Contrato do cliente** | Conjunto de restrições configuradas no projecto: Versão Odoo, Custom/Studio/Módulos permitidos |

---

## Pré-requisitos

Antes de usar o Brodoo num projecto, verificar:

- [ ] Módulo `pg_brodoo` instalado na instância Odoo
- [ ] Conta GitHub configurada em **Brodoo → Configuração** (token de acesso)
- [ ] Repositório GitHub criado para o projecto do cliente
- [ ] Branch de desenvolvimento criada no repositório (ex: `dev_nelson`, `staging`)

---

## Fluxo de Uso em 5 Passos

### Passo 1 — Criar o projecto no Odoo
Criar o projecto normalmente em **Project → Projects**. O projecto precisa de existir antes de qualquer configuração Brodoo.

### Passo 2 — Onboarding em Batch (configuração inicial de vários projectos)
Para configurar múltiplos projectos de uma vez:

1. Ir a **Project → Projects** (vista de lista)
2. Seleccionar os projectos pretendidos
3. Menu **Acções → Onboarding em Batch**
4. O wizard mostra quais os projectos elegíveis (com repositório + branch) e quais serão ignorados
5. Clicar **Iniciar Sync** — o Brodoo publica o primeiro espelho em cada projecto

> **Elegibilidade:** O projecto precisa de ter os campos **Repositório** e **Branch** preenchidos no separador Brodoo.

### Passo 3 — Onboarding Individual (configuração detalhada)
Abrir o projecto → botão **Onboarding** (topo do formulário):

- Preencher versão Odoo, edição, ambiente
- Definir restrições do contrato (Standard/Módulos/Studio/Custom permitidos)
- Configurar âmbito inicial, entregáveis, stakeholders
- Activar os fluxos de sync (Scope Sync, Status Sync, etc.)
- Aplicar configuração

### Passo 4 — Sincronizar (publicar espelho)
Após o onboarding, o espelho fica configurado. Para publicar:

- **Manual:** botão **Sincronizar Agora** no formulário do projecto
- **Automático:** o Brodoo detecta alterações e sincroniza (se configurado em modo event-driven)

O GitHub recebe os ficheiros `.pg/` e o `PG_CONTEXT.md` actualizado.

### Passo 5 — Usar o agente AI
Com o repositório espelhado, o agente AI (Claude ou Codex) tem acesso a:
- `PG_CONTEXT.md` — contexto completo e restrições do contrato
- `.pg/project/project.json` — dados estruturados do projecto
- `.pg/tasks/tasks.json` — todas as tarefas
- `.pg/planning/planning.json` — milestones e planeamento

O agente respeita automaticamente as restrições contratuais definidas no Passo 3 (ex: "Custom Allowed: NÃO PERMITIDO").

---

## Estrutura de Ficheiros no Repositório GitHub

Após o primeiro Mirror Total, o repositório fica com esta estrutura:

```
repositorio-do-cliente/
├── PG_CONTEXT.md              ← Contexto consolidado (agente AI lê aqui)
├── AGENTS.md                  ← Instruções para agentes AI
├── CLAUDE.md                  ← Wrapper Claude Code que importa AGENTS.md
├── .pg/
│   ├── project/project.json   ← Dados base do projecto
│   ├── tasks/tasks.json       ← Todas as tarefas
│   ├── planning/planning.json ← Milestones e planeamento
│   ├── chatter/chatter.json   ← Comunicações e notas
│   ├── attachments/           ← Metadata de anexos
│   └── history/events.jsonl   ← Histórico de syncs
├── vendor/
│   └── odoo_src/              ← Source Odoo (referência técnica, read-only)
└── [código do projecto]
```

---

## Restrições Importantes

| Regra | Porquê |
|---|---|
| **Nunca usar branch `main` em projectos Odoo.sh** | Em Odoo.sh, `main` é produção. O Brodoo bloqueia esta configuração. |
| **Nunca modificar `vendor/odoo_src`** | É referência técnica read-only do source Odoo |
| **Custom só com justificação** | O agente AI segue a ordem: Standard → Módulo adicional → Studio → Custom |

---

## Documentação de Apoio

| Documento | Para quê |
|---|---|
| [BRODOO_GUIA_OPERACIONAL.md](BRODOO_GUIA_OPERACIONAL.md) | Referência completa de operação diária |
| [BRODOO_AGENTES_AI_GUIA.md](BRODOO_AGENTES_AI_GUIA.md) | Como usar Claude e Codex com o framework |
| [PG_TROUBLESHOOTING.md](PG_TROUBLESHOOTING.md) | Resolução de problemas comuns |
