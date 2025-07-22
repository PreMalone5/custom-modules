from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Property(models.Model):
    _name = "property"
    _description = "Property"

    partner_id = fields.Many2one('res.partner', string='Investor Name')
    description = fields.Text(string='Description')
    invested_amount = fields.Float(string='Invested Amount')
    project_id = fields.Many2one('project.project', string='Project')
    currency_id = fields.Many2one(
        'res.currency',
        related='project_id.currency_id',
        store=True,
        readonly=True
    )
    x_project_cost = fields.Monetary(
        related='project_id.project_cost',
        currency_field='currency_id',
        string="Project Cost",
        store=True,
    )
    x_project_type = fields.Selection(
        related='project_id.project_type',
        string="Project Type",
        store=True,
    )
    x_project_profit = fields.Monetary(
        related='project_id.profit',
        currency_field='currency_id',
        string="Project Profit",
    )
    investor_profit = fields.Monetary(
        string="Investor Profit",
        currency_field='currency_id',
        compute='_compute_investor_profit',
    )
    last_synced_profit = fields.Monetary(
        string="Last Synced Profit",
        currency_field='currency_id'
    )
    invest_ratio = fields.Float(
        string="Investment (%)",
        compute="_compute_invest_ratio",
        digits=(6, 2)
    )
    project_fill_percent = fields.Float(
        string="Project Fill (%)",
        compute="_compute_project_fill",
        store=True
    )
    remaining_investable_amount = fields.Monetary(
        string="Remaining Investable",
        compute="_compute_project_fill",
        currency_field='currency_id',
        store=True
    )
    roi_ratio = fields.Float(
        string="ROI (%)",
        compute="_compute_roi_ratio",
        digits=(6, 2)
    )
    total_project_cost = fields.Monetary(
        string="Total Project Cost",
        compute='_compute_total_project_cost',
        store=True,
        currency_field='currency_id'
    )

    @api.depends('x_project_cost', 'invested_amount')
    def _compute_invest_ratio(self):
        for record in self:
            record.invest_ratio = (record.invested_amount or 0.0) * 100.0 / (record.x_project_cost or 1.0)

    @api.depends('investor_profit', 'invested_amount')
    def _compute_roi_ratio(self):
        for record in self:
            if record.invested_amount:
                profit_diff = record.investor_profit - record.invested_amount
                record.roi_ratio = (profit_diff / record.invested_amount) * 100
            else:
                record.roi_ratio = 0.0

    @api.depends('project_id', 'invested_amount')
    def _compute_project_fill(self):
        for record in self:
            if not record.project_id or not record.x_project_cost:
                record.project_fill_percent = 0.0
                record.remaining_investable_amount = 0.0
                continue
            all_props = self.env['property'].search([('project_id', '=', record.project_id.id)])
            total_invested = sum(all_props.mapped('invested_amount'))
            record.project_fill_percent = min(100.0, total_invested * 100.0 / record.x_project_cost)
            record.remaining_investable_amount = max(0.0, record.x_project_cost - total_invested)

    @api.depends('project_id', 'invested_amount', 'x_project_profit')
    def _compute_investor_profit(self):
        for record in self:
            if record.x_project_cost and record.x_project_profit:
                ratio = record.invested_amount / record.x_project_cost
                record.investor_profit = record.x_project_profit * ratio
            else:
                record.investor_profit = 0.0

    def property_xlsx_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/property/excel/report',
            'target': 'new'
        }

    @api.model
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('wallet_syncing'):
            records.with_context(wallet_syncing=True)._sync_wallet_transactions()
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('wallet_syncing'):
            self.with_context(wallet_syncing=True)._sync_wallet_transactions()
        return res

    def _sync_wallet_transactions(self):
        Wallet = self.env['investor.wallet']
        Transaction = self.env['investor.wallet.transaction']

        for record in self:
            if not record.partner_id or not record.partner_id.is_investor:
                continue

            wallet = Wallet.search([('partner_id', '=', record.partner_id.id)], limit=1)
            if not wallet:
                continue

            # --- 1. INVESTMENT TRANSACTION ---
            existing_invest_tx = Transaction.search([
                ('wallet_id', '=', wallet.id),
                ('project_id', '=', record.project_id.id),
                ('type', '=', 'investment')
            ], limit=1)

            if record.invested_amount and not existing_invest_tx:
                Transaction.create({
                    'wallet_id': wallet.id,
                    'amount': -record.invested_amount,
                    'type': 'investment',
                    'project_id': record.project_id.id,
                    'note': f'Investment for {record.project_id.name}'
                })

            # --- 2. PROFIT/EXPENSE TRANSACTION (Delta Logic) ---
            project_cost = record.x_project_cost or 0
            project_profit = record.x_project_profit or 0
            invested = record.invested_amount or 0
            new_profit = (project_profit * invested / project_cost) if project_cost else 0
            old_profit = record.last_synced_profit or 0
            delta = new_profit - old_profit

            if delta != 0:
                tx_type = 'profit' if delta > 0 else 'expense'
                Transaction.create({
                    'wallet_id': wallet.id,
                    'amount': delta,
                    'type': tx_type,
                    'project_id': record.project_id.id,
                    'note': f'{"Profit" if delta > 0 else "Expense"} for {record.project_id.name}'
                })
                record.last_synced_profit = new_profit

            # --- 3. UPDATE EXISTING NOTES TO MATCH CURRENT PROJECT NAME ---
            transactions_to_update = Transaction.search([
                ('wallet_id', '=', wallet.id),
                ('project_id', '=', record.project_id.id),
                ('type', 'in', ['investment', 'profit', 'expense'])
            ])

            for tx in transactions_to_update:
                expected_note = ''
                if tx.type == 'investment':
                    expected_note = f'Investment for {record.project_id.name}'
                elif tx.type == 'profit':
                    expected_note = f'Profit for {record.project_id.name}'
                elif tx.type == 'expense':
                    expected_note = f'Expense for {record.project_id.name}'

                if expected_note and tx.note != expected_note:
                    tx.note = expected_note

    @api.model
    def cron_sync_all_wallet_profits(self):
        self.search([])._sync_wallet_transactions()
