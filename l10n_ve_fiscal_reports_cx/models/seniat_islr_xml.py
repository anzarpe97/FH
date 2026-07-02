###############################################################################
# Author: CIEXPRO SA 
# Copyleft: 2021-Present.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
import time
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import SubElement
from xml.etree.ElementTree import tostring
import base64
from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

ISLR_XML_WH_LINE_TYPES = [('invoice', 'Invoice'), ('employee', 'Employee')]

class SeniatIslrXml(models.Model):
    _name = 'seniat.islr.xml'
    _description = 'Generate ISLR XML'

    name = fields.Char(
        'Description',
        size=128,
        required=True,
        default=lambda self: 'Income Withholding ' + time.strftime('%m/%Y'),
        help='Description about statement of income withholding'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
        change_default=True,
        default=lambda self: self.env.company,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ],
        readonly=True,
        default='draft',
        copy=False,
        string="Status",
        track_visibility='onchange',
        index=True,
        help="* The 'Draft' state is used when a user is creating a new ISLR "
        "withholding statement."
        "\n* The 'Confirmed' state is used when a ISLR is valid."
        "\n* The 'Canceled' state is used when the ISLR is wrong."
    )
    date_from = fields.Date(
        string='Start Date',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    date_to = fields.Date(
        string='End Date',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    xml_line_ids = fields.One2many(
        'seniat.islr.xml.line',
        'xml_doc_id', 
        string='XML Items', 
        copy=False,
        readonly=True,
        states={
            'draft': [('readonly', False)],
            'confirmed': [('readonly', False)]
        }
    )
    # /!\ invoice_line_ids is just a subset of xml_line_ids.
    xml_invoice_line_ids = fields.One2many(
        'seniat.islr.xml.line',
        'xml_doc_id',
        string='XML Invoice lines',
        copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
        domain=[('type', '=', 'invoice')],
    )
    # /!\ invoice_line_ids is just a subset of xml_line_ids.
    xml_employee_line_ids = fields.One2many(
        'seniat.islr.xml.line',
        'xml_doc_id',
        string='XML Employee lines',
        copy=False,
        readonly=True,
        states={'confirmed': [('readonly', False)]},
        domain=[('type', '=', 'employee')],
    )
    xml_file_id = fields.Many2one(
        'ir.attachment',
        string="Xml file",
        copy=False,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )

    def action_to_draft(self):
        """ Passes the document to state draft
        """
        
        for xml_book in self:
            xml_book.mapped('xml_line_ids').unlink()
            xml_book.xml_file_id.unlink()
            xml_book.write({'state': 'draft'})
        return True

    def action_cancel(self):
        """ Passes the document to state cancel
        """
        
        for xml_book in self:
            xml_book.write({'state': 'cancel'})
        return True


    def action_done(self):
        """ Passes the document to state done
        """
        
        for xml_book in self:
            root = xml_book._xml()
            xml_book._write_attachment(root)
            xml_book.write({'state': 'done'})
        return True

    def _write_attachment(self, root):
        """ Codify the xml, to save it in the database and be able to
        see it in the client as an attachment
        @param root: data of the document in xml
        """
        fecha = time.strftime('%Y_%m_%d_%H%M%S')
        name = 'ISLR_' + fecha + '.' + 'xml'
        self.xml_file_id = self.env['ir.attachment'].create({
            'name': name,
            'res_id': self.id,
            'res_model': self._name,
            'datas': base64.encodebytes(root),
            'type': 'binary',
        })



    def _xml(self):
        """ Transform this document to XML format
        """
   
        root = ''
        period = self.date_to
        period2 = "%0004d%02d" % (period.year, period.month)
        partner = self.company_id.partner_id
        root = Element("RelacionRetencionesISLR")
        rif = "{}{}".format(
            partner.l10n_latam_identification_type_id.l10n_ve_code,
            partner.vat
        )
        root.attrib['RifAgente'] = rif
        root.attrib['Periodo'] = period2
        for line in self.xml_line_ids:
            detalle = SubElement(root, "DetalleRetencion")
            SubElement(detalle, "RifRetenido").text = line.partner_vat
            SubElement(detalle, "NumeroFactura").text = ''.join(
                i for i in line.invoice_number if i.isdigit())[-10:] or '0'
            SubElement(detalle, "NumeroControl").text = ''.join(
                i for i in line.control_number if i.isdigit())[-8:] or 'NA'
            #SubElement(detalle, "FechaOperacion").text = time.strftime('%d/%m/%Y', line.date)
            SubElement(detalle, "FechaOperacion").text = line.date.strftime('%d/%m/%Y')
            SubElement(detalle, "CodigoConcepto").text = line.concept_code
            SubElement(detalle, "MontoOperacion").text = str(round(line.move_id.amount_untaxed_bs, 2) )
            SubElement(detalle, "PorcentajeRetencion").text = str(
                line.porcent_rete)

        self.indent(root)
        return tostring(root, encoding="ISO-8859-1")


    def indent(self, elem, level=0):
        """ Return indented text
        @param level: number of spaces for indentation
        @param elem: text to indentig
        """
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def create_islr_xml_lines(self):
        self.ensure_one()
        domain = [
            ('move_type', 'in', ['in_invoice', 'in_refund']),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ['in_payment', 'paid']),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to)
        ]
        moves = self.env['account.move'].search(domain)
        if len(moves) != 0:
            for move in moves:
                #move._prepare_islr_xml_line_orm()
                xml_vals = move._prepare_islr_xml_line()
                if not xml_vals:
                    continue
                    
                xml_vals.update({'xml_doc_id': self.id})
                self.env['seniat.islr.xml.line'].create(xml_vals)


    def compute_xml_lines(self):
        for rec in self:
            rec.create_islr_xml_lines()


class SeniatIslrXmlLine(models.Model):
    _name = 'seniat.islr.xml.line'
    _description = 'ISLR XML line'

    xml_doc_id = fields.Many2one(
        'seniat.islr.xml', 
        string='Withholding Xml Document',
        required=True,
        help='Withholding document associated with this line'
    )
    concept_id = fields.Many2one(
        'seniat.tabla.islr', 
        string='Withholding Concept',
        required=True,
        track_visibility='onchange',
        help='Withholding concept associated with this rate'
    )
    partner_vat = fields.Char(
        string='VAT',
        size=10,
        required=True,
        help='Patner Vat'
    )
    invoice_number = fields.Char(
        string='Invoice Number',
        size=10,
        required=True,
        default=lambda self: '0',
        help='Number of invoice'
    )
    control_number = fields.Char(
        string='Control Number',
        size=10,
        required=True,
        default=lambda self: 'NA',
        help='Reference'
    )
    concept_code = fields.Char(
        string='Concept Code',
        size=3,
        required=True,
        help='Concept code'
    )
    porcent_rete = fields.Float(
        string='Withholding Rate',
        required=True,
        help='Withholding Rate'
    )
    wh = fields.Float(
        string='Withheld Amount',
        required=True,
        help='Withheld amount to partner'
    )
    base = fields.Float(
        string='Base Amount',
        required=True,
        help='Withholdable Base Amount'
    )
    move_id = fields.Many2one(
        'account.move',
        string='Bill',
        domain="[('move_type', 'in', ['in_invoice', 'in_refund']), ('state', '=', 'posted'), ('payment_state', 'in', ['in_payment', 'paid'])]",
        tracking=True,
        help='Withheld bill'
    )    
    move_line_id = fields.Many2one(
        string='Bill line',
        compute='_compute_move_line',
        store=True,
        copy=False,
        help='Withheld line bill'
    )
    type = fields.Selection(
        selection=ISLR_XML_WH_LINE_TYPES,
        string='XML ISLR type',
        required=True,
        default="invoice",
        help="Withheld ISLR type"
    )
    date = fields.Date(
        string='Date',
        required=True
    )

    @api.depends('move_id')
    def _compute_move_line(self):
        mov_line = False
        for xml_line in self:
            if xml_line.move_id.is_purchase_document():
                query = '''
                SELECT move.id, line.id AS line_src_id, rec_line.id AS rec_line_id,
                rec_line.payment_id, rec_line.journal_id, rec_line.date,
                move.ref, payment.amount, identification.l10n_ve_code, partner.vat,
                payment.comment_withholding, seniat.code_seniat,
                payment.withholding_base_amount,
                pay_group.regimen_islr_id
                FROM account_move move
                JOIN account_move_line line ON line.move_id = move.id
                JOIN account_partial_reconcile part ON part.debit_move_id = line.id OR part.credit_move_id = line.id
                JOIN account_move_line rec_line ON
                    (rec_line.id = part.debit_move_id AND line.id = part.credit_move_id)
                JOIN account_payment payment ON payment.id = rec_line.payment_id
                JOIN account_journal journal ON journal.id = rec_line.journal_id
                JOIN account_tax tax ON tax.id = payment.tax_withholding_id
                JOIN res_partner partner ON partner.id = move.partner_id
                JOIN l10n_latam_identification_type identification ON identification.id = partner.l10n_latam_identification_type_id
                JOIN account_payment_group pay_group ON pay_group.id = payment.payment_group_id
                JOIN seniat_tabla_islr seniat ON seniat.id = pay_group.regimen_islr_id
                WHERE move.id = %s
                AND tax.type_tax_use='supplier'
                AND tax.withholding_type='tabla_islr'
            UNION
                SELECT move.id, line.id AS line_src_id, rec_line.id AS rec_line_id,
                rec_line.payment_id, rec_line.journal_id, rec_line.date,
                move.ref, payment.amount, identification.l10n_ve_code, partner.vat,
                payment.comment_withholding, seniat.code_seniat,
                payment.withholding_base_amount,
                pay_group.regimen_islr_id
                FROM account_move move
                JOIN account_move_line line ON line.move_id = move.id
                JOIN account_partial_reconcile part ON part.debit_move_id = line.id OR part.credit_move_id = line.id
                JOIN account_move_line rec_line ON
                    (rec_line.id = part.credit_move_id AND line.id = part.debit_move_id)
                JOIN account_payment payment ON payment.id = rec_line.payment_id
                JOIN account_journal journal ON journal.id = rec_line.journal_id
                JOIN account_tax tax ON tax.id = payment.tax_withholding_id
                JOIN res_partner partner ON partner.id = move.partner_id
                JOIN l10n_latam_identification_type identification ON identification.id = partner.l10n_latam_identification_type_id
                JOIN account_payment_group pay_group ON pay_group.id = payment.payment_group_id
                JOIN seniat_tabla_islr seniat ON seniat.id = pay_group.regimen_islr_id
                WHERE move.id = %s
                AND tax.type_tax_use='customer'
                AND tax.withholding_type='tabla_islr'
            '''
                params = [xml_line.move_id.id, xml_line.move_id.id]
                self._cr.execute(query, params)
                res = self._cr.dictfetchone()
                if res:
                    xml_line.move_line_id = res['rec_line_id']


                inv_mov_lines = xml_line.move_id.mapped('line_ids')
                if xml_line.move_id.is_outbound():
                    partial_lines = inv_mov_lines.mapped('matched_debit_ids')
                    payment_mov_lines = partial_lines.mapped('debit_move_id')
                else:
                    partial_lines = inv_mov_lines.mapped('matched_credit_ids')
                    payment_mov_lines = partial_lines.mapped('credit_move_id')
    
                wh_payments = payment_mov_lines.mapped('payment_id').filtered(
                    lambda p: p.payment_method_id.code=='withholding'
                )
                islr_payment = wh_payments.filtered(
                    lambda x: x.tax_withholding_id.withholding_type=='tabla_islr'
                )
            else:
                xml_line.move_line_id = False



    @api.onchange('concept_id')
    def onchange_concept_id(self):
        # Ensures concept code is update
        if not self.concept_id:
            self.concept_code = False
        else:
            self.concept_code = self.concept_id.code_seniat
            rates = self.concept_id.mapped('banda_calculo_ids')
            if rates and len(rates) == 1:
                self.porcent_rete = rates.withholding_percentage
            if self.type == 'employee':
                self.date = self.xml_doc_id.date_from


        return {}