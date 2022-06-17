#!/usr/bin/env python
from __init__ import __version__, __version_info__
from config.configure import Configure
from network.network import Network
from modules.exchange import Exchange
from modules.payments import Payments
from utility.dynamic import Dynamic
from utility.sql import Sql
from utility.utility import Utility
from threading import Event
import time
import datetime
import logging
import signal
import sys

def chunks(l, n):
    # For item i in a range that is a length of l
    for i in range(0, len(l), n):
        # Create an index range for l of n items:
        yield l[i:i+n]


def process_payments(payment, unprocessed, dynamic, config, exchange, sql):
    logger.info("Transfer Payment")
    logger.debug("Unprocesses payment :")
    logger.debug(unprocessed)
    signed_tx = []
    check = {} 
    request_limit = dynamic.get_tx_request_limit()
    multi_limit = dynamic.get_multipay_limit()
   
    #if len(unprocessed) == 1:
    #    process_standard_payments(payments, unprocessed, dynamic, config, exchange, sql)
    #else:
    temp_multi_chunk = list(chunks(unprocessed, multi_limit))
    
    # remove any items over request_tx_limit
    multi_chunk = temp_multi_chunk[:request_limit]
    nonce = payment.get_nonce() + 1
        
    for i in multi_chunk:
    #    if len(i) > 1:
        unique_rowid = [y[0] for y in i]
        tx = payment.build_transfer_transaction(i, str(nonce))
        check[tx['id']] = unique_rowid
        signed_tx.append(tx)
        nonce += 1        
        
    accepted = payment.broadcast_transfer(signed_tx)
        
    #check for accepted and non-accepted transactions
    for k, v in check.items():
        if k in accepted:
            # mark all accepted records complete
            sql.open_connection()
            sql.process_staged_payment(v)
            sql.close_connection()
        else:
            # delete all transaction records with relevant multipay txid
            logger.info("Transaction ID Not Accepted")
            sql.open_connection()
            sql.delete_transaction_record(k)
            sql.close_connection()

    # payment run complete
    logger.info('Payment Run Completed!')
    
'''
def process_standard_payments(payment, unprocessed, dynamic, config, exchange, sql):
    logger.info("Standard Payment")
    signed_tx = []
    check = {}

    # process unpaid transactions
    unique_rowid = [y[0] for y in unprocessed]

    temp_nonce = payment.get_nonce()+1
    transaction_fee = dynamic.get_dynamic_fee()
        
    for i in unprocessed:
        # exchange processing
        if i[1] in config.convert_address and config.exchange == "Y":
            index = config.convert_address.index(i[1])
            pay_in = exchange.exchange_select(index, i[1], i[2], config.provider[index])
            tx = payment.build_transfer_transaction(pay_in, (i[2]), i[3], transaction_fee, str(temp_nonce))
        # standard tx processing
        else:           
            tx = payment.build_transfer_transaction(i[1], (i[2]), i[3], transaction_fee, str(temp_nonce))
        check[tx['id']] = i[0]
        signed_tx.append(tx)
        temp_nonce += 1    
                     
    accepted = payment.broadcast_standard(signed_tx)
    for_removal = payment.non_accept_check(check, accepted)
            
    # remove non-accepted transactions from being marked as completed
    if len(for_removal) > 0:
        for i in for_removal:
            logger.debug("Removing RowId: ", i)
            unique_rowid.remove(i)
                    
    sql.open_connection()
    sql.process_staged_payment(unique_rowid)
    sql.close_connection()

    # payment run complete
    logger.info('Payment Run Completed!')
    '''

# Handler for SIGINT and SIGTERM
def sighandler(signum, frame):
    logger.info("SIGNAL {0} received. Starting graceful shutdown".format(signum))
    killsig.set()
    return


if __name__ == '__main__':    
    # get configuration
    config = Configure()
    if (config.error):
        print("FATAL: config file not found! Terminating PAY.", file=sys.stderr)
        sys.exit(1)

    # set logging
    logger = logging.getLogger()
    logger.setLevel(config.loglevel)
    outlog = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(config.formatter)
    outlog.setFormatter(formatter)
    logger.addHandler(outlog)

    # start script
    msg='> Starting PAY script %s @ %s' % (__version__, str(datetime.datetime.now()))
    logger.info(msg)

    # subscribe to signals
    killsig = Event()
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    # load network
    network = Network(config.network)
    
    # load utility and dynamic
    utility = Utility(network)
    dynamic = Dynamic(utility, config)
      
    # connect to tbw script database and exchange module
    sql = Sql()
    exchange = Exchange(sql, config)
    
    # MAIN FUNCTION LOOP SHOULD START HERE
    while True:
        sql.open_connection()
        check = sql.unprocessed_staged_payments()
        sql.close_connection()
    
        if check > 0:
            # staged payments detected
            logger.info("Staged Payments Detected.......Begin Payment Processing")
            payments = Payments(config, sql, dynamic, utility, exchange)
        
            sql.open_connection()
            #if config.multi == "Y":
            unprocessed = sql.get_staged_payment().fetchall()
            sql.close_connection()
            process_payments(payments, unprocessed, dynamic, config, exchange, sql)
            #else:
            #    unprocessed = sql.get_staged_payment(dynamic.get_tx_request_limit()).fetchall()
            #    sql.close_connection()
            #    process_standard_payments(payments, unprocessed, dynamic, config, exchange, sql)
 
        logger.info("End Script - Looping")
        #killsig.wait(data.block_check)
        killsig.wait(1200)
        if killsig.is_set():
            logger.debug("Kill switch set. Breaking the main loop.")
            break
    
    logger.info("< Terminating PAY script.")
