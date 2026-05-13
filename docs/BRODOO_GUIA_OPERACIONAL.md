# Brodoo — Guia Operacional

> Referência completa para gestores de projecto e consultores. Cobre configuração, operação diária e resolução de situações comuns.

---

## Índice

1. [Configuração do Projecto](#1-configuração-do-projecto)
2. [Onboarding Individual](#2-onboarding-individual)
3. [Onboarding em Batch](#3-onboarding-em-batch)
4. [Mirror Total — Sincronização Completa](#4-mirror-total--sincronização-completa)
5. [Outros Tipos de Sync](#5-outros-tipos-de-sync)
6. [Leitura do PG_CONTEXT.md](#6-leitura-do-pg_contextmd)
7. [Dashboard Operacional](#7-dashboard-operacional)
8. [Campos de Configuração do Projecto](#8-campos-de-configuração-do-projecto)
9. [Regras e Restrições](#9-regras-e-restrições)
10. [Checklist Operacional](#10-checklist-operacional)
11. [Resolução de Situações Comuns](#11-resolução-de-situações-comuns)

---

## 1. Configuração do Projecto

### 1.1 Campos Obrigatórios para Activar o Brodoo

No formulário do projecto, separador **Brodoo → Estado do Projecto**:

| Campo | Descrição | Obrigatório para |
|---|---|---|
| **Repositório** | Repositório GitHub ligado ao projecto | Qualquer sync |
| **Branch** | Branch de desenvolvimento (ex: `dev_nelson`) | Qualquer sync |
| **Versão Odoo** | Ex: `19.0` | Onboarding, PG_CONTEXT |
| **Edição Odoo** | `Enterprise` / `Community` / `Unknown` | Onboarding, agente AI |
| **Ambiente Odoo** | `Odoo.sh` / `SaaS` / `On-Premise` / `Unknown` | Onboarding, agente AI |

### 1.2 Campos de Contrato do Cliente

Estes campos definem o que o agente AI pode ou não recomendar para este projecto:

| Campo | Valores | Significado |
|---|---|---|
| **Standard Allowed** | Yes / No / Unknown | Configuração standard Odoo permitida? |
| **Additional Modules Allowed** | Yes / No / Unknown | Módulos standard adicionais permitidos? |
| **Studio Allowed** | Yes / No / Unknown | Odoo Studio permitido? |
| **Custom Allowed** | Yes / No / Unknown | Desenvolvimento custom permitido? |
| **Additional Contract Restrictions** | Texto livre | Restrições adicionais do contrato |

> Estes valores são publicados automaticamente no `PG_CONTEXT.md` a cada mirror sync e são lidos pelo agente AI.

### 1.3 Configurar o Repositório GitHub

Em **Brodoo → Repositórios GitHub**:
1. Clicar **Novo**
2. Preencher o nome completo do repositório (ex: `parametroglobaladmin/artful`)
3. Clicar **Sincronizar Branches** para carregar as branches disponíveis

---

## 2. Onboarding Individual

O wizard de onboarding individual permite configurar um projecto em detalhe, incluindo âmbito inicial, entregáveis e stakeholders.

### Acesso
Abrir o projecto → botão **Onboarding** no topo do formulário.

### Secções do Wizard

**Ligação ao Projecto**
- Seleccionar o projecto Odoo
- Seleccionar o repositório GitHub
- Seleccionar a branch de desenvolvimento

**Parâmetros Odoo**
- Versão, edição, ambiente
- Permissões do contrato (Standard / Módulos / Studio / Custom)

**Âmbito Inicial**
- Âmbito incluído (texto livre, uma linha por item)
- Âmbito excluído
- Entregáveis
- Pressupostos
- Stakeholders

**Sincronizações a Activar**
- Scope Sync, Status Sync, Decisions Sync, Risks Sync, Deliveries Sync, Requirements Sync, Project Plan Sync, Budget Sync

### Validações Automáticas

O wizard bloqueia a aplicação se:
- Branch `main` seleccionada com ambiente `Odoo.sh`
- Nenhum fluxo de sync activado
- Campos obrigatórios em falta (versão, edição, ambiente, permissões)

---

## 3. Onboarding em Batch

Permite publicar o primeiro Mirror Total para múltiplos projectos de uma só vez, sem necessidade de preencher o wizard individual completo.

### Quando usar
- Configuração inicial de vários projectos em simultâneo
- Quando os projectos já têm repositório e branch configurados no Odoo
- Para publicar o contexto base antes de fazer o onboarding individual detalhado

### Como usar
1. Ir a **Project → Projects** (vista de lista)
2. Seleccionar os projectos pretendidos (checkbox)
3. Menu **Acções → Onboarding em Batch**
4. O wizard mostra:
   - **Elegíveis:** projectos com repositório + branch configurados
   - **Ignorados:** projectos sem repositório ou branch
5. Clicar **Iniciar Sync**
6. O resultado mostra: sucesso / erro / ignorado por projecto

### O que o batch onboarding faz
- Activa `Scope Sync` automaticamente se nenhum sync estiver activo (necessário para o mirror funcionar)
- Publica o Mirror Total completo: âmbito, planeamento, tarefas, chatter, anexos
- Gera o `PG_CONTEXT.md` inicial no repositório GitHub

---

## 4. Mirror Total — Sincronização Completa

O Mirror Total é a operação principal do Brodoo. Publica um snapshot completo do estado do projecto no repositório GitHub.

### O que é publicado
| Ficheiro | Conteúdo |
|---|---|
| `PG_CONTEXT.md` | Contexto consolidado em Markdown (para agentes AI e leitura humana) |
| `.pg/project/project.json` | Dados base do projecto, contrato, âmbito |
| `.pg/tasks/tasks.json` | Todas as tarefas com estado, responsáveis, prioridade |
| `.pg/planning/planning.json` | Milestones, planeamento, próximas etapas |
| `.pg/chatter/chatter.json` | Mensagens com cliente e notas internas |
| `.pg/attachments/attachments.json` | Metadata de anexos |
| `.pg/history/events.jsonl` | Log de todos os syncs anteriores |

### Como disparar manualmente
Abrir o projecto → botão **Sincronizar Agora**.

### Comportamento de hash
O Brodoo calcula um hash do payload. Se o estado do projecto não mudou desde o último sync, o mirror não republica (evita commits desnecessários no GitHub).

### Quando o mirror não fica em fila (retorna False)
O `queue_project` retorna `False` (sem criar run) se:
- `pg_scope_sync_enabled` e `pg_status_sync_enabled` ambos desactivados
- Repositório ou branch em falta

---

## 5. Outros Tipos de Sync

Além do Mirror Total, o Brodoo tem syncs específicos para partes do projecto:

| Sync | Ficheiro publicado | Activar em |
|---|---|---|
| **Scope Sync** | `.pg/PG_SCOPE_SYNC.json` | Separador Brodoo → Scope Sync Enabled |
| **Status Sync** | `.pg/PG_PROJECT_STATUS_SYNC.json` | Separador Brodoo → Status Sync Enabled |
| **Decisions Sync** | `.pg/decisions/` | Separador Brodoo → Decisions Sync Enabled |
| **Risks Sync** | `.pg/risks/` | Separador Brodoo → Risks Sync Enabled |
| **Deliveries Sync** | `.pg/deliveries/` | Separador Brodoo → Deliveries Sync Enabled |
| **Requirements Sync** | `.pg/requirements/` | Separador Brodoo → Requirements Sync Enabled |
| **Project Plan Sync** | `.pg/planning/` | Separador Brodoo → Project Plan Sync Enabled |
| **Budget Sync** | `.pg/budget/` | Separador Brodoo → Budget Sync Enabled |

### Modos de Scope Sync
- **Manual:** só sincroniza quando o utilizador clicar no botão
- **Event-Driven:** sincroniza automaticamente quando tarefas do projecto são alteradas

---

## 6. Leitura do PG_CONTEXT.md

O `PG_CONTEXT.md` é gerado automaticamente a cada Mirror Total. Estrutura:

### Secção 1 — Contexto Estrutural
```
- Projecto, cliente, gestor, repositório, branch
- Fase e etapa actual
- Último sync

### Objectivo e pedido actual
- Objetivo do projecto
- Pedido/requisito em curso

### Âmbito incluído
- Lista de itens de âmbito curados

### Contrato e Parâmetros Odoo          ← CRÍTICO para agentes AI
- Versão Odoo, Edição, Ambiente
- Configuração standard: PERMITIDO / NÃO PERMITIDO / Não definido
- Módulos standard adicionais: ...
- Odoo Studio: ...
- Desenvolvimento custom: ...
- Restrições adicionais: ...
```

### Secção 2 — Planeamento
- Milestones, próxima etapa, tasks abertas

### Secção 3 — Operação Actual
- Total de tarefas, go-live alvo, resumo operacional

### Secção 4 — Comunicações e Histórico
- Mensagens recentes com cliente, notas internas, histórico de syncs

---

## 7. Dashboard Operacional

Aceder em **Brodoo → Dashboard Brodoo**.

O dashboard apresenta uma visão consolidada de todos os projectos:

| Secção | O que mostra |
|---|---|
| **Tarefas Prontas** | Tasks em estado "ready for Brodoo" (prontas para o agente AI trabalhar) |
| **Falhas de Sincronização de Âmbito** | Projectos com scope sync em erro |
| **Falhas de Sincronização de Estado** | Projectos com status sync em erro |
| **Ações Rápidas** | Acesso directo às operações mais comuns |

---

## 8. Campos de Configuração do Projecto

### Separador "Estado do Projecto"

**Bloco esquerdo — Contexto funcional:**
| Campo | Para quê |
|---|---|
| Client Unit | Unidade organizacional do cliente |
| Repository Summary | Sumário do repositório para o agente AI |
| Project Phase | Fase actual: Análise / Implementação / Piloto / Go-Live / etc. |
| Odoo Version | Ex: `19.0` |
| Odoo Edition | Enterprise / Community / Unknown |
| Odoo Environment | Odoo.sh / SaaS / On-Premise / Unknown |
| Urgency | Low / Medium / High / Critical |

**Bloco direito — Contrato:**
| Campo | Para quê |
|---|---|
| Standard Allowed | Configuração standard permitida? |
| Additional Modules Allowed | Módulos adicionais permitidos? |
| Studio Allowed | Odoo Studio permitido? |
| Custom Allowed | Desenvolvimento custom permitido? |
| Additional Contract Restrictions | Texto livre para restrições específicas |

### Separador "Âmbito Actual"

| Campo | Para quê |
|---|---|
| Business Goal | Objectivo de negócio do projecto |
| Current Request | Requisito/pedido actual em análise |
| Current Process | Processo actual do cliente (antes do Odoo) |
| Problem or Need | Problema ou necessidade identificada |
| Business Impact | Impacto no negócio se não resolvido |
| Trigger | O que desencadeou este pedido |
| Frequency | Frequência de execução do processo |
| Volumes | Volumes envolvidos |

---

## 9. Regras e Restrições

### Regra 1 — Branch `main` proibida em Odoo.sh
Em projectos com ambiente `Odoo.sh`, o campo **Branch** não pode ser `main`. O Brodoo bloqueia esta configuração com uma mensagem de erro clara.

**Porquê:** Em Odoo.sh, `main` é a branch de produção. Ligar o sync de desenvolvimento à produção causaria publicação de contexto incompleto ou incoerente.

**Como resolver:** Criar uma branch de desenvolvimento no repositório GitHub (ex: `dev`, `staging`, `dev_nome`) e usar essa branch no campo Branch do projecto.

### Regra 2 — Ordem obrigatória de decisão técnica
O agente AI segue sempre esta ordem antes de recomendar uma solução:
1. Funcionalidade standard já disponível no projecto
2. Módulo standard Odoo adicional (mesmo que não instalado)
3. Odoo Studio
4. Desenvolvimento custom

**Nunca saltar** da análise standard directamente para custom.

### Regra 3 — `vendor/odoo_src` é read-only
O directório `vendor/odoo_src` no repositório contém o source code Odoo para referência técnica. Nunca deve ser modificado nem versionado.

---

## 10. Checklist Operacional

### Antes de iniciar um novo projecto
- [ ] Repositório GitHub criado
- [ ] Branch de desenvolvimento criada (nunca `main` em Odoo.sh)
- [ ] Módulo `pg_brodoo` instalado
- [ ] Token GitHub configurado em Brodoo → Configuração

### Configuração inicial do projecto
- [ ] Repositório e branch preenchidos no separador Brodoo
- [ ] Versão, edição e ambiente Odoo preenchidos
- [ ] Contrato preenchido (Standard / Módulos / Studio / Custom)
- [ ] Onboarding em batch **ou** onboarding individual executado
- [ ] Primeiro mirror sync realizado com sucesso
- [ ] `PG_CONTEXT.md` verificado no GitHub com secção "Contrato e Parâmetros Odoo" preenchida

### Operação regular (semanal)
- [ ] Verificar dashboard para syncs com erro
- [ ] Executar **Sincronizar Agora** após alterações significativas no âmbito
- [ ] Validar que `PG_CONTEXT.md` reflecte o estado actual do projecto

---

## 11. Resolução de Situações Comuns

### "Sync ignorado — mirror sync não disponível"
**Causa:** `pg_scope_sync_enabled` e `pg_status_sync_enabled` ambos desactivados.  
**Solução:** No formulário do projecto, separador Brodoo, activar pelo menos um dos dois.

### "A branch 'main' não pode ser utilizada em projectos Odoo.sh"
**Causa:** O campo Branch está preenchido com `main` e o Ambiente é `Odoo.sh`.  
**Solução:** Alterar o campo Branch para uma branch de desenvolvimento.

### "planning payload requires a non-empty string: current_phase"
**Causa:** Versão antiga do módulo sem o fix do planning payload.  
**Solução:** Fazer upgrade do módulo `pg_brodoo` para a versão mais recente (`19.0.1.0.0`).

### Mirror sync executado mas `PG_CONTEXT.md` sem secção "Contrato e Parâmetros Odoo"
**Causa:** Versão antiga do módulo.  
**Solução:** Fazer upgrade do módulo e executar novo sync.

### Mirror sync com "Sync já em curso"
**Causa:** Já existe um run em estado `queued` ou `running` para este projecto.  
**Solução:** Aguardar o run actual terminar. Verificar em **Brodoo → Mirror Sync Runs**.

### Build Odoo.sh falha com "invalid syntax at line 1:1"
**Causa:** Ficheiro `__manifest__.py` ou XML com BOM UTF-8.  
**Solução:** Garantir que os ficheiros são escritos com UTF-8 sem BOM. O PowerShell usa BOM por defeito — usar `New-Object System.Text.UTF8Encoding($false)`.
