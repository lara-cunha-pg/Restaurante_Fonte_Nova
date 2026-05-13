# Template — Levantamento de Âmbito

## Finalidade
Documento produzido na fase de análise para capturar o processo actual do cliente, identificar necessidades e definir o âmbito de implementação Odoo. Serve de base ao contrato, ao planeamento e à configuração do projecto no Brodoo.

## Tom de Discurso
- Analítico e estruturado
- Neutro — descreve o que existe sem julgamento sobre as escolhas actuais do cliente
- Preciso — evitar linguagem vaga ("possivelmente", "talvez", "em princípio")
- Distingue claramente factos confirmados de pontos ainda por validar
- Orientado ao negócio — as secções técnicas devem ser compreensíveis pelo cliente

## Instruções para o Agente
1. Basear o documento no `PG_CONTEXT.md` (campos: Business Goal, Current Request, Current Process, Problem or Need, Business Impact, Trigger, Frequency, Volumes)
2. Completar com informação da sessão actual
3. Marcar explicitamente os campos desconhecidos como `[POR VALIDAR]`
4. A secção "Âmbito Excluído" é tão importante quanto a incluída — protege o projecto de scope creep
5. Versionar o documento a cada revisão significativa

---

## Estrutura do Documento

---

# [Nome do Projecto] — Levantamento de Âmbito

**Versão:** 1.0
**Data:** DD/MM/AAAA
**Autor:** [Nome]
**Estado:** Rascunho / Em revisão / Validado pelo cliente
**Revisão pendente:** [Nome do interlocutor cliente], até DD/MM/AAAA

---

## 1. Contexto e Objectivo de Negócio

[Descrever o objectivo do projecto do ponto de vista do cliente. O que querem atingir, porquê agora, e qual o impacto esperado no negócio.]

**Trigger:** [O que desencadeou este projecto ou pedido]
**Impacto de negócio se não resolvido:** [Consequência de não avançar]

---

## 2. Processo Actual (AS-IS)

[Descrever como o processo funciona hoje, antes da implementação Odoo ou da alteração proposta. Incluir: quem executa, como executa, com que ferramentas, frequência e volumes aproximados.]

**Ferramentas actuais:** [Excel / email / sistema X / manual]
**Frequência:** [Diária / semanal / por encomenda / etc.]
**Volumes:** [Número de registos, documentos, utilizadores envolvidos]

---

## 3. Problema ou Necessidade Identificada

[O que está a falhar no processo actual ou o que o cliente precisa de melhorar. Ser específico sobre a dor — não apenas "quer automatizar".]

- [Problema 1]: [Descrição e impacto]
- [Problema 2]: [Descrição e impacto]

---

## 4. Âmbito Incluído

[Lista dos processos, funcionalidades e integrações a implementar nesta fase. Ser específico — cada item deve ser verificável quando concluído.]

- [ ] [Item de âmbito 1 — descrição clara e verificável]
- [ ] [Item de âmbito 2 — descrição clara e verificável]
- [ ] [Item de âmbito 3 — descrição clara e verificável]

---

## 5. Âmbito Excluído

[O que não está incluído nesta fase. Evita expectativas erradas e scope creep.]

- [Exclusão 1] — motivo: [razão ou fase futura]
- [Exclusão 2] — motivo: [razão ou fase futura]

---

## 6. Pressupostos

[Condições assumidas como verdadeiras para que o âmbito e a estimativa sejam válidos. Se alguma não se verificar, o âmbito pode ser afectado.]

- [Pressuposto 1]: [ex: o cliente disponibiliza dados mestres limpos antes do arranque]
- [Pressuposto 2]: [ex: existe um interlocutor técnico do cliente disponível X horas/semana]

---

## 7. Entregáveis

[O que será entregue formalmente ao cliente no final do projecto ou desta fase.]

| Entregável | Descrição | Data Prevista |
|---|---|---|
| [Entregável 1] | [Descrição breve] | DD/MM/AAAA |
| [Entregável 2] | [Descrição breve] | DD/MM/AAAA |

---

## 8. Stakeholders

| Nome | Empresa | Papel | Disponibilidade |
|---|---|---|---|
| [Nome] | [Empresa] | [Decisor / Utilizador chave / Técnico] | [X horas/semana] |
| [Nome] | Parametro Global | [Gestor de projecto / Consultor] | — |

---

## 9. Pontos por Validar

[Questões em aberto que precisam de confirmação antes de fechar o âmbito ou avançar para implementação.]

- [ ] [Questão 1] — responsável: [Nome], prazo: DD/MM
- [ ] [Questão 2] — responsável: [Nome], prazo: DD/MM

---

## Histórico de Versões

| Versão | Data | Autor | Alterações |
|---|---|---|---|
| 1.0 | DD/MM/AAAA | [Nome] | Versão inicial |
