from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    manager_employee_ids = fields.Many2many(related="pos_config_id.manager_employee_ids", readonly=False)
    iface_employee_validate_close = fields.Boolean(related="pos_config_id.iface_employee_validate_close", readonly=False)
    iface_employee_validate_decrease_quantity = fields.Boolean(related="pos_config_id.iface_employee_validate_decrease_quantity", readonly=False)
    iface_employee_validate_delete_order = fields.Boolean(related="pos_config_id.iface_employee_validate_delete_order", readonly=False)
    iface_employee_validate_delete_orderline = fields.Boolean(related="pos_config_id.iface_employee_validate_delete_orderline", readonly=False)
    iface_employee_validate_discount = fields.Boolean(related="pos_config_id.iface_employee_validate_discount", readonly=False)
    iface_employee_validate_payment = fields.Boolean(related="pos_config_id.iface_employee_validate_payment", readonly=False)
    iface_employee_validate_price = fields.Boolean(related="pos_config_id.iface_employee_validate_price", readonly=False)
