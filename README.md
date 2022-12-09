# DeSo Analysis Node Implementation

## An overview over DeSo blockchain
Running a DeSo node to retrieve on-chain data means to rely on a limited list of API methods, that mostly does not cover the needs of a developer. A solution to break this "obtainable" data is proposed through the use of this framework, which fetches blocks from the official node to extract and store its content in a Psql DB following a different scheme. In this way queries are much flexible allowing us to to draw some custom overviews of DeSo ecosystem in order to compute much complex analyses, i.e. fraud and malicious activities within NFT marketplace, common social newtorks user behaviour and so on...

To express its potential, here it is a [Graph representation](https://hub.graphistry.com/graph/graph.html?dataset=fbcbb4618a0f4d3c9d6b948ee3b105ae&play=5000&splashAfter=false&session=946050bad8344c048610a0e32d6563a5) of all NFT sales ( Directed Multigraph) till this moment, produced by combining this framework with the Graphistry Python module.
![image](https://user-images.githubusercontent.com/52136996/206786729-13eeb0dc-7883-42e5-be77-22c61bb0f36c.png)

### Dependencies:

### How does it work?:
