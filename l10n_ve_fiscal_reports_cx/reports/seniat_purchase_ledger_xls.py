from odoo import models
import logging
import datetime
import pytz
from xlwt import *
from odoo.exceptions import UserError, ValidationError, Warning






class PartnerXlsx(models.AbstractModel):
    _name = 'report.10n_ve_fiscal_reports_cx.seniat_vat_ledger_purchase'
    _inherit = 'report.report_xlsx.abstract'
    _description ="Este Modulo Permite Generar el Libro de compras en Xlsx."
    
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

    def get_format_numeric(self,workbook):
        formato = workbook.add_format()
        formato.set_num_format(4)
        return formato
    def get_format_totals(self,workbook):
        formato = workbook.add_format({'border':5})
        formato.set_num_format(4)
        return formato
        
    """
        This method allows to calculate all the totals in each column
    """
    def totals_printer(self,l,purchase_book,sheet,workbook):
        totals = self.env['report.l10n_ve_fiscal_reports_cx.template_purchase_ledger'].sudo()._get_report_values(purchase_book.id)
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
    
    def resumen_printer(self,l,purchase_book,sheet,workbook):
        l += 4
        totals = self.env['report.l10n_ve_fiscal_reports_cx.template_purchase_ledger'].sudo()._get_report_values(purchase_book.id)
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

    def generate_xlsx_report(self, workbook, data, purchase_book):   
        logging.info("is Purchase") 
        
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
        

        
        company = self.env['res.company']._company_default_get('account.move')
        headers = ['Nro','Fecha Doc.','Nombre O Razon Social','Tipo Prov.',' N° Comprobante','N° Plan. Imp.','N° Exp. Imp.'
                ,'Tipo Doc.','N° Factura','N° Nota Debito','N° Nota Credito','Factura Afectada','N° Control','Total Compra incluye iva',
                'Compra sin Derecho Credito iva','Base Imponible',' % Alic','Impuesto iva','IVA Retenido','IVA Ret. Terc.','Anti. IVA Imp.'
        ]
        format_head = self.get_format_head(workbook)
        format_line = self.get_format_linme(workbook)
        format_date = self.get_format_date(workbook)
        sheet = workbook.add_worksheet("Libro de Compras")
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
        sheet.write(4, 1, "Libro De Compras", format_line)
        sheet.write(5, 0, "Fecha Inicial", format_line)
        sheet.write(5, 1, purchase_book.date_start,format_date)
        sheet.write(5, 2, "Fecha Final", format_line)
        sheet.write(5, 3, purchase_book.date_end,format_date)

  
        for i in range(0,len(headers)):
            sheet.write(10, i, headers[i], format_head)  
        indice = 1
        
        purchase_book_line_ids = self.env['seniat.vat.ledger.line'].search([('ledger_id','=',purchase_book.id)])
        indice = 1
        line = 11 
        for l in purchase_book_line_ids:
            sheet.write(line, 0,indice,)
            sheet.write(line, 1,l.invoice_date,format_date)
            sheet.write(line, 2,l.partner_name,)
            sheet.write(line, 3,l.withholding_number,)
            sheet.write(line, 4,'',)
            sheet.write(line, 5,'',)
            sheet.write(line, 6,l.invoice_number,)
            sheet.write(line, 7,l.debit_note_number,)
            sheet.write(line, 8,l.credit_note_number,)
            sheet.write(line, 9,l.affected_invoice if l.affected_invoice else '',)
            sheet.write(line, 10,l.document_number,)
            sheet.write(line, 11,l.total_amount,self.get_format_numeric(workbook))
            sheet.write(line, 12,l.exempt_amount,self.get_format_numeric(workbook))
            if l.vat_reduced_base:
                sheet.write(line, 13,l.vat_reduced_base,self.get_format_numeric(workbook))
            elif l.vat_general_base:
                sheet.write(line, 13,l.vat_general_base,self.get_format_numeric(workbook))
            elif l.vat_additional_base:
                sheet.write(line, 13,l.vat_additional_base,self.get_format_numeric(workbook))


            if l.vat_reduced_rate:
                sheet.write(line, 14,l.vat_reduced_rate,self.get_format_numeric(workbook))
            elif l.vat_general_rate:
                sheet.write(line, 14,l.vat_general_rate,self.get_format_numeric(workbook))
            elif l.vat_additional_rate:
                sheet.write(line, 14,l.vat_additional_rate,self.get_format_numeric(workbook))

            if l.vat_reduced_tax:
                sheet.write(line, 15,l.vat_reduced_tax,self.get_format_numeric(workbook))
            elif l.vat_general_tax:
                sheet.write(line, 15,l.vat_general_tax,self.get_format_numeric(workbook))
            elif l.vat_additional_tax:
                sheet.write(line, 15,l.vat_additional_tax,self.get_format_numeric(workbook))
            
            sheet.write(line, 16,l.tax_withheld_amount,self.get_format_numeric(workbook))
            sheet.write(line, 17,"",self.get_format_numeric(workbook))
            sheet.write(line, 18,"",self.get_format_numeric(workbook))


            line += 1
            indice += 1
        line = self.totals_printer(line,purchase_book,sheet,workbook)
        self.resumen_printer(line,purchase_book,sheet,workbook)