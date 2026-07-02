# coding: utf-8


import time
from datetime import datetime

from odoo import models, api, _
from odoo.exceptions import UserError, Warning, ValidationError


class SaleLedgerReport(models.AbstractModel):
    _name = 'report.l10n_ve_fiscal_reports_cx.template_sale_ledger'
    _description = 'Seniat Sale Ledger Report'

    total_exempt_amount = 0
    total_reduced_base = 0
    total_reduced_tax = 0
    total_general_base = 0
    total_general_tax = 0
    total_additional_base = 0
    total_additional_tax = 0
    total_amount = 0
    total_amount_base = 0
    total_amount_tax = 0
    total_amount_withheld = 0

    def _get_exempt_amount(self, ledger_id):
        exempt_amount = 0
        self.total_amount = 0
        self.total_amount_base = 0
        self.total_amount_tax = 0
        self.total_amount_withheld = 0
        sql="""
        SELECT sum(exempt_amount) AS  exempt
        FROM  seniat_vat_ledger_line  
        WHERE ledger_id=%d
        """%(ledger_id)
        self._cr.execute(sql)
        res = self._cr.fetchone()
        if res:
            exempt_amount = res[0]
            self.total_amount += exempt_amount
        self.total_exempt_amount = exempt_amount
        return exempt_amount

    def _get_vat_reduced(self, ledger_id):
        reduced_taxes = []
        self.total_reduced_base = 0
        self.total_reduced_tax = 0
        sql="""
        SELECT vat_reduced_rate, 
        COALESCE(SUM(vat_reduced_base * CASE WHEN doc_type='01' THEN 1 ELSE -1 END),0) AS base, 
        COALESCE(SUM(vat_reduced_tax * CASE WHEN doc_type='01' THEN 1 ELSE -1 END),0) AS tax, 
        COALESCE(SUM(vat_reduced_withheld * CASE WHEN doc_type='01' THEN 1 ELSE -1 END),0) AS withheld 
        FROM  seniat_vat_ledger_line  
        WHERE ledger_id=%d
        GROUP BY vat_reduced_rate
        ORDER BY vat_reduced_rate
        """%(ledger_id)
        self._cr.execute(sql)
        results = self._cr.fetchall()
        if results:
            for res in results:
                if res[0]:
                    reduced_taxes.append({'rate':res[0], 'base': res[1], 'tax':res[2], 'withheld':res[3]})
                    self.total_reduced_base += res[1]
                    self.total_reduced_tax += res[2]
                    self.total_amount += res[1]  + res[2]
                    self.total_amount_base += res[1]
                    self.total_amount_tax += res[2]
                    self.total_amount_withheld += res[3]
        else:
            reduced_taxes.append({'rate':'', 'base': 0, 'tax':0, 'withheld':0})
        return reduced_taxes

    def _get_vat_general(self, ledger_id):
        general_taxes = []
        self.total_general_base = 0
        self.total_general_tax = 0
        sql="""
        SELECT vat_general_rate,
        COALESCE(SUM(vat_general_base * CASE WHEN doc_type='01' THEN 1 ELSE -1 END),0) AS base,
        COALESCE(SUM(vat_general_tax * CASE WHEN doc_type='01' THEN 1 ELSE -1 END),0) AS tax,
        COALESCE(SUM(vat_general_withheld * CASE WHEN doc_type='01' THEN 1 ELSE -1 END),0) AS withheld
        FROM  seniat_vat_ledger_line  
        WHERE ledger_id=%d
        GROUP BY vat_general_rate
        ORDER BY vat_general_rate
        """%(ledger_id)
        self._cr.execute(sql)
        results = self._cr.fetchall()
        if results:
            for res in results:
                if res[0]:
                    general_taxes.append({'rate':res[0], 'base': res[1], 'tax':res[2], 'withheld':res[3]})
                    self.total_general_base += res[1]
                    self.total_general_tax += res[2]
                    self.total_amount += res[1] + res[2]
                    self.total_amount_base += res[1]
                    self.total_amount_tax += res[2]
                    self.total_amount_withheld += res[3]
        else:
            general_taxes.append({'rate':'', 'base': 0, 'tax':0, 'withheld':0})
        return general_taxes

    def _get_vat_additional(self, ledger_id):
        additional_taxes = []
        self.total_additional_base = 0
        self.total_additional_tax = 0
        sql="""
        SELECT vat_additional_rate,
        COALESCE(SUM(vat_additional_base * CASE WHEN doc_type='01' THEN 1 ELSE -1 END),0) AS base,
        COALESCE(SUM(vat_additional_tax * CASE WHEN doc_type='01' THEN 1 ELSE -1 END),0) AS tax,
        COALESCE(SUM(vat_additional_withheld * CASE WHEN doc_type='01' THEN 1 ELSE -1 END),0) AS withheld
        FROM  seniat_vat_ledger_line  
        WHERE ledger_id=%d
        GROUP BY vat_additional_rate
        ORDER BY vat_additional_rate
        """%(ledger_id)
        self._cr.execute(sql)
        results = self._cr.fetchall()
        if results:
            for res in results:
                if res[0]:
                    additional_taxes.append({'rate':res[0], 'base': res[1], 'tax':res[2], 'withheld':res[3]})
                    self.total_additional_base += res[1]
                    self.total_additional_tax += res[2]
                    self.total_amount += res[1]  + res[2]
                    self.total_amount_base += res[1]
                    self.total_amount_tax += res[2]
                    self.total_amount_withheld += res[3]
        else:
            additional_taxes.append({'rate':'', 'base': 0, 'tax':0, 'withheld':0})
        return additional_taxes

    @api.model
    def _get_report_values(self, docids, data=None):
        if not docids:
            raise UserError(_("You need select a data to print."))

        data = self.env['seniat.vat.ledger'].browse(docids)
        res = dict()
        return {
            'data': data,
            'lines': res,
            'get_exempt_amount': self._get_exempt_amount(data.id),
            'get_vat_reduced': self._get_vat_reduced(data.id),
            'get_vat_general': self._get_vat_general(data.id),
            'get_vat_additional': self._get_vat_additional(data.id),
            'get_total_reduced_base': self.total_reduced_base,
            'get_total_reduced_tax': self.total_reduced_tax,
            'get_total_general_base': self.total_general_base,
            'get_total_general_tax': self.total_general_tax,
            'get_total_additional_base': self.total_additional_base,
            'get_total_additional_tax': self.total_additional_tax,
            'get_total_amount': self.total_amount,
            'get_total_amount_base': self.total_amount_base,
            'get_total_amount_tax': self.total_amount_tax,
            'get_total_amount_withheld': self.total_amount_withheld,
        }

