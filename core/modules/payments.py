from solar_crypto.transactions.builder.transfer import Transfer
# from solar_crypto.transactions.builder.multi_payment import MultiPayment
import time
import logging

class Payments:
    def __init__(self, config, sql, dynamic, utility, exchange):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.sql = sql
        self.dynamic = dynamic
        self.utility = utility
        self.exchange = exchange
        self.client = self.utility.get_client()

    '''
    def non_accept_check(self, c, a):
        removal_check = []
        for k, v in c.items():
            if k not in a:
                self.logger.info("Transaction ID Not Accepted")
                removal_check.append(v)
                self.sql.open_connection()
                self.sql.delete_transaction_record(k)
                self.sql.close_connection()
        return removal_check
    '''
    
    def get_nonce(self):
        n = self.client.wallets.get(self.config.delegate)
        return int(n['data']['nonce'])

    '''
    def build_transfer_transaction(self, address, amount, vendor, fee, nonce):
        # python3 crypto version    
        transaction = Transfer(recipientId=address, amount=amount, vendorField=vendor)
        transaction.set_fee(fee)
        transaction.set_nonce(int(nonce))
        transaction.sign(self.config.passphrase)

        sp = self.config.secondphrase
        if sp == 'None':
            sp = None
        if sp is not None:
            transaction.second_sign(sp)

        transaction_dict = transaction.to_dict()
        return transaction_dict
    '''

    def build_transfer_transaction(self, payments, nonce):
        f = self.dynamic.get_dynamic_fee(len(payments))
        transaction = Transfer(vendorField=self.config.message)
        transaction.set_fee(f)
        transaction.set_nonce(int(nonce))

        for i in payments:
            # exchange processing
            if i[1] in self.config.convert_address and self.config.exchange == "Y":
                index = self.config.convert_address.index(i[1])
                pay_in = self.exchange.exchange_select(index, i[1], i[2], self.config.provider[index])
                transaction.add_transfer(i[2], pay_in)
            else:
                transaction.add_transfer(i[2], i[1])

        transaction.sign(self.config.passphrase)
        sp = self.config.secondphrase
        if sp == 'None':
            sp = None
        if sp is not None:
            transaction.second_sign(sp)
    
        transaction_dict = transaction.to_dict()
        return transaction_dict
    
    '''
    def broadcast_standard(self, tx):
        # broadcast to relay
        try:
            transaction = self.client.transactions.create(tx)
            self.logger.info(f"Transaction: {transaction}")
            records = [[j['recipientId'], j['amount'], j['id']] for j in tx]
            time.sleep(1)
        except BaseException as e:
            # error
            self.logger.error(f"Something went wrong {e}")
            quit()

        self.sql.open_connection()
        self.sql.store_transactions(records)
        self.sql.close_connection()
    
        return transaction['data']['accept']
    '''
    
    def broadcast_transfer(self, tx):    
        # broadcast to relay
        try:
            transaction = self.client.transactions.create(tx)
            self.logger.info(f"Transaction: {transaction}")
            for i in tx:
                records = []
                id = i['id']
                records = [[j['recipientId'], j['amount'], id] for j in i['asset']['payments']]
            time.sleep(1)
        except BaseException as e:
            # error
            self.logger.error(f"Something went wrong: {e}")
            quit()
    
        self.sql.open_connection()
        self.sql.store_transactions(records)
        self.sql.close_connection()
        
        return transaction['data']['accept']
