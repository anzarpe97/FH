# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
import logging
import json
_logger = logging.getLogger(__name__)
try:
    from lxml import etree
except:
    _logger.warning("no se ha cargado lxml !!!")

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def update_json_data(self, json_data=False, update_data={}):
        ''' It updates JSON data. It gets JSON data, converts it to a Python
        dictionary, updates this, and converts the dictionary to JSON data
        again. '''
        dict_data = json.loads(json_data) if json_data else {}
        dict_data.update(update_data)
        return json.dumps(dict_data, ensure_ascii=False)

    def set_modifiers(self, element=False, modifiers_upd={}):
        ''' It updates the JSON modifiers with the specified data to indicate
        if a XML tag is readonly or invisible or not. '''
        if element is not False:  # Do not write only if element:
            modifiers = element.get('modifiers') or {}
            modifiers_json = self.update_json_data(
                modifiers, modifiers_upd)
            element.set('modifiers', modifiers_json)
    """
    Show only the fields that belong to the Venezuelan location in the partner view.
    """
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ResPartner, self).fields_view_get(view_id=view_id,view_type=view_type,toolbar=toolbar,submenu=submenu)
        if view_type in ['form','kanban']:
            company_obj  = self.env['res.company'].browse(self.env.context['allowed_company_ids'])
            document = etree.XML(res['arch'])
            if company_obj.country_id.code != 'VE': 
                fields =[
                        document.xpath("//field[@name='l10n_ve_responsibility_type_id']"),
                        document.xpath("//field[@name='vat_retention']"),
                        document.xpath("//field[@name='seniat_partner_type_id']"),

                    ]
                for field in fields:
                    if field:
                        self.set_modifiers(field[0], {'invisible': True, })
                
           
            res['arch'] = etree.tostring(document,encoding='unicode')
        return res
