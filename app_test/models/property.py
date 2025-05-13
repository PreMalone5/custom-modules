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
    # --- existing related fields ---
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
    # 1) show the project’s total profit
    x_project_profit = fields.Monetary(
        related='project_id.profit',
        currency_field='currency_id',
        string="Project Profit",
        # store=True,
    )
    # 2) compute this investor’s share of profit
    investor_profit = fields.Monetary(
        string="Investor Profit",
        currency_field='currency_id',
        compute='_compute_investor_profit',
        # store=True,
    )
    # your existing Invesment Ratio / fill fields …
    invest_ratio = fields.Float(
        string="Investment (%)",
        compute="_compute_invest_ratio",
        # store=True,
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
        # store=True,
        digits=(6, 2)
    )
    total_project_cost = fields.Monetary(
        string="Total Project Cost",
        compute='_compute_total_project_cost',
        store=True,
        currency_field='currency_id'
    )

    term_line_ids = fields.One2many('property.term.line', 'property_id', string="Project Terms")


    @api.depends('x_project_cost', 'term_line_ids.term_type', 'term_line_ids.amount')
    def _compute_total_project_cost(self):
        for record in self:
            additional_total = sum(
                line.amount for line in record.term_line_ids
                if line.term_type == 'additional'
            )
            record.total_project_cost = record.x_project_cost + additional_total

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
            # allocate profit in proportion to investment
            if record.x_project_cost and record.x_project_profit:
                ratio = record.invested_amount / record.x_project_cost
                record.investor_profit = record.x_project_profit * ratio
            else:
                record.investor_profit = 0.0

    @api.constrains('invested_amount', 'project_id')
    def _check_total_investment_per_project(self):
        for record in self:
            if not record.project_id:
                continue
            total = sum(
                self.env['property'].search([
                    ('project_id', '=', record.project_id.id),
                    ('id', '!=', record.id)
                ]).mapped('invested_amount')
            ) + record.invested_amount
            if record.x_project_cost and total > record.x_project_cost:
                raise ValidationError(
                    f"Total invested amount ({total}) exceeds the project cost ({record.x_project_cost})."
                )

    def property_xlsx_report(self):
        return {
                'type': 'ir.actions.act_url',
                'url' : '/property/excel/report',
                'target' : 'new'
        }