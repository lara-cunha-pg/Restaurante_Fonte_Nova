# Template — Orçamento / Estimativa de Esforço

## Finalidade
Documento que apresenta a estimativa de esforço e custo para um conjunto de trabalhos definidos. Serve de base à aprovação do cliente, ao acompanhamento do consumo do contrato e à facturação.

## Tom de Discurso
- Preciso e objectivo — sem ambiguidades nas descrições de cada linha
- Cada item deve ser compreensível pelo cliente sem contexto técnico adicional
- Pressupostos e exclusões explícitos — protegem ambas as partes em caso de disputa
- Evitar linguagem que crie expectativas não garantidas ("deverá ser simples", "provavelmente")

## Instruções para o Agente
1. Basear a estimativa nas tarefas e âmbito definidos no `PG_CONTEXT.md`
2. Agrupar por área funcional, não por componente técnico — o cliente entende "Gestão de Compras" melhor que "modelo purchase.order"
3. Indicar sempre os pressupostos que sustentam cada estimativa
4. Listar explicitamente o que não está incluído
5. Não incluir estimativas para trabalhos fora do âmbito validado no `PG_CONTEXT.md` — criar secção separada se necessário
6. Marcar como `[POR VALIDAR]` qualquer item com incerteza significativa de esforço

---

## Estrutura do Documento

---

# [Nome do Projecto] — Estimativa de Esforço

**Versão:** 1.0
**Data:** DD/MM/AAAA
**Válido até:** DD/MM/AAAA
**Preparado por:** [Nome]
**Para aprovação de:** [Nome / Cargo / Empresa]

---

## Âmbito Coberto

[Resumo em 2 a 3 frases do que esta estimativa cobre. Referência à versão do documento de âmbito se existir.]

Esta estimativa cobre os trabalhos descritos no [Levantamento de Âmbito v1.0, DD/MM/AAAA].

---

## Detalhe de Esforço

| # | Área | Descrição do Trabalho | Esforço (dias) | Observações |
|---|---|---|---|---|
| 1 | [Área 1] | [Descrição clara e verificável] | [X] | |
| 2 | [Área 2] | [Descrição clara e verificável] | [X] | |
| 3 | [Área 3] | [Descrição clara e verificável] | [X] | [POR VALIDAR] |
| 4 | Gestão de projecto | Acompanhamento, reuniões, relatórios | [X] | |
| 5 | Formação e arranque | Formação de utilizadores, suporte go-live | [X] | |
| | | **Total** | **[X]** | |

---

## Pressupostos

[Condições assumidas como verdadeiras para que esta estimativa seja válida. Se alguma não se verificar, o esforço pode ser afectado e a estimativa revista.]

1. [Pressuposto 1 — ex: o cliente disponibiliza dados mestres em formato Excel limpo antes do início da migração]
2. [Pressuposto 2 — ex: as integrações com sistemas externos têm API documentada e disponível]
3. [Pressuposto 3 — ex: existe um interlocutor do cliente disponível pelo menos X horas por semana para validações]
4. [Pressuposto 4 — ex: o âmbito não inclui desenvolvimentos custom além dos listados]

---

## Exclusões

[O que não está incluído nesta estimativa. Evitar ambiguidades sobre o que o cliente recebe.]

- [Exclusão 1 — ex: migração de dados históricos para além de X anos]
- [Exclusão 2 — ex: integrações com sistemas não listados no âmbito]
- [Exclusão 3 — ex: formação de utilizadores adicionais para além dos X previstos]
- Suporte pós go-live (coberto por contrato de suporte separado)

---

## Condições

- Esta estimativa tem uma margem de variação de **±[X]%** para trabalhos de análise, configuração e testes.
- Desenvolvimentos custom têm estimativa própria sujeita a especificação técnica detalhada previamente aprovada.
- Trabalhos fora do âmbito desta estimativa serão orçamentados separadamente antes de serem iniciados.
- Validade desta estimativa: [DD/MM/AAAA]. Após esta data, os valores podem ser revistos.

---

## Aprovação

| | Parametro Global | Cliente |
|---|---|---|
| **Nome** | [Nome] | [Nome] |
| **Cargo** | [Cargo] | [Cargo] |
| **Data** | | |
| **Assinatura** | | |
