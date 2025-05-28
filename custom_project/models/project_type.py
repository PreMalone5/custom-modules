from odoo import models, fields

class ProjectType(models.Model):
    _name = 'project.type'
    _description = 'Project Type'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')