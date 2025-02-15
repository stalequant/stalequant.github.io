# How to Attract Market Makers (MM) to Your Platform
## Insights from an Experienced Liquidity Provider

Many builders end up in a position where they want active liquidity on their platform. They need someone who will quote prices for the thing they've dreamed up, keep inventory, and stand ready to buy and sell. What should they do?

I'm one of the people you may be targeting, so I'll try to give you what attracts me to the platforms. I've been one of the first active liquidity providers for at least a dozen projects.

Given that, **this is what I want**. Note that EVERYTHING on this list is negotiable. But the more costs you put onto me, the more I'm going to demand.

## Lower barriers to entry

### Provide a Working SDK

Many builders assume pointing to an API spec is enough, but that's a mistake. Figuring out signing by yourself is always a massive pain. Because of that, I am very reluctant to integrate with a platform that lacks a proper SDK.

Making an SDK is a version of dogfooding. If someone on your team can't quickly put together an SDK, how on earth do you expect me to?

In the age of chat GPT, the language of the SDK doesn't really matter. I'd suggest either Python with type hints or TS to hit the widest possible audience.

**Actionable Suggestion:** Post an SDK that covers the basic methods of your protocol. 

**Role Model:** I'd put BitMEX as the role model here. BitMEX not only provided an SDK, they provided a basic MM bot. I think that's part of the platform's (past) success.

### Copy Existing Structures Where Possible

Anything that isn’t your core innovation should be as close to established players as possible. 

If I'm quoting on your platform, I'm going to be taking existing stuff (e.g., HL) and making whatever changes are needed. Every deviation from the norm adds a cost. Minimize unnecessary changes.

**Actionable Suggestion:** Follow existing players unless you have a good reason not to. 

**Role Model:** Hyperliquid did a good job here - USDT indexes, a similar funding formula to Binacne, and an AWS tokyo location made it easy to port Binance quotes over. Something like Kraken Futures is an anti-role model: 24-hour factor futures with unclear indices quoted in Europe is a nightmare for no good reason.

### Consider a Taker Speedbump

Slowing down taker orders by 100ms (e.g., Hyperliquid) makes it a lot easier to set up because you do not need to worry about being picked off by sniping bots.

### Completely Describe of Cash Flows

If you want me to provide reasonable price quotes, you need to provide an exact and detailed description of the cash flows of the assets being traded.

**Actionable Suggestion:** Take two similar products, review their documentation, and ensure yours covers everything they do. Information buried in Discord chats is not sufficient.

**Role Model:**  Skimming through platforms, I like Paradigm's documentation. Hyperliquid's is okay. Kraken Futures is poor. Whales Market is horrible.

## Make me comfortable I'm not going to lose my money

### Convey Trustworthiness

Everyone needs confidence that their funds are safe. Personally, I look for backers I know (VCs and ideally community members), a doxxed team, and a track record.

### Telegraph changes as much as possible

If I have a position in a contract and you change the contract, I lose money. Even worse, if I don't realize there is a change I might be quoting wrong and someone might take me to the cleaners.

### Specific asks

In order of priority:
- API keys. I don't want to have to store keys with withdraw access remotely.
- Clear information on rate limits. It's incredibly common for an MM to hit rate limits and then be a sitting duck and have all their orders picked off.
- Deadman switches or order expirations. If my system crashs (e.g., because of your system sending me garbage) or hits a hidden rate limit (above), I don't want to lose a bunch of money.
- Multisig (this only matters at later stages)

## Show me I'm going to make money

### Show Growth

Everyone wants growth, so this isn't really actionable. But realize that a lot of the integration costs are a one-time cost. If I'm earning that dividend over a long time, it's a much easier sell.

The returns to integration increase as the platform grows. If your growth is stagnant or uncertain, the cost of integration becomes harder to justify.

### Provide the information needed to assess profitability

The liquidity provider's profitability is of course the most important thing. I'm not saying much here because I don't want to leak too much alpha to other MM. 

My suggestion here is just to provide information easily. Don't tell people to enquire about the MM program on Discord and then reply three days later. Put it in the docs.
