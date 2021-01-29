import trio
import httpx
import json
from datetime import datetime, timedelta
from dateutil import tz

bit2me_currencies = ["BTC", "BCH", "ETH", "LTC", "DASH", "XRP", "ADA", "LINK", "COMP", "ATOM", "DAI", "XMR", "OMG", "DOT", "SC", "XLM", "USDT", "USDC", "ZEC", "XTZ", "UNI"]

def get_bit2me_endpoint():
    # https://gateway.bit2me.com/v1/currency/convert?
    #   from=BTC,BCH,ETH,LTC,DASH,XRP,ADA,LINK,COMP,ATOM,DAI,XMR,OMG,DOT,SC,XLM,USDT,USDC,ZEC,XTZ,UNI
    #   &to=EUR
    #   &value=1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1
    #   &time=2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z,2020-11-03T22:54:00.000Z
    bit2me_endpoint = "https://gateway.bit2me.com/v1/currency/convert?"
    
    bit2me_endpoint += "from="
    for currency in bit2me_currencies:
        bit2me_endpoint += currency + ","
    bit2me_endpoint = bit2me_endpoint[:-1]
    
    bit2me_endpoint += "&to=EUR"

    bit2me_endpoint += "&value="
    for currency in bit2me_currencies:
        bit2me_endpoint += "1,"
    bit2me_endpoint = bit2me_endpoint[:-1]
    
    bit2me_endpoint += "&time="
    timezone_diff = timedelta(hours=3)
    current_timestamp = datetime.now(tz=None) + timezone_diff
    current_timestamp = current_timestamp.strftime("%Y-%m-%dT%H:%M:00.000Z")
    for currency in bit2me_currencies:
        bit2me_endpoint += str(current_timestamp) + ","
    bit2me_endpoint = bit2me_endpoint[:-1]

    return bit2me_endpoint

endpoints = {
    "bit2me": "https://api.bit2me.com/v1/ticker2/",
    "bit2me_new": get_bit2me_endpoint(),
    "ripio": "https://app.ripio.com/api/v3/rates/?country=AR",
    "satoshitango": "https://api.satoshitango.com/v3/ticker/ARS",
    "buenbit": "https://be.buenbit.com/api/market/tickers/",
    "argenbtc": "https://argenbtc.com/cotizacion",
    "qubit": "https://www.qubit.com.ar/c_unvalue" # only selling price
    #"qubit": "https://www.qubit.com.ar/c_value" # only buying price
}

async def run_requests(endpoints):

    rates_info = {}

    async def get_request(exchange, url, client):
        res = await client.get(url)
        rates_info[exchange] = json.loads(res.text)

    async with httpx.AsyncClient() as client:
        async with trio.open_nursery() as nursery:
            for exchange, url in endpoints.items():
                nursery.start_soon(get_request, exchange, url, client)

    return rates_info


def has_key(dict, key):
    try:
        x = dict[key]
        return True
    except KeyError:
        return False


def process_info_bit2me(requests_res, rates):
    bit2me_ticker = requests_res["bit2me"]["data"]
    for item in bit2me_ticker:
        currency = item["symbol"]
        if has_key(rates, currency) == False:
            rates[currency] = {}
        rates[currency]["buy"] = item["buy"]
        rates[currency]["network_fee"] = item["network_fee"]


def process_info_bit2me_new(requests_res, rates):
    bit2me_new_ticker = requests_res["bit2me_new"]
    for i in range(len(bit2me_new_ticker)):
        currency = bit2me_currencies[i]
        if has_key(rates, currency) == False:
            rates[currency] = {}
        rates[currency]["buy"] = bit2me_new_ticker[i]
        if has_key(rates[currency], "network_fee") == False:
            rates[currency]["network_fee"] = 0


def process_info_ripio(requests_res, rates):
    ripio_ticker = requests_res["ripio"]
    for item in ripio_ticker:
        currency = item["ticker"][:-4]
        if has_key(rates, currency) == False:
            rates[currency] = {}
        if has_key(rates[currency], "sell") == False:
            rates[currency]["sell"] = {}
        rates[currency]["sell"]["ripio"] = item["sell_rate"]
        if has_key(rates[currency], "commission") == False:
            rates[currency]["commission"] = {}
        rates[currency]["commission"]["ripio"] = 0.01


def process_info_satoshitango(requests_res, rates):
    satoshitango_ticker = requests_res["satoshitango"]["data"]["ticker"]
    for currency, info in satoshitango_ticker.items():
        if has_key(rates, currency) == False:
            rates[currency] = {}
        if has_key(rates[currency], "sell") == False:
            rates[currency]["sell"] = {}
        rates[currency]["sell"]["satoshitango"] = info["bid"]
        if has_key(rates[currency], "commission") == False:
            rates[currency]["commission"] = {}
        rates[currency]["commission"]["satoshitango"] = 0.01


def process_info_buenbit(requests_res, rates):
    buenbit_ticker = requests_res["buenbit"]["object"]
    for currency_pair, info in buenbit_ticker.items():
        if currency_pair[-3:] == "ars":
            currency = currency_pair[:-3].upper()
            if has_key(rates, currency) == False:
                rates[currency] = {}
            if has_key(rates[currency], "sell") == False:
                rates[currency]["sell"] = {}
            rates[currency]["sell"]["buenbit"] = info["purchase_price"]
            if has_key(rates[currency], "commission") == False:
                rates[currency]["commission"] = {}
            rates[currency]["commission"]["buenbit"] = 0 # comisión incluida en el precio


def process_info_argenbtc(requests_res, rates):
    argenbtc_ticker = requests_res["argenbtc"]
    currency = "BTC"
    if has_key(rates, currency) == False:
      rates[currency] = {}
    if has_key(rates[currency], "sell") == False:
      rates[currency]["sell"] = {}
    text_rate = argenbtc_ticker["precio_venta_f"]
    rates[currency]["sell"]["argenbtc"] = text_rate.replace(".", "").replace(",", ".")
    if has_key(rates[currency], "commission") == False:
      rates[currency]["commission"] = {}
    rates[currency]["commission"]["argenbtc"] = 0 # comisión incluida en el precio


def process_info_qubit(requests_res, rates):
    qubit_ticker = requests_res["qubit"]
    for currency, info in qubit_ticker.items():
        if has_key(rates, currency) == False:
            rates[currency] = {}
        if has_key(rates[currency], "sell") == False:
            rates[currency]["sell"] = {}
        rates[currency]["sell"]["qubit"] = info[2]
        if has_key(rates[currency], "commission") == False:
            rates[currency]["commission"] = {}
        rates[currency]["commission"]["qubit"] = 0.01


def check_rates(EUR_amount):

    # requests_res = trio.run(run_requests, endpoints)
    requests_res = {'bit2me_new': [12186.462522, 208.3010982, 345.94368119999996, 47.51205419999999, 55.5046167, 0.20437088879999998, 0.08168782517999999, 9.0383647926, 75.5094678, 3.774279834, 0.8608266887999999, 100.3695342, 2.4143071734599997, 3.5232920579999996, 0.0020290452000000002, 0.06399762017999999, 0.853477794, 0.852625254, 46.412277599999996, 1.615051776, 1.65904284], 'bit2me': {'code': 200, 'data': [{'symbol': 'BTC', 'name': 'Bitcoin', 'base': 'EUR', 'buy': 12535.2, 'buy_url': 'https://bit2me.com/buy-bitcoin', 'sell': 11805, 'sell_url': 'https://bit2me.com/sell-bitcoin', 'active': True, 'network_fee': 0.0002, 'icon': 'https://bit2me.com/assets/images/crypto-logos/btc.svg'}, {'symbol': 'ETH', 'name': 'Ethereum', 'base': 'EUR', 'buy': 357.01, 'buy_url': 'https://bit2me.com/buy-ethereum', 'sell': 336.21, 'sell_url': 'https://bit2me.com/sell-ethereum', 'active': True, 'network_fee': 0.008, 'icon': 'https://bit2me.com/assets/images/crypto-logos/eth.svg'}, {'symbol': 'LTC', 'name': 'Litecoin', 'base': 'EUR', 'buy': 49, 'buy_url': 'https://bit2me.com/buy-litecoin', 'sell': 46.14, 'sell_url': 'https://bit2me.com/sell-litecoin', 'active': True, 'network_fee': 0.02, 'icon': 'https://bit2me.com/assets/images/crypto-logos/ltc.svg'}, {'symbol': 'BCH', 'name': 'Bitcoin Cash', 'base': 'EUR', 'buy': 214.55, 'buy_url': 'https://bit2me.com/buy-bitcoin-cash', 'sell': 202.05, 'sell_url': 'https://bit2me.com/sell-bitcoin-cash', 'active': True, 'network_fee': 0.003, 'icon': 'https://bit2me.com/assets/images/crypto-logos/bch.svg'}, {'symbol': 'DASH', 'name': 'Dash', 'base': 'EUR', 'buy': 57.16, 'buy_url': 'https://bit2me.com/buy-dash', 'sell': 53.83, 'sell_url': 'https://bit2me.com/sell-dash', 'active': True, 'network_fee': 0.001, 'icon': 'https://bit2me.com/assets/images/crypto-logos/dash.svg'}]}, 'satoshitango': {'data': {'ticker': {'BTC': {'date': '2020-11-05 02:23:02', 'timestamp': 1604542982, 'bid': 2133245.36, 'ask': 2248864.53, 'high': 0, 'low': 0, 'volume': 0}, 'ETH': {'date': '2020-11-05 02:23:02', 'timestamp': 1604542982, 'bid': 60565.95, 'ask': 64050.19, 'high': 0, 'low': 0, 'volume': 0}, 'LTC': {'date': '2020-11-05 02:23:02', 'timestamp': 1604542982, 'bid': 8280.2, 'ask': 8800.39, 'high': 0, 'low': 0, 'volume': 0}, 'XRP': {'date': '2020-11-05 02:23:02', 'timestamp': 1604542982, 'bid': 35.82, 'ask': 37.76, 'high': 0, 'low': 0, 'volume': 0}, 'BCH': {'date': '2020-11-05 02:23:02', 'timestamp': 1604542982, 'bid': 36372.76, 'ask': 38455.91, 'high': 0, 'low': 0, 'volume': 0}, 'DAI': {'date': '2020-11-05 02:23:02', 'timestamp': 1604542982, 'bid': 150.29, 'ask': 159.54, 'high': 0, 'low': 0, 'volume': 0}, 'USDC': {'date': '2020-11-05 02:23:02', 'timestamp': 1604542982, 'bid': 149.58, 'ask': 157.29, 'high': 0, 'low': 0, 'volume': 0}}, 'code': 'success'}}, 'qubit': {'BTC': [1, '14274.6500', '2119785.5250', '3.2333'], 'NEO': ['0.001004087665897237410374334922', '14.3330', '2128.4505', '-1.1654'], 'QTUM': ['0.0001292501042057073203195875205', '1.8450', '273.9825', '-0.3241'], 'ADA': ['0.000006699288599019940944261330400', '0.0956', '14.2011', '2.9941'], 'EOS': ['0.0001663718550016988157327850420', '2.3749', '352.6726', '1.2276'], 'IOTA': ['0.00001670794029976216579741009412', '0.2385', '35.4172', '-2.6531'], 'XLM': ['0.000005240058425250356401032599749', '0.0748', '11.1078', '-0.1068'], 'ETC': ['0.0003426493819463174228439926723', '4.8912', '726.3432', '1.1143'], 'ICX': ['0.00002206709096195003029846616204', '0.3150', '46.7775', '1.0263'], 'BNB': ['0.001920964787227707859737366590', '27.4211', '4072.0334', '2.7011'], 'ETH': ['0.02844202835095781682913416441', '406.0000', '60291.0000', '5.8477'], 'LINK': ['0.0007404734967232121277929756596', '10.5700', '1569.6450', '3.0094'], 'BCH': ['0.01706871972342579327689295359', '243.6500', '36182.0250', '0.5904'], 'USDT': ['0.00007005425702206358824909892712', '1.0000', '148.5000', 0], 'DAI': ['0.00007005425702206358824909892712', '1.0000', '148.5000', 0], 'PAX': ['0.00007005425702206358824909892712', '1.0000', '148.5000', 0], 'TUSD': ['0.00006999120819074373101967473808', '0.9991', '148.3664', '-0.0100'], 'XRP': ['0.00001681092005758459927213626954', '0.2400', '35.6355', '0.2548'], 'LTC': ['0.003902022116128941865474810241', '55.7000', '8271.4500', '5.0349']}, 'argenbtc': {'precio_compra': 2290816.45, 'precio_venta': 2209460.4, 'precio_compra_f': '2.290.816', 'precio_venta_f': '2.209.460', 'date_cotizacion': '23:23:44'}, 'ripio': [{'ticker': 'USDC_ARS', 'buy_rate': '160.64', 'sell_rate': '154.31', 'variation': '-0.19'}, {'ticker': 'ETH_ARS', 'buy_rate': '68635.99', 'sell_rate': '61831.26', 'variation': '1.05'}, {'ticker': 'DAI_ARS', 'buy_rate': '163.47', 'sell_rate': '154.97', 'variation': '0.01'}, {'ticker': 'LTC_ARS', 'buy_rate': '9431.30', 'sell_rate': '8496.26', 'variation': '1.99'}, {'ticker': 'BTC_ARS', 'buy_rate': '2299179.82', 'sell_rate': '2208426.48', 'variation': '0.93'}], 'buenbit': {'object': {'daiars': {'price_change_percent': '-4.42%', 'price': '156.75', 'currency': 'AR$', 'ask_currency': 'ars', 'bid_currency': 'dai', 'purchase_price': '153.7', 'selling_price': '159.8', 'market_identifier': 'daiars'}, 'daiusd': {'price_change_percent': '-3.81%', 'price': '1.03', 'currency': 'U$D', 'ask_currency': 'usd', 'bid_currency': 'dai', 'purchase_price': '1.01', 'selling_price': '1.05', 'market_identifier': 'daiusd'}, 'btcars': {'price_change_percent': '+6.40%', 'price': '2212750.0', 'currency': 'AR$', 'ask_currency': 'ars', 'bid_currency': 'btc', 'purchase_price': '2169400.0', 'selling_price': '2256100.0', 'market_identifier': 'btcars'}}, 'errors': []}}
    # print(requests_res)

    processed_rates = {}

    process_info_bit2me(requests_res, processed_rates)
    process_info_bit2me_new(requests_res, processed_rates)
    process_info_ripio(requests_res, processed_rates)
    process_info_satoshitango(requests_res, processed_rates)
    process_info_buenbit(requests_res, processed_rates)
    process_info_argenbtc(requests_res, processed_rates)
    process_info_qubit(requests_res, processed_rates)

    # print(processed_rates)
    messages = []

    for coin, data in processed_rates.items():
        try:
            # bit2me_comission = 0.03 # bit2me old
            bit2me_comission = 0.013 # bit2me new
            buy_price = data["buy"]
            network_fee = data["network_fee"]
            coins_bought = EUR_amount*(1-bit2me_comission)/buy_price
            coins_transfered = coins_bought - network_fee
            print(coin + ": " + str(coins_transfered) + " - network fee: " + str(network_fee))

            try:
                for exchange, sell_price in data["sell"].items():
                    exchange_commission = float(data["commission"][exchange])
                    ARS_received = float(coins_transfered)*float(sell_price)
                    ARS_commission_payed = ARS_received*exchange_commission
                    ARS_amount = ARS_received - ARS_commission_payed

                    row_desc = "Conversion ARS/EUR through "
                    row_desc += coin + " at " + exchange + ":\t"
                    rate = float(ARS_amount)/float(EUR_amount)
                    row_desc += str(round(rate, 2))
                    row_desc += "\t(" + "{:.2f}".format(ARS_amount) + " ARS / "
                    row_desc += str(EUR_amount) + " EUR)"
                    print(row_desc)
            except KeyError:
                print(coin + " cannot be sold at any of the provided exchanges")
        except KeyError:
            print(coin + " cannot be bought at bit2me")


input_message = "Ingrese monto a vender (EUR). \"c\" para cancelar: "
try:
    EUR_amount = float(input(input_message))

    while isinstance(EUR_amount, float):
        check_rates(float(EUR_amount))
        EUR_amount = float(input(input_message))
except ValueError:
    a = input("Fin. Apretá Enter para salir.")
