from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_investor = fields.Boolean(string="Investor", default=False)


    def _ensure_wallet(self):
        Wallet = self.env['investor.wallet']
        for partner in self:
            if partner.is_investor:
                if not Wallet.search([('partner_id', '=', partner.id)], limit=1):
                    Wallet.create({'partner_id': partner.id})
            else:
                # Optional: delete wallet if they are no longer an investor
                wallets = Wallet.search([('partner_id', '=', partner.id)])
                wallets.unlink()

    @api.model
    def create(self, vals):
        partner = super().create(vals)
        partner._ensure_wallet()
        return partner

    def write(self, vals):
        res = super().write(vals)
        if 'is_investor' in vals:
            self._ensure_wallet()
        return res

    def contact_xlsx_report(self):
        self.ensure_one()  # make sure only one record is processed
        return {
            'type': 'ir.actions.act_url',
            'url': f'/contacts/excel/report/{self.id}',
            'target': 'new'
        }
