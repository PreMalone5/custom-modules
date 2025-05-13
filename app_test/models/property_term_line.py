from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PropertyTermLine(models.Model):
    _name = 'property.term.line'
    _description = 'Project Term Line'

    property_id = fields.Many2one('property', string="Property")
    term_type = fields.Selection([
        ('building', 'Building'),
        ('purchase', 'Purchase'),
        ('other', 'Other')
    ], string="Term Type", required=True)
    amount = fields.Monetary(string="Amount")
    currency_id = fields.Many2one('res.currency', string="Currency")

