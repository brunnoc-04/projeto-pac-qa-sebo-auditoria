# -*- coding: utf-8 -*-
# TC-11: Livro entre R$ 15,00 e R$ 18,99 (classe de equivalência da subfaixa intermediária)
# Livro 11 'Patinando no Gelo de Europa' — R$ 18,00 na lista, lucro esperado 10,94
# Passos: 1) aplicar filtro de preço 15,00 a 18,99 na vitrine 2) localizar o Livro 11
#         3) conferir preço exibido vs lista 4) registrar na planilha (lucro, classificação)
#         5) constatar a violação do mínimo de venda (RN-01) — achado vai para o Jira
# v4 (19/10/2026): estratégia em camadas para o filtro, após 3 rodadas de diagnóstico:
#   rodada 1: fill '18.99' DEPOIS do Enter no mínimo → máximo ignorado (15 cards;
#             hipótese: o re-render do Enter descarta o vínculo do máximo)
#   v2: fill '18,99' (vírgula) → rejeitado pelo navegador (input[type=number], formato estrito)
#   v3: digitação caractere a caractere → estados intermediários inválidos (máx < mín)
#       alimentam o clamp do slider → campos terminam em 45/45 (1 card: o livro de R$ 45)
#   Camada 1 (v4): fill nos DOIS campos antes de qualquer Enter (sem re-render no meio;
#       máximo com ponto — formato canônico aceito pelo navegador via fill) + UM único Enter
#   Camada 2 (fallback provado na rodada 1): recarrega a página (estado padrão 12/45)
#       e aplica só o mínimo (15) — o livro é localizado entre os resultados >= 15
# Padrão da suíte embutido: goto domcontentloaded (flake), comparação numérica (\xa0),
# diagnóstico de filtro, leitura forense dos campos (#inputValueMin / #inputValueMax)

import json
import os
import re
from playwright.sync_api import sync_playwright

CAMINHO_JSON = "playwright/data/livros.json"
PASTA_EVIDENCIA = "evidencias/2026-10-19"

# Locators herdados da Frente 1 + filtro calibrado no codegen de 19/10
CARDS = ".product-list__items .product-item"

ID_ALVO = "L-11"
PRECO_MINIMO = "15"
PRECO_MAXIMO = "18.99"  # ponto: formato canônico do input[type=number] via fill
MINIMO_VENDA = 19.00  # RN-01: mínimo de venda definido pelo dono


def preco_para_float(texto):
    # Converte 'R$ 18,00' (com espaço comum ou invisível \xa0) em 18.00
    limpo = texto.replace("R$", "").replace("\xa0", "").replace(" ", "")
    limpo = limpo.replace(".", "").replace(",", ".")
    return float(limpo)


def fmt_brl(valor):
    # 18.0 -> 'R$ 18,00' (padrão pt-BR no log)
    return f"R$ {valor:.2f}".replace(".", ",")


def ler_campos(pagina):
    # Leitura forense: o que está de fato gravado nos inputs (a única verdade)
    val_min = pagina.evaluate("() => { const el = document.querySelector('#inputValueMin'); return el ? el.value : 'campo não encontrado'; }")
    val_max = pagina.evaluate("() => { const el = document.querySelector('#inputValueMax'); return el ? el.value : 'campo não encontrado'; }")
    return val_min, val_max


def abrir_vitrine(pagina, url):
    pagina.goto(url, wait_until="domcontentloaded")
    pagina.wait_for_timeout(2000)
    print("Vitrine carregada (DOM pronto)")
    try:
        pagina.locator("g > path").click(timeout=8000)
        print("Pop-up de aniversário fechado")
    except Exception:
        print("Pop-up não apareceu, seguindo")


def rolar_e_contar(pagina):
    # Rolagem progressiva antes de ler (carregamento preguiçoso, lição do TC-08)
    altura_total = pagina.evaluate("document.body.scrollHeight")
    posicao = 0
    while posicao < altura_total:
        posicao += 600
        pagina.evaluate(f"window.scrollTo(0, {posicao})")
        pagina.wait_for_timeout(400)
        altura_total = pagina.evaluate("document.body.scrollHeight")
    pagina.evaluate("window.scrollTo(0, 0)")
    pagina.wait_for_timeout(1000)
    return pagina.locator(CARDS).count()


with open(CAMINHO_JSON, encoding="utf-8") as arquivo:
    dados = json.load(arquivo)

url_vitrine = dados["vitrine_ev"]

# Achar o livro pelo id (padrão da suíte)
livro = None
for item in dados["livros"]:
    if item["id"] == ID_ALVO:
        livro = item
if livro is None:
    print(f"ATENÇÃO: o id {ID_ALVO} não existe no livros.json (validar a massa)")
    raise SystemExit

termo = livro["titulo"][:20]
print(f"Testando {livro['id']}: {livro['titulo']} (preço na lista: {fmt_brl(livro['preco'])})")

with sync_playwright() as p:

    navegador = p.chromium.launch(headless=False)
    contexto = navegador.new_context(locale="pt-BR")
    pagina = contexto.new_page()

    # ---- CAMADA 1: fill nos dois campos + UM único Enter no fim ----
    abrir_vitrine(pagina, url_vitrine)
    campo_minimo = pagina.get_by_role("spinbutton", name="Mínimo:")
    campo_minimo.fill(PRECO_MINIMO)
    campo_maximo = pagina.get_by_role("spinbutton", name="Máximo:")
    campo_maximo.fill(PRECO_MAXIMO)
    campo_minimo.press("Enter")  # único Enter, DEPOIS dos dois fills
    pagina.wait_for_timeout(2000)
    print(f"Camada 1: filtro preenchido {PRECO_MINIMO} a {PRECO_MAXIMO} (um único Enter)")

    val_min, val_max = ler_campos(pagina)
    print(f"Campos do filtro após aplicar: Mínimo='{val_min}' | Máximo='{val_max}'")

    total_cards = rolar_e_contar(pagina)
    anuncios = pagina.locator(CARDS).filter(has_text=termo)
    total_anuncios = anuncios.count()
    print(f"Camada 1: total de cards nos resultados: {total_cards} | anúncios do Livro 11: {total_anuncios}")
    print("Esperado na faixa 15,00-18,99: ~4 cards (Livros 2, 7, 11 e 17 da lista)")

    # ---- CAMADA 2 (fallback provado na rodada 1): recarrega e aplica só o mínimo ----
    if total_anuncios == 0:
        print("ATENÇÃO: Livro 11 não localizado na Camada 1 — recarregando e aplicando o caminho provado (só mínimo)")
        abrir_vitrine(pagina, url_vitrine)
        campo_minimo = pagina.get_by_role("spinbutton", name="Mínimo:")
        campo_minimo.fill(PRECO_MINIMO)
        campo_minimo.press("Enter")
        pagina.wait_for_timeout(2000)
        val_min, val_max = ler_campos(pagina)
        print(f"Campos do filtro (Camada 2): Mínimo='{val_min}' | Máximo='{val_max}'")
        total_cards = rolar_e_contar(pagina)
        anuncios = pagina.locator(CARDS).filter(has_text=termo)
        total_anuncios = anuncios.count()
        print(f"Camada 2: total de cards nos resultados: {total_cards} | anúncios do Livro 11: {total_anuncios}")
        print("Estado esperado: só-mínimo (~15 cards = 11 >= 19 + 4 da subfaixa) — desvio documentado no protocolo")

    print(f"Estado final do filtro: Mínimo='{val_min}' | Máximo='{val_max}'")

    # ---- LEITURA DO CARD E VEREDITO ----
    if total_anuncios > 0:
        texto_card = anuncios.first.inner_text()
        print("Texto do card:", texto_card.replace("\n", " | ")[:200])

        preco_card = re.search(r"R\$\s*[\d.,]+", texto_card)
        if preco_card:
            preco_encontrado = preco_card.group(0)
            print("Preço publicado no card:", preco_encontrado)
            try:
                valor_card = preco_para_float(preco_encontrado)
                if abs(valor_card - livro["preco"]) < 0.005:
                    print("Preço CONSISTENTE com a Lista do Livreiro")
                else:
                    print(f"ATENÇÃO: preço na vitrine ({fmt_brl(valor_card)}) difere da lista ({fmt_brl(livro['preco'])})")

                # Veredito do caso — política de precificação (RN-01)
                if valor_card < MINIMO_VENDA:
                    print(f"TC-11: REPROVADO — anúncio à venda por {fmt_brl(valor_card)}, abaixo do mínimo de venda de R$ 19,00 (RN-01)")
                    print("Achado vai para o Jira; ressalva RN-03: o livreiro confirma se é promoção antes de qualquer ação corretiva")
                else:
                    print("TC-11: Aprovado — preço dentro do mínimo de venda (RN-01)")
            except ValueError:
                print("ATENÇÃO: preço do card ilegível:", repr(preco_encontrado))

        # Apoio ao registro na planilha
        lucro = 0.83 * livro["preco"] - 4.00
        classificacao = "verde (saldo > R$ 10,00)" if lucro > 10.00 else "saldo <= R$ 10,00"
        print(f"Lucro pela fórmula (0,83 x preço - 4,00): {fmt_brl(lucro)} — {classificacao}; registrar na planilha")
    else:
        print("TC-11: ATENÇÃO: Livro 11 NÃO localizado nem na Camada 2 (conferir evidência)")

    # EVIDÊNCIA
    os.makedirs(PASTA_EVIDENCIA, exist_ok=True)
    pagina.screenshot(path=f"{PASTA_EVIDENCIA}/TC-11_livro11_filtro_preco.png", full_page=True)
    print("Evidência salva em:", PASTA_EVIDENCIA)

    contexto.close()
    navegador.close()