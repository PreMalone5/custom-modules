from odoo import models, fields

class ProjectTermLine(models.Model):
    _name = 'project.term.line'
    _description = 'Project Term Line'

    project_id = fields.Many2one('project.project', string="Project", required=True)
    term_type = fields.Char(string="Term Type", required=True)
    amount = fields.Monetary(string="Amount")
    currency_id = fields.Many2one('res.currency', string="Currency")
