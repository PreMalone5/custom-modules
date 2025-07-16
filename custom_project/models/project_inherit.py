from odoo import models, fields, api

class ProjectProject(models.Model):
    _inherit = 'project.project'

    project_cost = fields.Monetary(string='Project Estimate', currency_field='currency_id')
    project_type = fields.Selection([
        ('development', 'Development'),
        ('external_investment', 'External investment'),
    ], string='Project Type')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string="Analytic Account",
        help="Link this project to an analytic account from the accounting module."
    )

    profit = fields.Monetary(
        related='analytic_account_id.balance',
        string='Profit',
        readonly=True,
    )

    term_line_ids = fields.One2many('project.term.line', 'project_id', string="Project Terms")

    total_project_cost = fields.Monetary(
        string="Project Total Cost",
        compute='_compute_total_project_cost',
        store=True,
        currency_field='currency_id'
    )

    @api.model
    def create(self, vals):
        projects = super().create(vals)
        projects = projects if isinstance(projects, models.Model) else self.browse(projects.ids)

        for project in projects:
            if project.analytic_account_id:
                project.analytic_account_id.write({'name': project.name})
        return projects

    def write(self, vals):
        result = super().write(vals)
        for project in self:
            if project.analytic_account_id and 'name' in vals:
                project.analytic_account_id.write({'name': project.name})
        return result

    @api.depends('project_cost', 'term_line_ids.amount')
    def _compute_total_project_cost(self):
        for record in self:
            terms_total = sum(line.amount for line in record.term_line_ids)
            record.total_project_cost = (record.project_cost or 0.0) + terms_total

    def action_open_investors(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Project Investors',
            'res_model': 'property',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def projects_xlsx_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/projects/excel/report/{self.id}',
            'target': 'new'
        }
