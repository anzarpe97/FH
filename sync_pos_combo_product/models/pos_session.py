
from odoo import models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        result.append('product.combo')
        return result

    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        result['search_params']['fields'].append('is_combo')
        return result

    def _loader_params_product_combo(self):
        return {
            'search_params': {
                'fields': ['product_template_id', 'is_required_product', 'is_include_in_main_product_price', 'category_id', 'product_ids', 'no_of_items'],
                'order': 'id',
            },
        }

    def _get_pos_ui_product_combo(self, params):
        return self.env['product.combo'].search_read(**params['search_params'])

