#!/usr/bin/env python
from config.configure import Configure
from network.network import Network
from modules.allocate import Allocate
from modules.blocks import Blocks
from modules.initialize import Initialize
from modules.payments import Payments
from modules.stage import Stage
from modules.voters import Voters
from utility.database import Database
from utility.sql import Sql
from utility.utility import Utility
import sys
import time


if __name__ == '__main__':
    print("Start Script")
    # get configuration
    config = Configure()
    
    # load network
    network = Network(config.network)
    
    # load utility
    utility = Utility(network)
    
    # connect to core and tbw script database
    database = Database(config, network)
    sql = Sql()
    
    # check if initialized
    Initialize(config, database, sql)
    
    # get blocks
    block = Blocks(config, database, sql)
    
    # get last block to start
    last_block = block.get_last_block()
    
    # use last block timestamp to get all new blocks
    new_blocks = block.get_new_blocks(last_block)
    
    # store all new blocks
    block.store_new_blocks(new_blocks)
    
    # get unprocessed blocks
    unprocessed_blocks = block.return_unprocessed_blocks()
    
    # allocate block rewards
    allocate = Allocate(database, config, sql)
    voter_options = Voters(config, sql)
    
    for unprocessed in unprocessed_blocks:
        print(unprocessed)
        block_timestamp = unprocessed[1]
        # get vote and unvote transactions
        vote, unvote = allocate.get_vote_transactions(block_timestamp)
        # create voter_roll
        voter_roll = allocate.create_voter_roll(vote, unvote)
        # get voter_balances
        voter_balances = allocate.get_voter_balance(unprocessed, voter_roll)
        print("\noriginal voter_balances")
        for k, v in voter_balances.items():
            print(k,v)
        # run voters through various vote_options
        if config.whitelist == 'Y':
            voter_balances = voter_options.process_whitelist(voter_balances)
        if config.whitelist == 'N' and config.blacklist =='Y':
            voter_balances = voter_options.process_blacklist(voter_balances)
        print("\n voter_balances post whitelist or blacklist")
        for k, v in voter_balances.items():
            print(k,v)
            
        voter_balances = voter_options.process_voter_cap(voter_balances)
        print("\n voter_balances post voter cap")
        for k, v in voter_balances.items():
            print(k,v)
 
        voter_balances = voter_options.process_voter_min(voter_balances)
        print("\n voter_balances post voter min")
        for k, v in voter_balances.items():
            print(k,v)
 
        voter_balances = voter_options.process_anti_dilution(voter_balances)
        print("\n voter_balances post anti_dulite")
        for k, v in voter_balances.items():
            print(k,v)
        
        # allocate block rewards
        allocate.block_allocations(unprocessed, voter_balances)
        # get block count
        block_count = block.block_counter()
        print(f"\nCurrent block count : {block_count}")
        time.sleep(10)
    
    
    quit()
    # stage payments
    Stage(config, sql)
    quit()
    # process payment
    Payments(config, sql)
    quit()
    
    print("End Script")
