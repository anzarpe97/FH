{
    'name': '[Original] POS Manager Validation using Employee PIN',
    'version': '16.0.1.0',
    'summary': """Validation of Closing POS, Order Deletion, Order Line Deletion,
                  Discount Application, Order Payment, Price Change and Decreasing Quantity,
Odoo POS validation, Odoo POS validate, Odoo POS confirmation, Odoo POS confirm,
Odoo POS checking, Odoo POS check, Odoo POS access, Odoo POS employee, employee access,
access right, delete order, delete order line, POS closing, closing POS, decrease quantity,
Odoo POS employee validation, Odoo POS restaurant validation""",
    'description': """
POS Manager Validation using Employee PIN
=========================================

This module allows validation for certain features on POS UI
if the cashier has no access rights or not a manager

Per Point of Sale, you can define manager validation for the following features:
* POS Closing
* Order Deletion
* Order Line Deletion
* Discount Application
* Order Payment
* Price Change
* Decresing Quantity


Compatibility
-------------

This module is compatible and tested with these modules:
* Restaurant module (pos_restaurant)
""",
    'category': 'Sales/Point of Sale',
    'author': 'MAC5',
    'contributors': ['MAC5'],
    'website': 'https://apps.odoo.com/apps/modules/browse?author=MAC5',
    'depends': [
        'pos_hr',
    ],
    'data': [
        'views/pos_config_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_hr_manager_validation_mac5/static/src/js/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.gif'],
    'price': 79.99,
    'currency': 'EUR',
    'support': 'mac5_odoo@outlook.com',
    'license': 'OPL-1',
    'live_test_url': 'https://youtu.be/eP0okikaBk4',
}
