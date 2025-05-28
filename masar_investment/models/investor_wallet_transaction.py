from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class InvestorWalletTransaction(models.Model):
    _name = 'investor.wallet.transaction'
    _description = 'Investor Wallet Transaction'
    _order = 'create_date desc'

    wallet_id = fields.Many2one(
        'investor.wallet', string='Wallet', required=True, ondelete='cascade'
    )
    amount = fields.Monetary(
        string='Amount', required=True,
        help='Signed amount: positive for profits/deposits, negative for withdrawals/investments'
    )
    currency_id = fields.Many2one(
        related='wallet_id.currency_id', store=True, readonly=True
    )
    type = fields.Selection([
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('profit', 'Profit'),
        ('investment', 'Investment'),
    ], string='Type', required=True)
    create_date = fields.Datetime(string='Date', readonly=True)
    note = fields.Text(string='Notes')

    @api.onchange('type', 'amount')
    def _onchange_type_amount(self):
        for rec in self:
            if rec.amount is False:
                continue
            if rec.type in ('deposit', 'profit') and rec.amount < 0:
                rec.amount = -rec.amount
            elif rec.type in ('withdrawal', 'investment') and rec.amount > 0:
                rec.amount = -rec.amount

    @api.constrains('amount', 'wallet_id', 'type')
    def _check_wallet_balance_limit(self):
        for rec in self:
            if not rec.wallet_id:
                continue
            # Get other transactions (excluding current one)
            other_tx = rec.wallet_id.transaction_ids.filtered(lambda t: t.id != rec.id)
            new_balance = sum(other_tx.mapped('amount')) + rec.amount

            # For types that decrease balance, ensure it doesn't go negative
            if rec.type in ('withdrawal', 'investment') and new_balance < 0:
                raise ValidationError("This transaction would cause the wallet balance to go below zero.")