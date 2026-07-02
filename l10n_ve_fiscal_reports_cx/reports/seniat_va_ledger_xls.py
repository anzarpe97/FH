from odoo import models
import logging
import datetime
import pytz
from xlwt import *
from odoo.exceptions import UserError, ValidationError, Warning



class PartnerXlsx(models.AbstractModel):
    _name = 'report.10n_ve_fiscal_reports_cx.seniat_vat_ledger'
    _inherit = 'report.report_xlsx.abstract'
    _description ="Este Modulo Permite Generar el Libro de ventas en Xlsx."

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
    """
        I could have made an instance of this method the model l10n_ve_fiscal_reports_cx.template_purchase_ledger,
        but I decided to rebuild it in case this report has any 
        particular change in the logic in the future
    """

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

    """
        I could have made an instance of this method the model l10n_ve_fiscal_reports_cx.template_purchase_ledger,
        but I decided to rebuild it in case this report has any 
        particular change in the logic in the future
    """
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

    """
        I could have made an instance of this method the model l10n_ve_fiscal_reports_cx.template_purchase_ledger,
        but I decided to rebuild it in case this report has any 
        particular change in the logic in the future
    """
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
                    self.total_amount += res[1]  + res[2]
                    self.total_amount_base += res[1]
                    self.total_amount_tax += res[2]
                    self.total_amount_withheld += res[3]
        else:
            general_taxes.append({'rate':'', 'base': 0, 'tax':0, 'withheld':0})
        return general_taxes

    """
        I could have made an instance of this method the model l10n_ve_fiscal_reports_cx.template_purchase_ledger,
        but I decided to rebuild it in case this report has any 
        particular change in the logic in the future
    """

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

    """
        I could have made an instance of this method the model l10n_ve_fiscal_reports_cx.template_purchase_ledger,
        but I decided to rebuild it in case this report has any 
        particular change in the logic in the future
    """

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


    """
        The Get_forma methods what it does is set the values ​​according to a format of each numeric cell, 
        date or string.
    """
    def get_format_head(self,workbook):
        formato = workbook.add_format({'bold': True})
        formato.set_bg_color('gray')
        formato.set_align('center')
        return formato
        
    def get_format_linme(self,workbook):
        formato = workbook.add_format()
        formato.set_align('center')
        return formato
    def get_format_date(self,workbook):
        cell_format_date = workbook.add_format()
        cell_format_date.set_num_format('dd/mm/yyyy')
        #cell_format_date.set_align('center')
        return cell_format_date

    def get_format_totals(self,workbook):
        formato = workbook.add_format({'border':5})
        formato.set_num_format(4)
        return formato
    
    """
        This method allows to calculate all the totals in each column
    """
    def totals_printer(self,l,sale_book,sheet,workbook):
        totals = self._get_report_values(sale_book.id)
        format_totals = self.get_format_totals(workbook)


        sheet.write(l, 11, 'TOTALES',format_totals)
        sheet.write(l, 12,totals['get_total_amount'] ,format_totals)
        sheet.write(l, 13,totals['get_exempt_amount'],format_totals)
        sheet.write(l, 14, totals['get_total_amount_base'] ,format_totals)
        sheet.write(l, 15, '',)#sin definir
        sheet.write(l, 16, totals['get_total_amount_tax'],format_totals)
        sheet.write(l, 17,totals['get_total_amount_withheld'],format_totals)


        return l+1
    """
        This is the final box of contemplates some totals of the book.
    """
    
    def resumen_printer(self,l,sale_book,sheet,workbook):
        l += 4
        totals = self._get_report_values(sale_book.id)
        format_totals = self.get_format_totals(workbook)
        formato1 = workbook.add_format({'border':5})
 

        #head Resumen
        l += 1
        sheet.write(l, 0, "Resumen de Libro de Ventas", )
        l += 1
        sheet.write(l, 0, "Art. 72 Reglamento IVA", )

        l += 2
        
        sheet.write(l, 0, "RESUMEN", formato1)
        sheet.write(l, 1, "BASE IMPOBILE", formato1)
        sheet.write(l, 2, "DEBITO FISCAL", formato1)
        sheet.write(l, 3, "IVA RET POR EL COMPRADOR", formato1)
        l += 1
        sheet.write(l, 0, "Ventas Internas no Gravadas", formato1)
        sheet.write(l, 1, totals['get_exempt_amount'], self.get_format_totals(workbook))
        sheet.write(l, 2, "", self.get_format_totals(workbook))
        sheet.write(l, 3, "", self.get_format_totals(workbook))
        l += 1
        sheet.write(l, 0, "Ventas de Exportación", formato1)
        sheet.write(l, 1, "", self.get_format_totals(workbook))
        sheet.write(l, 2, "", self.get_format_totals(workbook))
        sheet.write(l, 3, "", self.get_format_totals(workbook))
        l += 1

        sheet.write(l, 0, "Total Ventas y Debitos Fiscales", self.get_format_totals(workbook))
        sheet.write(l, 1, totals['get_total_amount'], self.get_format_totals(workbook))
        sheet.write(l, 2, totals['get_total_amount_tax'], self.get_format_totals(workbook))
        sheet.write(l, 3, totals['get_total_amount_withheld'], self.get_format_totals(workbook))
        l += 1
        
        sheet.write(l, 0, "Ajuste a los Debitos Fiscales de períodos anteriores", formato1)
        sheet.write(l, 1,'' , self.get_format_totals(workbook))
        sheet.write(l, 2,'' , self.get_format_totals(workbook))
        sheet.write(l, 3,'' , self.get_format_totals(workbook))
        l += 1
        
        sheet.write(l, 0, "Total Ajustes a los Debitos Fiscales de Períodos Anteriores", formato1)
        sheet.write(l, 1, '', self.get_format_totals(workbook))
        sheet.write(l, 2,'' , self.get_format_totals(workbook))
        sheet.write(l, 3,'' , self.get_format_totals(workbook))
        l += 1 
        sheet.write(l, 0, "TOTAL DE DEBITOS FISCALES", formato1)
        sheet.write(l, 1, totals['get_total_amount'], self.get_format_totals(workbook))
        sheet.write(l, 2,totals['get_total_amount_tax'] , self.get_format_totals(workbook))
        sheet.write(l, 3,totals['get_total_amount_withheld'] , self.get_format_totals(workbook))

        return l+1
    """  
        Main method that generates the report.
        install xlwt and xlsxwriter
    """
    def generate_xlsx_report(self, workbook, data, sale_book):

        company = self.env['res.company']._company_default_get('account.move')
        headers = ['Nro','Fecha Doc.','N° RIF','Nombre O Razon Social','N° Plan Exp','N°Comprobante','N°Factura','N°Control','N°Nota Débito/Crédito','Tipo Doc.',
        'N°Factura Afectada','Total Ventas Con IVA','Ventas No Sujetas','Base Imponible','%Alic','Impuestos IVA','IVA Retenido','IVA Perc.Comp']
        format_head = self.get_format_head(workbook)
        format_line = self.get_format_linme(workbook)
        format_date = self.get_format_date(workbook)
        sheet = workbook.add_worksheet("Libro de Ventas")
        sheet.set_column('A:Z', 35)
   
        value = {}
        value['company_name'] = company.name
        if company.vat:
            value['company_vat'] = company.vat
        else:
            value['company_vat'] = "La compania no posee un RUC asociado"

        sheet.write(1, 0, "Empresa", format_line)
        sheet.write(1, 1, value['company_name'],format_line)
        sheet.write(2, 0, "RIF:", format_line)
        sheet.write(2, 1, value['company_vat'],format_line)
        sheet.write(3, 0, "", format_line)
        sheet.write(4, 0, "Nombre del reporte", format_line)
        sheet.write(4, 1, "Libro De Ventas", format_line)
        sheet.write(5, 0, "Fecha Inicial", format_line)
        sheet.write(5, 1, sale_book.date_start,format_date)
        sheet.write(5, 2, "Fecha Final", format_line)
        sheet.write(5, 3, sale_book.date_end,format_date)

        
        for i in range(0,len(headers)):
            sheet.write(10, i, headers[i], format_head)  
        indice = 1
        l = 11 
        sale_book_line_ids = self.env['seniat.vat.ledger.line'].search([('ledger_id','=',sale_book.id)])
        for line in sale_book_line_ids:
            sheet.write(l, 0,indice,)
            sheet.write(l, 1, line.invoice_date,format_date)
            sheet.write(l, 2, line.partner_vat,)
            sheet.write(l, 3, line.partner_name,)
            sheet.write(l, 4, '',)#sin definir
            sheet.write(l, 5, line.withholding_number,)
            sheet.write(l, 6, line.invoice_number,)
            sheet.write(l, 7, line.document_number,)
            sheet.write(l, 8, line.credit_note_number,)
            sheet.write(l, 9, line.doc_type,)
            sheet.write(l, 10, line.affected_invoice,)
            sheet.write(l, 11, '{:,.2f}'.format(line.total_amount).replace(',', '@').replace('.', ',').replace('@', '.'),)
            sheet.write(l, 12, '{:,.2f}'.format(line.total_amount).replace(',', '@').replace('.', ',').replace('@', '.'),)
            if line.vat_reduced_base:
                sheet.write(l, 13, '{:,.2f}'.format(line.vat_reduced_base).replace(',', '@').replace('.', ',').replace('@', '.'),)
            elif line.vat_general_base:
                sheet.write(l, 13, '{:,.2f}'.format(line.vat_general_base).replace(',', '@').replace('.', ',').replace('@', '.'),)
                
            elif line.vat_additional_base:
                sheet.write(l, 13, '{:,.2f}'.format(line.vat_additional_base).replace(',', '@').replace('.', ',').replace('@', '.'),)
            
            if line.vat_reduced_rate:
                sheet.write(l, 14,line.vat_reduced_rate,)
            elif line.vat_general_rate:
                sheet.write(l, 14,line.vat_general_rate,)
            elif line.vat_additional_rate:
                sheet.write(l, 14,line.vat_additional_rate,)
            
            sheet.write(l, 15, '{:,.2f}'.format(line.tax_withheld_amount).replace(',', '@').replace('.', ',').replace('@', '.'),)
            
            l += 1
            indice += 1

        l = self.totals_printer(l,sale_book,sheet,workbook)

        self.resumen_printer(l,sale_book,sheet,workbook)


