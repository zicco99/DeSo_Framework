import sys
import time
import requests
import json
import random

from databaseDTO import block_is_in_db, block_is_intirely_inserted, block_is_intirely_inserted_by_height, bootstrap_db, clean_insert, close_db, dirty_insert, get_prev_block, max_block_h, min_block_h
from progress.bar import Bar


#Endpoints
last_block_endp = "https://bitclout.com/api/v1?"
block_info_endp = "https://bitclout.com/api/v1/block"

# A custom http request that retries in case of failure with a growing interval
def http_request(type,block_hash):
    try_num=0
    while(True):
        try:
            if(type=="lastblock"):
                r = requests.get(last_block_endp)
            if(type=="header"):
                r = requests.post(block_info_endp, json={"HashHex": block_hash})
            if(type=="fullblock"):
                r = requests.post(block_info_endp, json={"HashHex": block_hash,"FullBlock":True})
            return r.json()
        except(requests.exceptions.ConnectionError, json.decoder.JSONDecodeError) as err:
            time.sleep(2**try_num + random.random()*0.01) #Exponential
            try_num+=1


# MY BEST MASTERPIECE -> ELEGANT AS F... hahaha (V.3 - iterative check including a good enough integrity checker)

def iterative_fetch():
    #Check integrity of local blockchain
    max_stored_in_db = max_block_h()
    min_stored_in_db = min_block_h()

    last_b_header = http_request("lastblock",None)['Header']
    curr_heigh = last_b_header['Height']
    curr_hash = last_b_header['BlockHashHex']

    with Bar('Fetching:',max = curr_heigh) as bar:
        while(curr_heigh>0):
            if(curr_heigh>max_stored_in_db or curr_heigh<min_stored_in_db):
                curr_hash = clean_insert(http_request("fullblock",curr_hash))
                print("not yet db reached -> clean insert")
            else:
                if(not block_is_in_db(curr_hash)):
                    curr_hash = clean_insert(http_request("fullblock",curr_hash))
                    print("this miss in db -> clean insert")
                else:
                    if(not block_is_intirely_inserted(curr_hash)):
                        curr_hash = dirty_insert(http_request("fullblock",curr_hash))
                        print("here i have been interrupted, add the rest -> dirty insert")
                    else:
                        curr_hash = get_prev_block(curr_hash)
                        print("everything good,SKIP")

            curr_heigh-=1
            bar.next()

def integrity_check():
    max_stored_in_db = max_block_h()
    while(max_stored_in_db>0):
        if(block_is_intirely_inserted_by_height(max_stored_in_db)==False):
            sys.exit(-1)
        max_stored_in_db-=1
    
    print("Everything FINE!")
    

if __name__ == '__main__':

    #Establishing DB connection + parse argv
    bootstrap_db()

    #Start fetching 
    iterative_fetch()

    #Final integrity check
    integrity_check()

    #Close DB connection
    close_db()

    #Particular blocks hashes:
    #00000000003e997ad827fbd44c040e7cbeddf8c5014a2128064a5879a0282196 (zicco99 ops)
    #00000000000068985ffa6adcb5ed373efd060b0ab80ef3ee609571269b44d518 (Bitcoin Exchange)


    
  
    

