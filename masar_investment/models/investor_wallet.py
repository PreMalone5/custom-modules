from odoo import models, fields, api
from odoo.exceptions import ValidationError

class InvestorWallet(models.Model):
    _name = 'investor.wallet'
    _description = 'Investor Wallet'
    _inherit = ['mail.thread','mail.activity.mixin']


    partner_id = fields.Many2one(
        'res.partner', string='Investor', required=True,
        domain="[('is_investor','=',True)]",
        tracking=1
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.user.company_id.currency_id.id,
        help='Currency for the wallet',
        tracking=1
    )
    balance = fields.Monetary(
        string='Balance', currency_field='currency_id',
        compute='_compute_balance', store=True,
        help='Computed from transactions',
        tracking=1
    )
    transaction_ids = fields.One2many(
        'investor.wallet.transaction', 'wallet_id',
        string='Transactions'
    )

    @api.constrains('partner_id')
    def _check_investor_status(self):
        for wallet in self:
            if not wallet.partner_id.is_investor:
                raise ValidationError("Only partners marked as investors can have a wallet.")

    @api.depends('transaction_ids.amount')
    def _compute_balance(self):
        for wallet in self:
            wallet.balance = sum(wallet.transaction_ids.mapped('amount'))

    def action_add_balance(self, amount):
        if amount <= 0:
            raise ValidationError('Amount must be greater than zero.')
        self.env['investor.wallet.transaction'].create({
            'wallet_id': self.id,
            'amount': amount,
            'type': 'deposit',
        })

    def action_withdraw_balance(self, amount):
        if amount <= 0:
            raise ValidationError('Amount must be greater than zero.')
        if self.balance < amount:
            raise ValidationError('Insufficient balance.')
        self.env['investor.wallet.transaction'].create({
            'wallet_id': self.id,
            'amount': -amount,
            'type': 'withdrawal',
        })

    def action_resync_investments(self):
        for wallet in self:
            properties = self.env['property'].search([('partner_id', '=', wallet.partner_id.id)])
            properties._sync_wallet_transactions()

