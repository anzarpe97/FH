###############################################################################
# Author: Jesus Pozzo
# Copyleft: 2023-Present.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################

import xlwt  # libreria para xlxs
import xlsxwriter
import base64
import calendar
from io import StringIO
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime

import logging


_logger = logging.getLogger(__name__)


style_number = xlwt.XFStyle()
style_number.num_format_str = '$#,##0.000'

style_number2 = xlwt.XFStyle()
style_number2.num_format_str = '_ Bs.S#,##0.000'


class AccountReportCXC(models.TransientModel):
    _name = 'account.invoice.report.cxc'
    _description = 'Resporte de Cuentas por cobrar'

    start_date = fields.Date(
        string='Fecha Inicio', required=True, default=datetime.today().replace(day=1))

    end_date = fields.Date(string="Fecha Fin", required=True, default=datetime.now().replace(
        day=calendar.monthrange(datetime.now().year, datetime.now().month)[1]))

    invoice_data = fields.Char(string='Name')

    file_name = fields.Binary('Descargar', readonly=True)

    state = fields.Selection(
        [('choose', 'choose'), ('get', 'get')], default='choose')
    consolidado = fields.Boolean(default=False, string="Consolidado?")

    
    """
        ACA en este reporte estan todas la Facturas y Notas de debitos a clientes.
    """
    def action_invoices_report(self):
        
        current_company_id = self.env.company
        query = """
        SELECT 
            m.id, 
            m.name, 
            m.date, 
            m.amount_total, 
            m.amount_residual, 
            m.debit_origin_id, 
            m.amount_residual_bs, 
            m.tax_day, 
            m.amount_total_bs, 
            m.partner_id,
            p.name as partner_name,
            p.vat as partner_vat
        FROM 
            account_move m
        JOIN res_partner p ON m.partner_id = p.id
        WHERE 
            m.move_type = 'out_invoice' 
            AND m.amount_residual != 0
            AND m.date BETWEEN %s AND %s
            AND m.state = 'posted'
            AND m.company_id = %s;
        """
        self.env.cr.execute(query, (self.start_date, self.end_date,current_company_id.id))
        result = self.env.cr.dictfetchall()
        
        if result:
            _logger.info(result)
            file = StringIO()
            workbook = xlwt.Workbook()
            sheet = workbook.add_sheet("CUENTAS POR COBRAR")
            format1 = xlwt.easyxf('font:bold True ;align: horiz center')
            
            format4 = xlwt.easyxf(
                'align: horiz left;borders:right medium , left medium')
            format3 = xlwt.easyxf('font:bold True;pattern: pattern solid, fore_colour gray25;'
                                'align: horiz center; borders:bottom medium , top thick , left medium , right medium')
            format8 = xlwt.easyxf('font:bold True;pattern: pattern solid, fore_colour gray25;'
                                'align: horiz center;borders:top medium')
            format9 = xlwt.easyxf('font:bold True;pattern: pattern solid, fore_colour gray25;'
                                'align: horiz center;borders:top medium , left medium')
            format10 = xlwt.easyxf('font:bold True;pattern: pattern solid, fore_colour gray25;'
                                'align: horiz center;borders:top medium , right medium')
            format11 = xlwt.easyxf('font:bold True;pattern: pattern solid, fore_colour gray25;'
                                'align: horiz center;borders:top medium , right medium , bottom medium')

            sheet.write(1, 0, "Empresa", format1)
            sheet.write(1, 1, current_company_id.name)
            sheet.write(2, 0, "R.I.F.:", format1)
            if current_company_id.vat:
                sheet.write(2, 1,current_company_id.vat)
            else:
                sheet.write(2, 1, "No posee RIF asociado")
            sheet.write(3, 0, ".:", format1)
            sheet.write(8, 2, "CUENTAS POR COBRAR", format1)
            sheet.write(5, 0, "DESDE")

            sheet.write(5, 1, self.start_date.strftime('%d/%m/%Y'))
            sheet.write(5, 2, "HASTA")
            sheet.write(5, 3, self.end_date.strftime('%d/%m/%Y'))
            i = 0
            while i <= 40:
                sheet.col(i).width = int(30 * 250)
                i = 1 + i
            filename = (
                '/tmp/cuentas_por_cobrar.xls' )
            

            sheet.write(10, 0, "Fecha", format3)
            sheet.write(10, 1, "RIF", format3)
            sheet.write(10, 2, "Nombre o Razon Social", format3)
            sheet.write(10, 3, "N° de Documento", format3)
            sheet.write(10, 4, "Tipo de Documento", format3)
            sheet.write(10, 5, "Monto Total $", format3)
            # sheet.write(10, 5, "Monto Total Bs.", format3)
            sheet.write(10, 6, "Deuda $", format3)
            # sheet.write(10, 7, "Deuda Bs.", format3)
            
            i = 11
            for inv in result:
                sheet.write(i, 0, inv.get('date').strftime('%d/%m/%Y'))
                sheet.write(i, 1, inv.get('partner_vat')) 
                sheet.write(i, 2, inv.get('partner_name').upper())
                sheet.write(i, 3, inv.get('name').upper())
                sheet.write(i, 4, "NOTA DE DEBITO" if inv.get('debit_origin_id')  else "FACTURA")
                sheet.write(i, 5,inv.get('amount_total') ,style_number)
                # sheet.write(i, 5,inv.get('amount_total_bs') ,style_number2)
                sheet.write(i, 6,inv.get('amount_residual') ,style_number)
                # sheet.write(i, 7,inv.get('amount_residual_bs') ,style_number2)
                i += 1

        
            
            workbook.save(filename)
            file = open(filename, "rb")
            file_data = file.read()
            out = base64.encodebytes(file_data)
            self.write(
                {
                    'state': 'get', 
                    'file_name': out,
                    'invoice_data': 'cuentas_por_cobrar.xls'}
                )
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.invoice.report.cxc',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'target': 'new',
            }
        else:
            raise ValidationError(
                "No hay facturas,ND,NC y retenciones para el rango de fecha especificado")


