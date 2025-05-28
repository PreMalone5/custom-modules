from odoo import models

class Project(models.Model):
    _inherit = 'project.project'

    def write(self, vals):
        res = super().write(vals)
        if 'profit' in vals:
            self.env['property'].search([('project_id', 'in', self.ids)])._sync_wallet_transactions()
        return res
