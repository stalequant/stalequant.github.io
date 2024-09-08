const wsHyperliquid = new WebSocket('wss://api.hyperliquid.xyz/ws');

var hyperliquidFirstCall = true;
var hyperLiquidBinanceRatio = 1;

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

wsHyperliquid.onopen = function() {
    wsHyperliquid.send(JSON.stringify({
        "method": "subscribe",
        "subscription": { "type": "l2Book", "coin": coinParam }
    }));
    wsHyperliquid.send(JSON.stringify({
        "method": "subscribe",
        "subscription": { "type": "trades", "coin": coinParam }
    }));
};

wsHyperliquid.onmessage = function(event) {
    const venue = 'hyperliquid';
    const message = JSON.parse(event.data);

    if (message.channel === "l2Book" && message.data.coin === coinParam) {
        const timestamp = parseFloat(message.data.time);
        const levels = message.data.levels;
        if (levels && levels.length >= 2) {
            addData(venue, 'bid-ask', true, timestamp, parseFloat(levels[0][0].px));
            addData(venue, 'bid-ask', false, timestamp, parseFloat(levels[1][0].px));

            const deepBid = getDepthPrice(levels[0].map(item => [item.px, item.sz]));
            addData(venue, '$5k spread', true, timestamp, deepBid);

            const deepAsk = getDepthPrice(levels[1].map(item => [item.px, item.sz]));
            addData(venue, '$5k spread', false, timestamp, deepAsk);
        }
    }

    if (message.channel === "trades" && message.data.length > 0) {
        if (hyperliquidFirstCall){
		hyperliquidFirstCall = false;
		return
	}
        message.data.forEach(trade => {
            if (trade.coin === coinParam) {
                const tradePrice = parseFloat(trade.px);
                const timestamp = trade.time;
                addData(venue, 'trades', trade.side === "B", timestamp, tradePrice);
            }
        });
    }
};
  
