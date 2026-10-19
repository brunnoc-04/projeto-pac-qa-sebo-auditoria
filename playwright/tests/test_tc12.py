# -*- coding: utf-8 -*-
# TC-12: Livro entre R$ 12,00 e R$ 14,99 (classe de equivalência da subfaixa inferior)
# Livro 8 'Café com o Criador do Universo 2026' — R$ 12,00 na lista, lucro esperado 5,96
# Passos: 1) aplicar filtro de preço abaixo de R$ 15,00 na vitrine 2) localizar o Livro 8
#         3) conferir preço exibido vs lista 4) registrar na planilha (lucro, classificação)
#         5) constatar violação da RN-01 (preço < mínimo 19) e classificação RN-04 (saldo <= 10)
# Estratégia em camadas (herdada do TC-11, 4 rodadas de diagnóstico):
#   o filtro da EV aplica limites INTEIROS com fidelidade, mas o máximo DECIMAL não
#   propaga para o estado do filtro sob automação (valor fica no campo, página ignora).
#   Camada 1: faixa 12 a 14.99 (fill em lote + Enter único)
#   Camada 2: só mínimo 12 (inteiro — aplica com fidelidade)
#   Camada 3: sem filtro (vitrine inteira)
#   O veredito (RN-01/RN-04) independe do estado do filtro: o Livro 8 está à venda.
# Diagnóstico por contagem: 4 cards = faixa aplicou; 19 cards = máximo não aplicou
#   (com mínimo 12 nada é excluído: todos os 19 visíveis custam >= 12 — os 2 abaixo
#   são invisíveis pela plataforma, achado EV-01 do TC-24).
# Nota do caso: R$ 12,00 VISÍVEL corrobora o limiar inclusivo do EV-01 pelo outro lado.
# Padrão da suíte: goto domcontentloaded, comparação numérica (\xa0), leitura forense

import json
import os
import re
from playwright.sync_api import sync_playwright

CAMINHO_JSON = "playwright/data/livros.json"
PASTA_EVIDENCIA = "evidencias/2026-10-19"

# Locators herdados da Frente 1 + filtro calibrado no codegen de 19/10
CARDS = ".product-list__items .product-item"

ID_ALVO = "L-08"
PRECO_MINIMO = "12"
PRECO_MAXIMO = "14.99"
MINIMO_VENDA = 19.00  # RN-01: mínimo de venda definido pelo dono
META_OPERACIONAL = 10.00  # RN-04: verde somente com saldo acima de 10


def preco_para_float(texto):
    # Converte 'R$ 12,00' (com espaço comum ou invisível \xa0) em 12.00
    limpo = texto.replace("R$", "").replace("\xa0", "").replace(" ", "")
    limpo = limpo.replace(".", "").replace(",", ".")
    return float(limpo)


def fmt_brl(valor):
    # 12.0 -> 'R$ 12,00' (padrão pt-BR no log)
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

    # ---- CAMADA 1: faixa 12 a 14.99 (fill em lote + UM único Enter) ----
    abrir_vitrine(pagina, url_vitrine)
    campo_minimo = pagina.get_by_role("spinbutton", name="Mínimo:")
    campo_minimo.fill(PRECO_MINIMO)
    campo_maximo = pagina.get_by_role("spinbutton", name="Máximo:")
    campo_maximo.fill(PRECO_MAXIMO)
    campo_minimo.press("Enter")
    pagina.wait_for_timeout(2000)
    print(f"Camada 1: filtro preenchido {PRECO_MINIMO} a {PRECO_MAXIMO} (um único Enter)")

    val_min, val_max = ler_campos(pagina)
    print(f"Campos do filtro após aplicar: Mínimo='{val_min}' | Máximo='{val_max}'")

    total_cards = rolar_e_contar(pagina)
    anuncios = pagina.locator(CARDS).filter(has_text=termo)
    total_anuncios = anuncios.count()
    print(f"Camada 1: total de cards nos resultados: {total_cards} | anúncios do Livro 8: {total_anuncios}")
    print("Esperado na faixa 12,00-14,99: 4 cards (Livros 3, 8, 13 e 19 da lista)")
    if total_cards == 19:
        print("ATENÇÃO: 19 cards = o máximo decimal não aplicou (comportamento documentado no TC-11); com mínimo 12 nada é excluído — todos os visíveis custam >= 12")

    # ---- CAMADA 2: só mínimo 12 (inteiro — aplica com fidelidade, lição do TC-11) ----
    if total_anuncios == 0:
        print("ATENÇÃO: Livro 8 não localizado na Camada 1 — recarregando e aplicando só o mínimo 12")
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
        print(f"Camada 2: total de cards nos resultados: {total_cards} | anúncios do Livro 8: {total_anuncios}")

    # ---- CAMADA 3: sem filtro (vitrine inteira) ----
    if total_anuncios == 0:
        print("ATENÇÃO: Livro 8 não localizado na Camada 2 — recarregando sem filtro")
        abrir_vitrine(pagina, url_vitrine)
        val_min, val_max = ler_campos(pagina)
        total_cards = rolar_e_contar(pagina)
        anuncios = pagina.locator(CARDS).filter(has_text=termo)
        total_anuncios = anuncios.count()
        print(f"Camada 3: total de cards nos resultados: {total_cards} | anúncios do Livro 8: {total_anuncios}")

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
                    print(f"TC-12: REPROVADO — anúncio à venda por {fmt_brl(valor_card)}, abaixo do mínimo de venda de R$ 19,00 (RN-01)")
                    print("Achado vai para o Jira; ressalva RN-03: o livreiro confirma se é promoção antes de qualquer ação corretiva")
                else:
                    print("TC-12: Aprovado — preço dentro do mínimo de venda (RN-01)")

                # Nota EV-01: o limiar inclusivo do piso da plataforma, corroborado pelo outro lado
                if abs(valor_card - 12.00) < 0.005:
                    print("Nota EV-01: R$ 12,00 VISÍVEL na vitrine — exatamente no piso da plataforma o anúncio existe (limiar inclusivo confirmado)")

                # Classificação RN-04 (régua de rentabilidade)
                lucro = 0.83 * livro["preco"] - 4.00
                if lucro > META_OPERACIONAL:
                    classificacao = "verde (saldo > R$ 10,00)"
                else:
                    classificacao = "saldo positivo de até R$ 10,00 (RN-04 — não é verde)"
                print(f"Lucro pela fórmula (0,83 x preço - 4,00): {fmt_brl(lucro)} — {classificacao}; registrar na planilha")
            except ValueError:
                print("ATENÇÃO: preço do card ilegível:", repr(preco_encontrado))
    else:
        print("TC-12: ATENÇÃO: Livro 8 NÃO localizado em nenhuma camada (conferir evidência)")

    # EVIDÊNCIA
    os.makedirs(PASTA_EVIDENCIA, exist_ok=True)
    pagina.screenshot(path=f"{PASTA_EVIDENCIA}/TC-12_livro08_filtro_preco.png", full_page=True)
    print("Evidência salva em:", PASTA_EVIDENCIA)

    contexto.close()
    navegador.close()