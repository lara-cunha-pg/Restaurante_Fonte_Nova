# PG_FIT_GAP_FRAMING_PROMPT

Quero que operes em modo de **fit-gap framing consultivo** para este projeto.

Usa como input o que ja saiu do discovery e, quando existir, o `PG_CONTEXT.md`.
O objetivo deste modo nao e decidir ja a solucao final.
O objetivo e **mapear rapidamente o encaixe da necessidade no Odoo antes da decisao consultiva**, distinguindo o que parece coberto, o que ainda e gap e o que continua por validar.

---

## 1. Fontes obrigatorias

Antes de fechar este framing, consulta obrigatoriamente:

1. `PG_CONTEXT.md`
2. codigo do projeto
3. `vendor/odoo_src`
4. documentacao oficial da versao ativa

Se houver conflito entre memoria geral, discovery resumido e evidencia do projeto, prevalece sempre a evidencia.

---

## 2. Regra de disciplina neste modo

Neste modo:

- nao decides ainda a solucao final
- nao classificas ainda a recomendacao como standard, modulo adicional, Studio ou custom
- nao assumes que uma area Odoo potencialmente impactada ja e uma solucao validada

Separa sempre explicitamente:

- `FACTO OBSERVADO`
- `INFERENCIA`
- `PONTO POR VALIDAR`

---

## 3. O que tens de mapear

Mapeia explicitamente:

- necessidade ou objetivo
- fit standard observado no projeto
- fit standard adicional potencial no Odoo
- fit potencial via Studio
- gaps reais observados
- pontos por validar
- risco de decidir cedo demais
- proximo passo recomendado

---

## 4. Como interpretar areas impactadas

Se no discovery tiverem surgido areas Odoo potencialmente impactadas, usa-as apenas como orientacao de framing.
Nao trates "area impactada" como equivalente a "solucao encontrada".
O objetivo aqui e perceber o encaixe provavel e a natureza do gap, nao fechar a implementacao.

---

## 5. Formato minimo esperado na resposta

Responde com esta estrutura:

1. **Necessidade / objetivo**
2. **FACTOS OBSERVADOS**
3. **INFERENCIAS**
4. **PONTOS POR VALIDAR**
5. **Areas Odoo potencialmente impactadas**
6. **Mapa de fit e gaps**
   - fit standard observado no projeto
   - fit standard adicional potencial no Odoo
   - fit potencial via Studio
   - gaps reais observados
7. **Risco de decidir cedo demais**
8. **Proximo passo recomendado**
9. **Fecho obrigatorio**

---

## 6. Fecho obrigatorio

No fim do framing, escolhe apenas um:

- `FIT MAIORITARIAMENTE STANDARD`
- `FIT STANDARD COM VALIDACAO ADICIONAL`
- `GAP RELEVANTE AINDA POR CONFIRMAR`
- `NAO HA BASE SUFICIENTE PARA DECISAO`

Se o fecho nao permitir ainda decisao consultiva, explica claramente o que falta validar antes de passar para recomendacao.
