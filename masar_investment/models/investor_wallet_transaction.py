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
        ('deposit', 'ايداع'),
        ('withdrawal', 'سحب'),
        ('profit', 'Profit'),
        ('investment', 'Investment'),
        ('expense', 'Expense'),
        ('charity', 'زكاه'),
        ('company_share', 'حصة شركة'),
    ], string='Type', required=True)
    create_date = fields.Datetime(string='Date', readonly=True)
    transaction_date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    note = fields.Text(string='Notes')

    # NEW: Link to a project
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        domain="[('id', 'in', available_project_ids)]"
    )

    available_project_ids = fields.Many2many(
        'project.project',
        compute='_compute_available_projects',
        string='Available Projects'
    )

    @api.depends('wallet_id.partner_id')
    def _compute_available_projects(self):
        for rec in self:
            if rec.wallet_id and rec.wallet_id.partner_id:
                props = self.env['property'].search([('partner_id', '=', rec.wallet_id.partner_id.id)])
                rec.available_project_ids = props.mapped('project_id')
            else:
                rec.available_project_ids = [(5, 0, 0)]

    @api.onchange('type', 'amount')
    def _onchange_type_amount(self):
        for rec in self:
            if rec.amount is False:
                continue
            if rec.type in ('deposit', 'profit') and rec.amount < 0:
                rec.amount = -rec.amount
            elif rec.type in ('withdrawal', 'investment', 'charity', 'company_share') and rec.amount > 0:
                rec.amount = -rec.amount

    @api.constrains('amount', 'wallet_id', 'type')
    def _check_wallet_balance_limit(self):
        for rec in self:
            if not rec.wallet_id:
                continue
            other_tx = rec.wallet_id.transaction_ids.filtered(lambda t: t.id != rec.id)
            new_balance = sum(other_tx.mapped('amount')) + rec.amount

            if rec.type in ('withdrawal', 'investment') and new_balance < 0:
                raise ValidationError("This transaction would cause the wallet balance to go below zero.")

    # def unlink(self):
    #     for rec in self:
    #         if rec.type in ('investment', 'profit', 'expense'):
    #             raise ValidationError("You cannot delete system-generated transactions like investment, profit, or expense.")
    #     return super().unlink()

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        fields = super().fields_get(allfields=allfields, attributes=attributes)

        if 'type' in fields:
            if attributes is None or 'selection' in attributes:
                original_selection = fields['type'].get('selection', [])
                fields['type']['selection'] = [
                    item for item in original_selection
                    if item[0] not in ('investment', 'profit', 'expense')
                ]

        return fields