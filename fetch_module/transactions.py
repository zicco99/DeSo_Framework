import math

from sqlalchemy import ARRAY, Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Block(Base):
    __tablename__ = 'block'

    block_hash = Column(String, primary_key=True)
    version = Column(Integer)
    tx_number = Column(Integer)
    prev_block_hash = Column(String)
    timestamp = Column(Integer)
    block_height = Column(Integer)
    tx_merkle_root = Column(String)
    block_nonce = Column(String)
    extra_nonce = Column(String)

    def __init__(self, b_hash, version, tx_number, prev_hash, timestamp, b_height, tx_merkle_root, b_nonce, extra_nonce):
        self.block_hash = b_hash
        self.version = version
        self.tx_number = tx_number
        self.prev_block_hash = prev_hash
        self.timestamp = timestamp
        self.block_height = b_height
        self.tx_merkle_root = tx_merkle_root
        self.block_nonce = b_nonce
        self.extra_nonce = extra_nonce

    def __str__(self):
        return ' BlockHash: {self.block_hash}\n Version: {self.version}\n PrevBlockHash: {self.prev_block_hash}\n TimeStamp: {self.timestamp}\n BlockHeight: {self.block_height}\n TxMerkleRoot: {self.tx_merkle_root}\n BlockNonce: {self.block_nonce}\n ExtraNonce: {self.extra_nonce}\n'.format(self=self)


class Transaction(Base):
    __tablename__ = 'transaction'
    tx_id_base58 = Column(String, primary_key=True)
    tx_raw_hex = Column(String)
    signature_hex = Column(String)
    block_hash = Column(String, ForeignKey('block.block_hash'))
    mine_fee = Column(Float)
    tx_transactor_base58 = Column(String)

    #Shared columns among transactions (To avoid wasting too much space but also use few indexs in db)

    #State added if the transaction has been write by a custom node (official nodes excluded)
    on_custom_node = Column(Boolean)
    node_recipient_base58 = Column(String)
    node_fee = Column(Float)

    #Cryptocurrency transfered,used,biddded... etc.
    amount = Column(Float)

    #Contains the other user involved in binary transaction (es. receiver in BasicTransfer etc...)
    other_us_base58 = Column(String)

    #Shared state among all NFT transactions
    nft_hash = Column(String)
    nft_serial = Column(Integer)

    #Creator related a certain coin or NFT
    creator_base58 = Column(String)

    #Tipped,reposted,liked,NFT's... post hash
    post_hash = Column(String)


    def __init__(self,id_base58,raw_hex,sign_hex,transactor,block_hash,metadata):
        self.tx_id_base58 = id_base58
        self.tx_raw_hex = raw_hex
        self.signature_hex = sign_hex
        self.tx_transactor_base58 = transactor
        self.block_hash = block_hash
        self.mine_fee = metadata['BasicTransferTxindexMetadata']['FeeNanos'] / 10**9

##################### TX SEMANTIC PARSING -> SUBCLASSES #########################

class BasicTransfer(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'BasicTransfer'}
    is_a_tip = Column(Boolean)

    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        self.is_a_tip = True

        diamond_lvl = metadata["BasicTransferTxindexMetadata"]["DiamondLevel"]
        #Differ tips from transfers
        if(diamond_lvl!=0):
            self.post_hash = metadata["BasicTransferTxindexMetadata"]["PostHashHex"]
        else:
            self.is_a_tip = False

        self.on_custom_node = True
        if(len(outputs)==3):#The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]

            self.other_us_base58 = metadata["AffectedPublicKeys"][1]["PublicKeyBase58Check"]
            self.amount = outputs[1]['AmountNanos'] / 10**9

        else:
            self.on_custom_node = False
            self.other_us_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
            self.amount = outputs[0]['AmountNanos'] / 10**9

class UpdateProfile(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'UpdateProfile'}
    n_username = Column(String)
    n_founder_reward = Column(Float)
    n_is_hidden = Column(Boolean)

    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        self.on_custom_node = True
        if(len(outputs)==2):
            self.node_fee = outputs[0]['AmountNanos'] / 10**9 
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
        else:
            self.on_custom_node = False

        profile = metadata["UpdateProfileTxindexMetadata"]

        self.n_username = profile["NewUsername"]
        self.n_founder_reward = profile["NewCreatorBasisPoints"] / 100
        self.n_is_hidden = profile["IsHidden"]


class Follow(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'Follow'} 
    is_unfollow = Column(Boolean)

    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        self.on_custom_node = True

        if(len(outputs)==3):#The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
            self.other_us_base58 = metadata["AffectedPublicKeys"][2]["PublicKeyBase58Check"]
        else:
            self.on_custom_node = False
            self.other_us_base58 = metadata["AffectedPublicKeys"][1]["PublicKeyBase58Check"]

        self.is_unfollow = metadata["FollowTxindexMetadata"]["IsUnfollow"]


class CreatorCoin(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'CreatorCoin'}
    is_buy = Column(Boolean)

    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        self.on_custom_node = True
        if(len(outputs)==3):#The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
            self.other_us_base58 = metadata["AffectedPublicKeys"][2]["PublicKeyBase58Check"]
        else:
            self.on_custom_node = False
            self.other_us_base58 = metadata["AffectedPublicKeys"][1]["PublicKeyBase58Check"]
        
        self.is_buy = metadata["CreatorCoinTxindexMetadata"]["OperationType"]=="buy"
        
        if(self.is_buy): #BUY
            self.amount = metadata["CreatorCoinTxindexMetadata"]["DeSoToSellNanos"] / 10**9
        else: #SELL
            self.amount = metadata["CreatorCoinTxindexMetadata"]["CreatorCoinToSellNanos"] / 10**9

class SubmitPost(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'SubmitPost'}
    is_repost = Column(Boolean)
    submitted_post_hash = Column(String)

    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        self.is_repost = True
        self.on_custom_node = True

        if(len(outputs)==3):#The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
            self.other_us_base58 = metadata["AffectedPublicKeys"][2]["PublicKeyBase58Check"]

        else:
            self.on_custom_node = False
            if(len(outputs)>1):
                self.other_us_base58 = metadata["AffectedPublicKeys"][1]["PublicKeyBase58Check"]
            else:
                self.is_repost = False
        
        self.submitted_post_hash = metadata["SubmitPostTxindexMetadata"]["PostHashBeingModifiedHex"]
        self.post_hash = metadata["SubmitPostTxindexMetadata"]["ParentPostHashHex"]


class Like(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'Like'}
    is_unlike = Column(Boolean)

    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        self.on_custom_node = True

        if(len(outputs)==3):#The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
            self.other_us_base58 = metadata["AffectedPublicKeys"][2]["PublicKeyBase58Check"]

        else:
            self.on_custom_node = False
            self.other_us_base58 = metadata["AffectedPublicKeys"][1]["PublicKeyBase58Check"]

        self.is_unlike = metadata["LikeTxindexMetadata"]["IsUnlike"] 
        self.post_hash = metadata["LikeTxindexMetadata"]["PostHashHex"]
    

class BlockReward(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'BlockReward'}

    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        self.on_custom_node = True
        if(len(outputs)==2):#The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
            self.other_us_base58 = metadata["AffectedPublicKeys"][1]["PublicKeyBase58Check"]
            self.amount = outputs[1]["AmountNanos"] / 10**9

        else:
            self.on_custom_node = False
            self.other_us_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
            self.amount = outputs[0]["AmountNanos"] / 10**9


class BitcoinExchange(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'BitcoinExchange'}
    btc_addr = Column(String)
    btc_spent = Column(Float)
    deso_gen = Column(Float)

    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        #TODO
        print(outputs)

        self.on_custom_node = True
        if(len(outputs)==2):#The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
        else:
            self.on_custom_node = False

        exchange_metadata = metadata["BitcoinExchangeTxindexMetadata"]

        self.btc_addr = exchange_metadata['BitcoinSpendAddress']
        self.btc_spent = exchange_metadata['SatoshisBurned'] / 10**9
        self.deso_gen = exchange_metadata["NanosCreated"] / 10**9


class PrivateMessage(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'PrivateMessage'}
    msg_time = Column(Integer)

    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        self.on_custom_node = True
        if(len(outputs)==3):#The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
            self.other_us_base58 = metadata["AffectedPublicKeys"][2]["PublicKeyBase58Check"]
        else:
            self.on_custom_node = False
            self.other_us_base58 = metadata["AffectedPublicKeys"][1]["PublicKeyBase58Check"]

        self.msg_time = metadata["PrivateMessageTxindexMetadata"]["TimestampNanos"] // 10**9


class MessagingGroup(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'MessagingGroup'}
    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        self.on_custom_node = True
        if(len(outputs)==2):#The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
        else:
            self.on_custom_node = False
        

class CreatorCoinTransfer(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'CreatorCoinTransfer'}
    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        self.on_custom_node = True
        if(len(outputs)==3):#The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
            self.other_us_base58 = metadata["AffectedPublicKeys"][2]["PublicKeyBase58Check"]
        else:
            self.on_custom_node = False
            self.other_us_base58 = metadata["AffectedPublicKeys"][1]["PublicKeyBase58Check"]
        
        self.creator_base58 = metadata['CreatorCoinTransferTxindexMetadata']['CreatorUsername']
        self.amount = metadata['CreatorCoinTransferTxindexMetadata']['CreatorCoinToTransferNanos'] / 10**9


class AuthorizeDerivatedKey(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'AutorizeDerivatedKey'}
    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        self.on_custom_node = True
        if(len(outputs)==2):#The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
        else:
            self.on_custom_node = False
        

class NFTBid(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'NftBid'}
    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        self.on_custom_node = True
        if(len(outputs)==3):#The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
            self.other_us_base58 = metadata["AffectedPublicKeys"][2]["PublicKeyBase58Check"]
        else:
            self.on_custom_node = False
            self.other_us_base58 = metadata["AffectedPublicKeys"][1]["PublicKeyBase58Check"]
        
        self.amount =  metadata['NFTBidTxindexMetadata']['BidAmountNanos'] / 10**9
        self.post_hash = metadata['NFTBidTxindexMetadata']['NFTPostHashHex']
        self.nft_serial_n = metadata['NFTBidTxindexMetadata']['SerialNumber']

class AcceptNFTBid(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'AcceptNFTBid'}
    creator_bonus_perc = Column(Integer)
    coin_bonus_perc = Column(Integer)

    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)
        
        self.on_custom_node = True
        if(sum(1 for p_key,met in metadata["AffectedPublicKeys"] if met=="BasicTransferOutput")==2): #The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
            self.other_us_base58 = metadata["AffectedPublicKeys"][2]["PublicKeyBase58Check"]
        else:
            self.on_custom_node = False
            self.other_us_base58 = metadata["AffectedPublicKeys"][1]["PublicKeyBase58Check"]

        self.amount =  metadata['AcceptNFTBidTxindexMetadata']['BidAmountNanos'] / 10**9
        self.post_hash = metadata['AcceptNFTBidTxindexMetadata']['NFTPostHashHex']
        self.nft_serial = metadata['AcceptNFTBidTxindexMetadata']['SerialNumber']
        self.creator_base58 = metadata['AcceptNFTBidTxindexMetadata']['NFTRoyaltiesMetadata']['CreatorPublicKeyBase58Check']
        self.coin_bonus_perc = math.ceil((metadata['AcceptNFTBidTxindexMetadata']['NFTRoyaltiesMetadata']['CreatorCoinRoyaltyNanos'] / self.amount)*100 / 10**9)
        self.creator_bonus_perc = math.ceil((metadata['AcceptNFTBidTxindexMetadata']['NFTRoyaltiesMetadata']['CreatorRoyaltyNanos'] / self.bid_amount)*100 / 10**9)

class CreateNFT(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'CreateNFT'}
    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        self.on_custom_node = True
        if(sum(1 for p_key,met in metadata["AffectedPublicKeys"] if met=="BasicTransferOutput")==2): #The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
        else:
            self.on_custom_node = False

        self.post_hash = metadata['CreateNFTTxindexMetadata']['NFTPostHashHex']


class UpdateNFT(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'UpdateNFT'}
    on_sale = Column(Boolean)
    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        self.on_custom_node = True
        if(sum(1 for p_key,met in metadata["AffectedPublicKeys"] if met=="BasicTransferOutput")==2): #The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
        else:
            self.on_custom_node = False

        self.on_sale = metadata["UpdateNFTTxindexMetadata"]["IsForSale"]
        self.post_hash = metadata['UpdateNFTTxindexMetadata']['NFTPostHashHex']


class BurnNFT(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'BurnNFT'}
    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        self.on_custom_node = True
        if(sum(1 for p_key,met in metadata["AffectedPublicKeys"] if met=="BasicTransferOutput")==2): #The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
        else:
            self.on_custom_node = False

        self.post_hash = metadata['BurnNFTTxindexMetadata']['NFTPostHashHex']
        self.nft_serial = metadata['BurnNFTTxindexMetadata']['SerialNumber']

class NFTTransfer(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'NFTTransfer'}
    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        self.on_custom_node = True
        if(sum(1 for p_key,met in metadata["AffectedPublicKeys"] if met=="BasicTransferOutput")==2): #The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
            self.other_us_base58 = metadata["AffectedPublicKeys"][1]["PublicKeyBase58Check"]
        else:
            self.on_custom_node = False
            self.other_us_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]

        self.post_hash = metadata['NFTTransferTxindexMetadata']['NFTPostHashHex']
        self.nft_serial = metadata['NFTTransferTxindexMetadata']['SerialNumber']


class AcceptNFTTransfer(Transaction):
    __mapper_args__ = {'polymorphic_identity': 'NFTAcceptTransfer'}
    def __init__(self,id_base58,raw_hex,outputs,sign_hex,transactor,block_hash,metadata):
        super().__init__(id_base58,raw_hex,sign_hex,transactor,block_hash,metadata)

        self.on_custom_node = True
        if(sum(1 for p_key,met in metadata["AffectedPublicKeys"] if met=="BasicTransferOutput")==2): #The transaction has been done on a custom node, so there is a fee
            self.node_fee = outputs[0]['AmountNanos'] / 10**9
            self.node_recipient_base58 = metadata["AffectedPublicKeys"][0]["PublicKeyBase58Check"]
        else:
            self.on_custom_node = False

        self.post_hash = metadata['AcceptNFTTransferTxindexMetadata']['NFTPostHashHex']
        self.nft_serial = metadata['AcceptNFTTransferTxindexMetadata']['SerialNumber']
        
#Alternative node example :) -> BC1YLhjjhom1dQXdW52ZoXUxTZQJrLaUH4mRfJBkNTiJYCMu7oCZC4d

