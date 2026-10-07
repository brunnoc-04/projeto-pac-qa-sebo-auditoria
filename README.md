# 🔍 Auditoria de QA para Sebos e Livrarias Independentes em Marketplaces

> Projeto PAC — TripleTen Brasil | Autor: **Brunno Cesar** — Analista de QA

Auditoria de qualidade aplicada à operação de um sebo que vende os mesmos livros
em dois canais — **Estante Virtual (EV)** e **Mercado Livre (ML)** — sem um
sistema integrador entre eles. A tese: **na ausência de integração, os canais
dessincronizam** (preços divergentes, anúncios ativos sem estoque, estado de
conservação inconsistente), gerando venda fantasma, mediação no SAC e perda de
reputação. A suíte **demonstra** essas falhas com evidência material e quantifica
a saúde financeira de cada anúncio.

---

## 🎯 Modelo operacional

**Escrita manual / verificação automatizada.**

- Os cenários de teste — inclusive **erros propositais** que demonstram a tese —
  são criados **manualmente** pelo analista nos canais.
- O **Playwright atua como observador puro**: navega nas vitrines públicas como
  um comprador, lê o estado visível dos anúncios (título, preço, contagem de
  fotos, descrição, presença/ausência) e compara entre canais.
- **Nenhum teste automatiza login, edição, pausa ou compra.**
- O login do Mercado Livre exige verificação humana (código por e-mail/WhatsApp/
  SMS, Face ID, QR code) — impraticável e proibida para automação. Por isso o ML
  é usado **somente em leitura (vitrine pública)**.

## 🧩 Escopo da suíte — 29 casos

| Frente | Foco | Casos | Status |
|---|---|---|---|
| **F1 — Sincronização de estoque** | Consistência cadastral e transacional entre canais; venda fantasma | TC-01 a TC-11 | Em execução |
| **F2 — Precificação** | Régua R$ 19, break-even e margem por anúncio | TC-12 a TC-17 | Em execução |
| **F3 — Fotos e avarias** | Padrão visual 2/4 fotos, dicionário de avarias, transparência | TC-18 a TC-26 | Em execução |
| **API — Postman (ML)** | Comparação página vs API (preço, status, fotos) | TC-27 a TC-29 | ⚠️ Condicionado |

> ⚠️ **Bloco API condicionado:** depende da aprovação de aplicação no portal de
> desenvolvedores do Mercado Livre para obter o token de acesso. Se não liberado
> em tempo hábil (corte: 12/10), os casos seguem como **Bloqueado por Ambiente**
> e as requisições montadas no Postman ficam como evidência documental.

## 🛠 Stack

| Ferramenta | Papel |
|---|---|
| **Python + Playwright** | Verificação automatizada de leitura nas vitrines (nenhuma escrita) |
| **Google Sheets** | Consolidação financeira com fórmulas auditáveis (preço digita-se, líquido calcula-se) |
| **Postman** | Requisições à API do ML — bloco condicionado ao token |
| **Jira** | Registro formal de achados com evidência |
| **GitHub** | Versionamento de scripts, docs e evidências |

## 📐 Regras de negócio (resumo)

- **Régua:** preço mínimo de venda **R$ 19** (política do dono)
- **Break-even:** ~R$ 5 (EV) / ~R$ 9,50 (ML)
- **Comissões:** EV 17% + mensalidade R$ 69/mês (faixa 501–2.000 livros) • ML Premium 16% + R$ 4 até R$ 79
- **Fotos:** 2 = bom estado • 4 = avaria evidenciada e descrita • 1 ou 3 = ERRO
- **Dicionário de avarias:** rasgo, grifo, mancha, oxidação, lombada gasta, amarelado, rasura, sublinhação, marcação

Detalhes completos: [Documentação de Requisitos e RNs](docs/requisitos-rns.html) e [Plano de Testes v2.0](docs/plano-de-testes.html).

## 📁 Estrutura

```text
├── docs/            # documentação v2.0 (requisitos, plano de testes)
├── playwright/      # suíte de automação
│   ├── data/        # massa de dados (L-01 a L-09, links das vitrines)
│   ├── pages/       # page objects
│   └── tests/       # casos de teste (TC-01 a TC-26)
├── postman/         # bloco API condicionado (ver nota acima)
├── sheets/          # referências da planilha de consolidação
├── jira/            # índice dos reportes de achados
└── evidencias/      # screenshots por ciclo: AAAA-MM-DD/TC-XX_L-YY_canal.png