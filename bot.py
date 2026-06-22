# Bot
import ccxt
import pandas as pd
import time

# 2. COLOCA AS TUAS CHAVES AQUI NO MEIO DAS ASPAS
API_KEY = 'QPGBolG9cGExuKnJh2H1MnyIh9/GFRh/pKv1Z2RX52ua6UJU7hYI71uX'
SECRET_KEY = 'nypDQz1h9RAwThad251/YTTR6JDBXEHinbwckGdjk6iYoko50YA3yW1bWtuzgYOJE/Q5cSmkYD7OxIbCKN5dIQ=='

# 3. PARÂMETROS ESTRATÉGICOS DE LUCRO E FILTRO
MIN_POR_TRADE = 20.0          
PISO_MINIMO_LUCRO = 1.0130    
RECUO_TRAILING = 0.0005        
PRECO_MAXIMO_MOEDA = 5.0      

print(f"🚀 BOT ULTRA-VOLATILIDADE INICIADO!")

# Conectar à API da Kraken Pro
exchange = ccxt.kraken({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'enableRateLimit': True,
})

moedas_compradas = {}

def obter_saldo_usd_real():
    try:
        saldo = exchange.fetch_balance()
        return float(saldo['total'].get('USD', 0.0))
    except Exception as e:
        print(f"❌ Erro ao ler saldo na Kraken: {e}")
        return 0.0

def escanear_moedas_volateis():
    try:
        tickers = exchange.fetch_tickers()
        dados_mercado = []
        for par, info in tickers.items():
            if par.endswith('/USD') and 'USDT' not in par and 'USDC' not in par:
                preco_atual = info['close']
                if preco_atual <= PRECO_MAXIMO_MOEDA:
                    mudanca_24h = info.get('percentage', 0)
                    if abs(mudanca_24h) > 2.0:
                        dados_mercado.append({'par': par, 'mudanca': abs(mudanca_24h), 'preco': preco_atual})
        df = pd.DataFrame(dados_mercado).sort_values(by='mudanca', ascending=False)
        return df.head(10)
    except Exception as e:
        return pd.DataFrame()

# 5. LOOP PRINCIPAL
while True:
    print("\n--- [Ciclo de Verificação e Trailing] ---")
    CAPITAL_TOTAL_ATUAL = obter_saldo_usd_real()
    if CAPITAL_TOTAL_ATUAL < MIN_POR_TRADE:
        CAPITAL_TOTAL_ATUAL = 200.0
    
    if moedas_compradas:
        for par in list(moedas_compradas.keys()):
            try:
                ticker = exchange.fetch_ticker(par)
                preco_atual = ticker['close']
                dados = moedas_compradas[par]
                
                if preco_atual > dados['preco_maximo']:
                    moedas_compradas[par]['preco_maximo'] = preco_atual
                
                lucro_atual_fator = preco_atual / dados['preco_compra']
                topo_maximo = moedas_compradas[par]['preco_maximo']
                
                if lucro_atual_fator >= PISO_MINIMO_LUCRO:
                    preco_gatilho_venda = topo_maximo * (1 - RECUO_TRAILING)
                    if preco_atual <= preco_gatilho_venda:
                        lucro_final = ((preco_atual / dados['preco_compra']) - 1) * 100
                        if lucro_final >= 1.30:
                            print(f"💰 VENDENDO {par} com lucro de +{lucro_final:.2f}%!")
                            exchange.create_market_sell_order(par, dados['quantidade'])
                            del moedas_compradas[par]
            except Exception as e:
                print(f"❌ Erro no trailing: {e}")

    if len(moedas_compradas) < 10:
        top_moedas = escanear_moedas_volateis()
        if not top_moedas.empty:
            total_moedas = len(top_moedas)
            capital_dinamico = CAPITAL_TOTAL_ATUAL / total_moedas
            if capital_dinamico < MIN_POR_TRADE:
                capital_dinamico = MIN_POR_TRADE
                
            for index, row in top_moedas.iterrows():
                par_candidato = row['par']
                preco_atual = row['preco']
                
                if par_candidato not in moedas_compradas and (len(moedas_compradas) * capital_dinamico) < CAPITAL_TOTAL_ATUAL:
                    try:
                        quantidade = capital_dinamico / preco_atual
                        print(f"🛒 COMPRA REAL: {capital_dinamico:.2f} USD em {par_candidato}...")
                        exchange.create_market_buy_order(par_candidato, quantity = quantidade)
                        moedas_compradas[par_candidato] = {
                            'preco_compra': preco_atual,
                            'preco_maximo': preco_atual,
                            'quantidade': quantidade
                        }
                    except Exception as e:
                        print(f"❌ Erro na compra: {e}")
    time.sleep(15)
