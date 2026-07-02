# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.tools.translate import _
from odoo.addons import decimal_precision as dp
from datetime import timedelta, datetime, date
from odoo.exceptions import ValidationError
import logging

class SeniatVatLedger(models.Model):
    STATES = [('draft', 'Draft'),
              ('confirmed', 'Confirmed'),
              ('done', 'Done'),
              ('cancel', 'Cancel')]

    TYPES = [('sale', 'Sale Ledger'),
             ('purchase', 'Purchase Ledger')]

    @api.model
    def _get_type(self):
        context = self._context or {}
        return context.get('type', 'purchase')

    _description = "Venezuela's Sale & Purchase Vat Ledger"
    _name = 'seniat.vat.ledger'

    name = fields.Char(string='Description', size=256, required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda 
                                 self: self.env.user.company_id.id, help='Company', 
                                 required=True)
    date_start = fields.Date(string='Begin Date', help="Begin date of period")
    date_end = fields.Date(string='End date', help="End date of period")
    state = fields.Selection(STATES, string='Status', required=True, readonly=True,
                             default='draft')
    type = fields.Selection(TYPES, string='Type', required=True,
                            default=lambda s: s._get_type(),
                            help="Select Sale for Customers and Purchase for Suppliers")
    line_ids = fields.One2many('seniat.vat.ledger.line', 'ledger_id', 'Vat Ledger Lines',
                              help='Lines being recorded in the book')
    note = fields.Text('Note')


    def action_cancel(self):
        """ Call cancel_move and return True
        """
        self.clear_lines()
        self.write({'state': 'cancel'})
        return True

    def action_confirmed(self):
        """ Call action_confirmed and return True
        """
        self.write({'state': 'confirmed'})
        return True

    def action_done(self):
        """ Call action_done and return True
        """
        self.write({'state': 'done'})
        return True

    def set_to_draft(self):
        self.write({'state': 'draft'})
        return True

    @api.model
    def get_amount_exempt(self, type, invoice_id):
        """
        """
        amount = 0
        sqle="""
        SELECT SUM(l.price_subtotal) AS exento
        FROM account_move_line AS l 
        INNER JOIN account_move_line_account_tax_rel AS r ON l.id=r.account_move_line_id 
        INNER JOIN account_tax AS t ON r.account_tax_id=t.id 
        WHERE  t.type_tax_use='%s' AND t.amount=0 AND l.move_id=%d
        """%(type,invoice_id)
        self._cr.execute(sqle)
        result = self._cr.fetchone()
        if result:
            amount = result[0]

        return amount

    @api.model
    def get_vat_tax(self, type_doc,type_aliq, invoice_id):
        """
        """
        result = {'base':0,'tax_amount':0,'percent_amount':0}
        sqle="""
        SELECT t.amount AS percent_amount,
        COALESCE(l.tax_base_amount,0) AS base_amount,
        COALESCE(l.price_subtotal,0) AS tax_amount
        FROM  account_tax AS t 
        INNER JOIN account_move_line AS l ON t.id=l.tax_line_id  
        WHERE t.type_tax_use='%s' AND t.l10n_ve_aliquot_type='%s' AND l.move_id=%d
        """%(type_doc,type_aliq,invoice_id)
        self._cr.execute(sqle)
        res = self._cr.fetchone()
        if res:
            result['percent_amount'] = res[0]
            result['base'] = res[1]
            result['tax_amount'] = res[2]

        return result

    @api.model
    def get_withheld_amount(self, type_tax, invoice_id):
        """
        """
        result = {'withholding_number':'','withheld_amount':0}
        sql="""
        SELECT p.withholding_number AS number_wh,p.amount AS amount_wh,l.move_id AS invoice 
        FROM  account_tax AS t INNER JOIN account_payment  AS p ON t.id=p.tax_withholding_id 
        INNER JOIN account_move_line_payment_group_to_pay_rel AS g ON p.payment_group_id=g.payment_group_id 
        INNER JOIN account_move_line AS l ON g.to_pay_line_id=l.id 
        WHERE t.type_tax_use='%s' AND t.withholding_type='partner_tax' AND l.move_id=%d
        """%(type_tax,invoice_id)
        self._cr.execute(sql)
        res = self._cr.fetchone()
        if res:
            result['withholding_number'] = res[0]
            result['withheld_amount'] = res[1]

        return result

    @api.model
    def get_invoices(self):
        """ Return string with data of the current document
        """
        result = {}
        move_obj = self.env['account.move']
        line_obj = self.env['seniat.vat.ledger.line']
        if self.type == 'purchase':
            invoices = move_obj.search([
                    ('invoice_date', '>=', self.date_start),
                    ('invoice_date', '<=', self.date_end),
                    ('state', 'not in', ['cancel','draft']),
                    ('type', 'in', ['in_invoice', 'in_refund'])])
        else:
            invoices = move_obj.search([
                    ('invoice_date', '>=', self.date_start),
                    ('invoice_date', '<=', self.date_end),
                    ('state', 'not in', ['cancel','draft']),
                    ('type', 'in', ['out_invoice', 'out_refund'])])
        if invoices:
            for invoice in invoices:
                vat = ''
                affected_invoice = ''
                credit_note_number = ''
                wh_number = ''
                doc_type = '01'
                tax_base_amount = 0
                tax_withheld_amount = 0
                tax_withholding_rate = 0
                vat_reduced_withheld = 0
                vat_general_withheld = 0
                vat_additional_withheld = 0
                if self.type == 'purchase':
                    invoice_number = invoice.ref or ''
                    type_tax = 'supplier'
                else:
                    invoice_number = invoice.name
                    type_tax = 'customer'
                ref = invoice_number
              

                if ref and invoice.l10n_ve_document_number:
                    ref += ' / ' + invoice.l10n_ve_document_number


                if invoice.partner_id.vat and invoice.partner_id.l10n_latam_identification_type_id:
                    vat = invoice.partner_id.l10n_latam_identification_type_id.l10n_ve_code+invoice.partner_id.vat
                if invoice.type in ('in_refund', 'out_refund'):
                    doc_type = '03'
                    credit_note_number = invoice_number
                    invoice_number = ''
                    if invoice.type == 'in_refund':
                        affected_invoice = invoice.reversed_entry_id.ref
                    else:
                        affected_invoice = invoice.reversed_entry_id.name

                withholding_tax = self.get_withheld_amount(type_tax,invoice.id)
                if withholding_tax['withholding_number']:
                    tax_withholding_rate = invoice.partner_id.vat_retention
                    tax_withheld_amount = withholding_tax['withheld_amount']
                    wh_number = withholding_tax['withholding_number']

                tax_reduced = self.get_vat_tax(self.type, 'reducido', invoice.id)
                vat_reduced_rate = tax_reduced['percent_amount']
                vat_reduced_base = tax_reduced['base']
                vat_reduced_tax = tax_reduced['tax_amount']
                if vat_reduced_tax and tax_withheld_amount:
                    tax_base_amount = vat_reduced_base
                    vat_reduced_withheld = tax_withheld_amount

                tax_general = self.get_vat_tax(self.type, 'general', invoice.id)
                vat_general_rate = tax_general['percent_amount']
                vat_general_base = tax_general['base']
                vat_general_tax = tax_general['tax_amount']
                if vat_general_tax and tax_withheld_amount:
                    tax_base_amount = vat_general_base
                    vat_general_withheld = tax_withheld_amount

                tax_additional = self.get_vat_tax(self.type, 'adicional', invoice.id)
                vat_additional_rate = tax_additional['percent_amount']
                vat_additional_base = tax_additional['base']
                vat_additional_tax = tax_additional['tax_amount']
                if vat_additional_tax and tax_withheld_amount:
                    tax_base_amount = vat_additional_base
                    vat_additional_withheld = tax_withheld_amount


                line_obj.create({'name': ref,'ledger_id': self.ids[0], 
                                'company_id': invoice.company_id.id,
                                'invoice_id': invoice.id,
                                'partner_name': invoice.partner_id.name,
                                'partner_vat': vat,
                                'doc_type': doc_type,
                                'invoice_date': invoice.invoice_date,
                                'invoice_number': invoice_number,
                                'document_number': invoice.l10n_ve_document_number,
                                'credit_note_number': credit_note_number,
                                'withholding_number': wh_number,
                                'affected_invoice': affected_invoice,
                                'total_amount': invoice.amount_total,
                                'exempt_amount': self.get_amount_exempt(self.type, invoice.id),
                                'vat_reduced_rate': vat_reduced_rate,
                                'vat_reduced_base': vat_reduced_base,
                                'vat_reduced_tax': vat_reduced_tax,
                                'vat_reduced_withheld': vat_reduced_withheld,
                                'vat_general_rate': vat_general_rate,
                                'vat_general_base': vat_general_base,
                                'vat_general_tax': vat_general_tax,
                                'vat_general_withheld': vat_general_withheld,
                                'vat_additional_rate': vat_additional_rate,
                                'vat_additional_base': vat_additional_base,
                                'vat_additional_tax': vat_additional_tax,
                                'vat_general_withheld': vat_general_withheld,
                                'tax_base_amount': tax_base_amount,
                                'tax_withheld_amount': tax_withheld_amount,
                                'tax_withholding_rate': tax_withholding_rate
                                })
        return True

    def clear_lines(self):
        """ Clear lines of current withholding document and delete wh document
        information from the invoice.
        """
        if self.ids:
            lines = self.env['seniat.vat.ledger.line'].search([
                ('ledger_id', 'in', self.ids)])

            if lines: lines.unlink()

        return True

    def action_get_lines(self):
        """ 
        """
        cl = self.clear_lines()
        resp = self.get_invoices()

        return True


class SeniatVatLedgerLines(models.Model):
    _description = "Venezuela's Sale & Purchase Vat Ledger Lines"
    _name = 'seniat.vat.ledger.line'


    name = fields.Char(string='Lines')
    ledger_id = fields.Many2one('seniat.vat.ledger', 'Seniat Vat Ledger',
                            help='Vat Ledger that owns this line', ondelete='cascade', index=True)
    company_id = fields.Many2one(related='ledger_id.company_id', store=True, readonly=True)
    invoice_id = fields.Many2one('account.move', 'Invoice',
                                 help='Invoice related to this line')
    partner_name = fields.Char(string='Partner Name', size=128, help='')
    partner_vat = fields.Char(string='RIF', size=128, help='')
    doc_type = fields.Char(string='Doc. Type', size=8, help='Document Type')
    invoice_date = fields.Date(string='Invoice Date', help='')
    invoice_number = fields.Char(string='Invoice number', size=64, help='')
    credit_note_number = fields.Char(string='Credit Notes', size=64, help='')
    debit_note_number = fields.Char(string='Debit Notes', size=64, help='')
    document_number = fields.Char(string='Invoice Control number', size=64, help='Number used to manage pre-printed invoice')
    withholding_number = fields.Char(string='Withholding number', size=64, help='')
    affected_invoice = fields.Char(string='Affected Invoice', size=64,
                                   help='For an invoice line type means parent invoice for a Debit'
                                        ' or Credit Note. For an withholding line type means the invoice'
                                        ' number related to the withholding')
    total_amount = fields.Float(string='Total', help='')
    exempt_amount = fields.Float(string='Exempt', help='Exempt is a Tax with 0 tax percentage')

    # === Vat Amount fields ===
    vat_reduced_rate = fields.Float(string='Reduced rate',help='Vat reduced tax rate')
    vat_reduced_base = fields.Float(string='Reduced Base', help='Vat Reduced Base Amount')
    vat_reduced_tax = fields.Float(string='Reduced Tax', help='Vat Reduced Tax Amount')
    vat_reduced_withheld = fields.Float(string='Reduced amount withheld', help='Vat Reduced Tax Amount')
    vat_general_rate = fields.Float(string='General rate', help='Vat general tax rate ')
    vat_general_base = fields.Float(string='General Base', help='Vat General Base Amount')
    vat_general_tax = fields.Float(string='General Tax', help='Vat General Tax Amount')
    vat_general_withheld = fields.Float(string='General amount withheld', help='Vat General Tax Amount')
    vat_additional_rate = fields.Float(string='Additional rate', help='Vat plus additional tax rate ')
    vat_additional_base = fields.Float(string='Additional Base', help='Vat General plus Additional Base Amount')
    vat_additional_tax = fields.Float(string='Additional Tax', help='Vat General plus Additional Tax Amount')
    vat_additional_withheld = fields.Float(string='Additional amount withheld', help='Vat General plus Additional Tax Amount')
    tax_base_amount = fields.Float(string='Taxable Amount', help='Amount used as Taxing Base')
    tax_withheld_amount = fields.Float(string='Taxed Amount', help='Taxed Amount on Taxing Base')
    tax_withholding_rate = fields.Float(string='Rate',nhelp="Withholding percentage")
