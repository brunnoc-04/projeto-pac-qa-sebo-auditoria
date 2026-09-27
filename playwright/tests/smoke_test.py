from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://www.estantevirtual.com.br")
    page.screenshot(path="../../print_inicial.png")
    browser.close()
    print("TESTE DE FUMACA PASSOU! Ambiente funcionando.")