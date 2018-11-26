# High-frequency-market-tracker

This tool tracs EVE Online market at high frequency. The polling is done as fast as the API allows (every 5 minutes).

frequent.py: This does the market polling. Market data is written in market_cache.gz
plot.py: This can be used to plot the data. Just type in the ID of the item you want to look at.

The repository includes sample market_cache.gz that contains several hours of market data. If you want to start from scratch just delete it.

Requires: 
* Grequests https://github.com/kennethreitz/grequests
* Matplotlib https://matplotlib.org/index.html
