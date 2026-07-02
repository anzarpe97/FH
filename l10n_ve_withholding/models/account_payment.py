# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2022-Present.
#
#
###############################################################################
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = "account.payment"

    #created to record retention percentages
    comment_withholding = fields.Char('Comment withholding')

    def _get_fiscal_period(self, date):
        str_date = str(date).split('-')
        vals = 'AÑO '+str_date[0]+' MES '+str_date[1]
        return vals

    @api.onchange('journal_id')
    def _onchange_compute_amount_currency(self):
        for rec in self:
            pass
            if rec.other_currency and rec.payment_group_id:
                if rec.payment_group_id.payments_amount <= 0:
                    rec.amount = rec.payment_group_id.selected_finacial_debt
                if rec.payment_group_id and rec.payment_group_id.payments_amount > 0:
                    rec.amount = 0
                    payments_amount = rec.payment_group_id.selected_finacial_debt - \
                        rec.payment_group_id.payments_amount
                    rec.amount = rec.company_id.currency_id._convert(
                        payments_amount, rec.currency_id, rec.company_id, rec.date)
            if not rec.other_currency and rec.payment_group_id:
                rec.amount = rec.payment_group_id.selected_finacial_debt
                if rec.payment_group_id and rec.payment_group_id.payments_amount > 0:
                    payments_amount = rec.payment_group_id.payments_amount - rec.amount
                    rec.amount = rec.payment_group_id.selected_finacial_debt - \
                        payments_amount

    @api.onchange('date')
    def _onchange_compute_amount_currency_date(self):
        for rec in self:
            if rec.other_currency and rec.payment_group_id:
                rec.amount_company_currency = rec.currency_id._convert(
                    rec.amount, rec.company_id.currency_id,
                    rec.company_id, rec.date)


    """
        Tengo que hacer esto para mostrar los campos en bolivares e estan desde la factura y no existan problemas con el tema de los decimales.
    """
    def get_amount_untaxed_bs(self):
        logging.info("--------------*---------------------")
        for rec in self:
            logging.info(rec.reconciled_bill_ids.amount_untaxed_bs)

            if rec.reconciled_bill_ids:
                return rec.reconciled_bill_ids.amount_untaxed_bs
            else:
                return 1.00

    def get_amount_total_bs(self):
        for rec in self:
            if rec.reconciled_bill_ids:
                return rec.reconciled_bill_ids.amount_total_bs
            else:
                return 1.00
    


    def get_amount_tax_bs(self):
        for rec in self:
            if rec.reconciled_bill_ids:
                return rec.reconciled_bill_ids.amount_tax_bs
            else:
                return 1.00

    