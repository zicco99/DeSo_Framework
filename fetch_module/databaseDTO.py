import sys

from transactions import *
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine,func, inspect


#CONFIGURATION
USERNAME_ROLE = "f.ziccolella"
PASSWORD_ROLE = "f.ziccolella"
DB_IP = "localhost"
PORT = 5432
DB_NAME = "deso_blockchain"

#####################################################################################################################

# Global vars
metadata_obj = None
session = None
tx_infos = ['TransactionIDBase58Check', 'RawTransactionHex', 'Inputs',
            'Outputs', 'TransactionType', 'BlockHashHex', 'SignatureHex', 'TransactionMetadata']

# UTILITY FUNCTIONS

def block_is_in_db(b_hash):
    global session
    block_check = session.query(Block).filter_by(block_hash=b_hash).first()
    return block_check is not None


def get_block_height(b_hash):
    global session
    block = session.query(Block).filter_by(block_hash=b_hash).first()
    return block.block_height


def block_is_intirely_inserted(b_hash):
    global session
    b = session.query(Block).filter_by(block_hash=b_hash).first()
    return b.tx_number == session.query(Transaction).filter_by(block_hash=b.block_hash).count()


def block_is_intirely_inserted_by_height(b_height):
    global session
    b = session.query(Block).filter_by(block_height=b_height).first()
    return b.tx_number == session.query(Transaction).filter_by(block_hash=b.block_hash).count()


def max_block_h():
    global session
    if (session.query(func.max(Block.block_height)).scalar() is None):
        return float('-inf')
    else:
        return session.query(func.max(Block.block_height)).scalar()


def max_block_h_se(session):
    if (session.query(func.max(Block.block_height)).scalar() is None):
        return float('-inf')
    else:
        return session.query(func.max(Block.block_height)).scalar()


def min_block_h():
    global session
    if (session.query(func.min(Block.block_height)).scalar() is None):
        return float('+inf')
    else:
        return session.query(func.min(Block.block_height)).scalar()


def get_prev_block(b_hash):
    global session
    return session.query(Block).filter_by(block_hash=b_hash).first().prev_block_hash


def tx_is_in_db(tx_hash):
    global session
    block_check = session.query(Transaction).filter_by(
        tx_id_base58=tx_hash).first()
    return block_check is not None


def insert_tx_in_db(header, tx):
    info = {}

    for key_info in tx_infos:
        try:
            info[key_info] = tx[key_info]
        except (KeyError):
            info[key_info] = None

    m = info['TransactionMetadata']

    params = (info['TransactionIDBase58Check'], info['RawTransactionHex'], info['Outputs'], info['SignatureHex'],m["TransactorPublicKeyBase58Check"], header['BlockHashHex'], info['TransactionMetadata'])
    transaction = None

    tx_type = info['TransactionMetadata']['TxnType']

    if (tx_type == "BASIC_TRANSFER"): transaction = BasicTransfer(*params)
    if (tx_type == "UPDATE_PROFILE"): transaction = UpdateProfile(*params)
    if (tx_type == "FOLLOW"): transaction = Follow(*params)
    if (tx_type == "CREATOR_COIN"): transaction = CreatorCoin(*params)
    if (tx_type == "SUBMIT_POST"): transaction = SubmitPost(*params)
    if (tx_type == "LIKE"): transaction = Like(*params)
    if (tx_type == "BLOCK_REWARD"):transaction = BlockReward(*params)               
    if (tx_type == "BITCOIN_EXCHANGE"): transaction = BitcoinExchange(*params)
    if (tx_type == "PRIVATE_MESSAGE"):transaction = PrivateMessage(*params)
    if (tx_type == "CREATOR_COIN_TRANSFER"): transaction = CreatorCoinTransfer(*params)
    if (tx_type == "AUTHORIZE_DERIVED_KEY"): transaction = AuthorizeDerivatedKey(*params) 
    if (tx_type == "NFT_BID"): transaction = NFTBid(*params)
    if (tx_type == "ACCEPT_NFT_BID"): transaction = AcceptNFTBid(*params)
    if (tx_type == "CREATE_NFT"): transaction = CreateNFT(*params)
    if (tx_type == "UPDATE_NFT"): transaction = UpdateNFT(*params)
    if (tx_type == "BURN_NFT"): transaction = BurnNFT(*params)
    if (tx_type == "NFT_TRANSFER"): transaction = NFTTransfer(*params)
    if (tx_type == "ACCEPT_NFT_TRANSFER"): transaction = AcceptNFTTransfer(*params)

    if(transaction is None):
        return

    try:
        session.add(transaction)
    except Exception as e:
        session.rollback()
        print(e)
        exit(-1)


def insert_block_in_db(block):
    try:
        session.add(block)
        session.commit()
    except Exception as e:
        session.rollback()
        print(e)
        exit(-1)

# -----------------------------------


def bootstrap_db():
    global session
    global metadata

    # Establishing DB connection
    engine = create_engine('postgresql://{}:{}@{}:{}/{}'.format(USERNAME_ROLE,PASSWORD_ROLE,DB_IP,PORT,DB_NAME))
    Session = sessionmaker(bind=engine)
    session = Session()
    metadata = MetaData(bind=engine)

    if (not inspect(engine).has_table("block")):
        Block.__table__.create(engine)

    if (not inspect(engine).has_table("transaction")):
        Transaction.__table__.create(engine)

    # Running options
    for arg in sys.argv:
        if (arg[0] == '-'):
            for op in arg[1:]:
                match op:
                    case 'n':  # Recreate database

                        metadata.reflect(bind=engine)
                        metadata.drop_all(bind=engine)

                        if (not inspect(engine).has_table("block")):
                            Block.__table__.create(engine)

                        if (not inspect(engine).has_table("transaction")):
                            Transaction.__table__.create(engine)
                        break

# Close DB connection


def close_db():
    global session
    session.close()


# The block is not in the DB  -> all transactions should be insered
def clean_insert(block_data):
    global session
    header = block_data['Header']

    # Constructing block obj
    block = Block(b_hash=header['BlockHashHex'], version=header['Version'],
                  tx_number=len(block_data["Transactions"]), prev_hash=header['PrevBlockHashHex'],
                  timestamp=header['TstampSecs'], b_height=header['Height'],
                  tx_merkle_root=header['TransactionMerkleRootHex'], b_nonce=str(
                      header['Nonce']),
                  extra_nonce=str(header['ExtraNonce']))

    # Insert block into DB
    insert_block_in_db(block)

    for tx in block_data["Transactions"]:
        # Insert transation into DB
        insert_tx_in_db(header, tx)

    try:
        session.commit()
    except Exception as e:
        session.rollback()
        print(e)
        exit(-1)

    return header['PrevBlockHashHex']


# Block is already in the DB but some transactions miss, check which misses and add
def dirty_insert(block_data):
    header = block_data['Header']

    for tx in block_data["Transactions"]:
        if (not tx_is_in_db(tx['TransactionIDBase58Check'])):
            # Insert transation into DB
            insert_tx_in_db(header, tx)

    try:
        session.commit()
    except Exception as e:
        session.rollback()
        print(e)
        exit(-1)

    return header['PrevBlockHashHex']
