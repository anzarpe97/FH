from odoo import api, fields, models, _


class PosSession(models.Model):
	_inherit = 'pos.session'

	def _loader_params_product_product(self):
		result = super()._loader_params_product_product()
		result['search_params']['fields'].extend(['qty_available','type'])
		return result
