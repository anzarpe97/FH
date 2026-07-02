from odoo import fields, models


class POSConfig(models.Model):
    _inherit = 'pos.config'

    manager_employee_ids = fields.Many2many('hr.employee', 'pos_config_manager_employee_rel',
                                            'pos_config_id', 'employee_id', string='Managers (Employee)')
    iface_employee_validate_close = fields.Boolean(string='Enable Validation for Closing POS (Employee)',
                                                   help=('Enabling this will allow manager to'
                                                         ' validate if POS needs to be closed'))
    iface_employee_validate_decrease_quantity = fields.Boolean(string='Enable Validation for Decreasing Quantity (Employee)',
                                                               help=('Enabling this will allow manager to validate'
                                                                     ' the order if need to decrease the quantity'))
    iface_employee_validate_delete_order = fields.Boolean(string='Enable Validation for Order Deletion (Employee)',
                                                          help=('Enabling this will allow manager to '
                                                                'validate the order if needs to be deleted'))
    iface_employee_validate_delete_orderline = fields.Boolean(string='Enable Validation for Order Line Deletion (Employee)',
                                                              help=('Enabling this will allow manager to validate'
                                                                    ' the order if need to delete an order line'))
    iface_employee_validate_discount = fields.Boolean(string='Enable Validation for Discount (Employee)',
                                                      help=('Enabling this will allow manager to validate'
                                                            ' the order if discount is applicable'))
    iface_employee_validate_payment = fields.Boolean(string='Enable Validation for Payment (Employee)',
                                                     help=('Enabling this will allow manager to '
                                                           'validate the order if needs to be paid'))
    iface_employee_validate_price = fields.Boolean(string='Enable Validation for Price Change (Employee)',
                                                   help=('Enabling this will allow manager to validate '
                                                         'the order if changing the price is applicable'))
