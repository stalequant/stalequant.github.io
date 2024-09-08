
const wsBinanceOrderBook = new WebSocket(`wss://fstream.binance.com/ws/${coinParam.toLowerCase()}usdt@depth20@100ms`);
const wsBinanceAggTrade = new WebSocket(`wss://fstream.binance.com/ws/${coinParam.toLowerCase()}usdt@aggTrade`);
const wsBinanceSpotOrderBook = new WebSocket(`wss://stream.binance.com:443/ws/${coinParam.toLowerCase()}usdt@depth20@100ms`);
const wsBinanceSpotAggTrade = new WebSocket(`wss://stream.binance.com:443/ws/${coinParam.toLowerCase()}usdt@aggTrade`);

var binanceLag = 0; 

function getDepthPrice(orders) {
    let sum = 0;
    let i = 0;
    while (i < orders.length) {
        sum += parseFloat(orders[i][1]) * parseFloat(orders[i][0]);
        if (sum > reqLiq) {
            return parseFloat(orders[i][0]);
        }
        i++;
    }
    return parseFloat(orders[orders.length - 1][1]) / 1.01;
}

wsBinanceOrderBook.onmessage = function(event) {
    const message = JSON.parse(event.data);
let venue = 'binance futures';

    if (message.e === "depthUpdate" && message.s === `${coinParam}USDT`) {	
        const timestamp = parseFloat(message.E);
    updateBinanceLag(timestamp)

            addData(venue,'bid-ask',true, timestamp, parseFloat(message.b[0][0]));
            addData(venue,'bid-ask',false, timestamp, parseFloat(message.a[0][0]));

            const deepBid = getDepthPrice(message.b);
            addData(venue,'$5k spread',true, timestamp, deepBid);
            const deepAsk = getDepthPrice(message.a);
            addData(venue,'$5k spread',false, timestamp, deepAsk);
    }
};

wsBinanceAggTrade.onmessage = function(event) {
const venue = 'binance futures';
    const message = JSON.parse(event.data);
    if (message.e === "aggTrade" && message.s === `${coinParam}USDT`) {
        const tradePrice = parseFloat(message.p);
        const timestamp = message.T;

    addData(venue, 'trades', !message.m, timestamp, tradePrice); // binance Trades
    }
};

function updateBinanceLag(timestamp){
 		    let measuredLag = Date.now() - timestamp;
		    binanceLag = binanceLag * .9 + measuredLag*.1;
}
        wsBinanceSpotOrderBook.onmessage = function(event) {
		const venue = 'binance spot';
                const message = JSON.parse(event.data);
                const currentTime = Date.now();
	        const timestamp = currentTime - binanceLag;
                    
		addData(venue,'bid-ask', true, timestamp, parseFloat(message.bids[0][0]));
                addData(venue,'bid-ask', false, timestamp, parseFloat(message.asks[0][0]));

                const deepBid = getDepthPrice(message.bids);
                addData(venue,'$5k spread',true, timestamp, deepBid);
                const deepAsk = getDepthPrice(message.asks);
                addData(venue,'$5k spread',false, timestamp, deepAsk);

        };
 
        wsBinanceSpotAggTrade.onmessage = function(event) {
	    const venue = 'binance spot';
            const message = JSON.parse(event.data);
            if (message.e === "aggTrade" && message.s === `${coinParam}USDT`) {
                const tradePrice = parseFloat(message.p);
                const timestamp = message.T;
	        updateBinanceLag(timestamp)

	        addData(venue, 'trades', !message.m, timestamp, tradePrice); // binance Trades
            }
        }; 
 
