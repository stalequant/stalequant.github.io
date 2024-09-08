
class CircularBuffer {
    constructor(capacity) {
      this.buffer = [];
      this.capacity = capacity;
    }
  
    push(item) {
      this.buffer.push(item);
      if (this.buffer.length > this.capacity) {
        this.buffer.shift();
      }
    }
  
    get(index) {
      return this.buffer[index];
    }
  
    toArray() {
      return [...this.buffer];
    }
        
    percentile( pct) {
        if (this.buffer.length === 0) return undefined;
        const sorted = [...this.buffer].sort((a, b) => a - b);
        return sorted[Math.floor(sorted.length * pct)];
    }
  }

  const  hl_binance_bid_ratio =  new CircularBuffer(200)
  const  hl_binance_ask_ratio =  new CircularBuffer(200)

  function pullRef(series, item, side) {
    const data = venueDtypeMapping[locToStr(series, item, side)];
    if (!data || !data.data || data.data.length === 0) {
        throw new RangeError(`No data available for ${series} ${item} ${side}`);
    }
    return data.data[data.data.length - 1].y;
}
var tick = -1

function isWithin10SecondsOfHour() {
  const now = new Date();
  const minutes = now.getMinutes();
  const seconds = now.getSeconds();
  
  return (minutes === 59 && seconds >= 50) || (minutes === 0 && seconds <= 10);
}

function addStalegunData(){
  try {
    
    const binance_bid = pullRef('binance futures', 'bid-ask', true)
    const binance_ask = pullRef('binance futures', 'bid-ask', false)
      
    tick =  Math.pow(10,Math.floor(Math.log10(binance_bid)) - 4)

    const hl_bid = pullRef('hyperliquid', 'bid-ask', true)
    const hl_ask = pullRef('hyperliquid', 'bid-ask', false)

    hl_binance_bid_ratio.push(hl_bid / binance_bid);
    hl_binance_ask_ratio.push(hl_ask / binance_ask);

    var bid_theo = hl_binance_bid_ratio.percentile(1/3) * binance_bid
    var ask_theo =  hl_binance_ask_ratio.percentile(2/3) * binance_ask
    
    if (isWithin10SecondsOfHour()){
      bid_theo = bid_theo  * (1-1/100)
      ask_theo = ask_theo  * (1+1/100) 
    } 
    
    if ( buying) { 
      const buy_price = Math.min(hl_bid+tick, bid_theo);
      addData('stalegun', 'bid-ask', true, Date.now() - binanceLag, buy_price);
      addData('stalegun', 'bid-ask', false, Date.now() - binanceLag,  buy_price );
      if( hl_ask< bid_theo){
        addData('stalegun', 'trades', true, Date.now() - binanceLag, hl_ask);

      }
    } else { 
      const buy_price = Math.min(hl_bid+tick, bid_theo);
      const sell_price = Math.max(hl_ask-tick, ask_theo);
      addData('stalegun', 'bid-ask', true, Date.now() - binanceLag, sell_price);
      addData('stalegun', 'bid-ask', false, Date.now() - binanceLag,  sell_price );
      if( hl_bid> ask_theo){
        addData('stalegun', 'trades', false, Date.now() - binanceLag, hl_bid);

      }
    }
    
  } catch (error) {
    if (error instanceof RangeError) {
      return 
    } else {
      throw error;
    }
  }
}