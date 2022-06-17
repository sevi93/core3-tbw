import logging

class Stage:
    def __init__(self, config, dynamic, sql, voters, delegate):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.dynamic = dynamic
        self.sql = sql
        self.voters = voters
        self.delegate = delegate
        
        # get transactions
        fees = self.get_transaction_fees()
        
        # stage delegate payments
        self.stage_delegate_payments(fees)
        
        # stage voter payments
        self.stage_voter_payments()
        
        
    def get_transaction_fees(self):
        delegate_tx = len([v for v in self.delegate.values() if v >= 0])
        voter_tx = len([v for v in self.voters.values() if v > 0])
        total_tx = voter_tx + delegate_tx
        self.logger.info(f"Total Transactions: {total_tx}")
        
        # check if multipayments
        # if self.config.multi == "Y":
        multi_limit = self.dynamic.get_multipay_limit()

        if total_tx % multi_limit == 0:
            numtx = round(total_tx / multi_limit)
        else:
            numtx = round(total_tx // multi_limit) + 1

        full_payments = total_tx // multi_limit
        full = int(full_payments * self.dynamic.get_dynamic_fee(multi_limit))
        partial_payments = total_tx % multi_limit
        partial = self.dynamic.get_dynamic_fee(partial_payments)
        transaction_fees = full + partial
            
        #else:
        #    transaction_fees = int(total_tx * self.dynamic.get_dynamic_fee())
        return transaction_fees
        
    
    def stage_delegate_payments(self, f):
        paid_delegate = {}
        count = 1
        for k, v in self.delegate.items():
            # this is the reserve account
            if count == 1:
                # reserve account insuffient to pay fees
                if (v - f) <= 0:
                    self.logger.error("Not enough to cover transaction fees in reserve")
                    self.logger.error("Update interval and restart")
                    quit()
                # process donation
                elif self.config.donate == "Y":
                    paid_donation = {}
                    donate_amt = int((self.config.donate_percent / 100) * v)
                    reserve_amt = v - donate_amt
                    paid_donation[self.config.donate_address] = donate_amt
                    
                    # update staging table with donation line
                    self.sql.open_connection()
                    self.sql.stage_payment(paid_donation, msg = "Donation")
                    self.sql.close_connection()
                    
                    # subtract out single tx fee because of extra donation tx
                    pay_amount = reserve_amt - self.dynamic.get_dynamic_fee(1)
                else:
                    pay_amount = v - f   
            else:
                pay_amount = v
            count += 1
            paid_delegate[k] = pay_amount
        self.logger.debug(f"Delegate Payments: {paid_delegate}")
        
        self.sql.open_connection()
        self.sql.update_delegate_paid_balance(paid_delegate)
        self.sql.stage_payment(paid_delegate, msg = "Reward")
        self.sql.close_connection()
    
    
    def stage_voter_payments(self):
        self.logger.debug("Voter Payments: {self.voters}")
        self.sql.open_connection()
        self.sql.update_voter_paid_balance(self.voters)
        self.sql.stage_payment(self.voters, msg = self.config.message)
        self.sql.close_connection()
