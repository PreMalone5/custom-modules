from odoo import models, fields, api
from odoo.exceptions import ValidationError

class InvestorWallet(models.Model):
    _name = 'investor.wallet'
    _description = 'Investor Wallet'

    partner_id = fields.Many2one(
        'res.partner', string='Investor', required=True,
        help='Related investor'
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.user.company_id.currency_id.id,
        help='Currency for the wallet'
    )
    balance = fields.Monetary(
        string='Balance', currency_field='currency_id', default=0.0,
        help='Current balance in the wallet'
    )
    add_amount = fields.Monetary(
        string='Add Amount', currency_field='currency_id', default=0.0,
        help='Amount to add to the balance'
    )

    def action_add_balance(self):
        """
        Add the specified amount to the wallet balance and reset the field.
        """
        for wallet in self:
            if wallet.add_amount <= 0:
                raise ValidationError('Please enter a positive amount to add.')
            wallet.balance += wallet.add_amount
            wallet.add_amount = 0.0