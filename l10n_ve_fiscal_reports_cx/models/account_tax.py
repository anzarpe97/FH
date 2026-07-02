# coding: utf-8


from odoo import fields,models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_ve_aliquot_type = fields.Selection(
            [('exento', 'Exempt'),
             ('general', 'General Aliquot'),
             ('reducido', 'Reducted Aliquot'),
             ('adicional', 'General Aliquot + Additional')],
            'Aliquot Type',
            required=False,
            help='Specify the aliquote type for the tax so it can be processed'
                 ' accrordly when the sale/purchase book is generatred')
