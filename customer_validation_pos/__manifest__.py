# -*- coding: utf-8 -*-
{
    'name': 'Customer Validation Pos',
    'version': '1.1.0',
    'author': 'Preway IT Solutions',
    'category': 'Point of Sale',
    'depends': ['point_of_sale'],
    'summary': 'This apps helps you add validation on customer in pos interface | pos required customer fields | POS Customer phone required | POS Customer Email Required | POS Customer Barcode Required | POS Validation',
    'description': """
- Odoo POS Customer phone unique
- Odoo POS Customer phone require
- Odoo POS Customer email unique
- Odoo POS Customer email require
- Odoo POS Customer barcode unique
- Odoo POS Customer barcode require
    """,
    'data': [
        "views/pos_config_view.xml",
    ],
    'assets': {
        'point_of_sale.assets': [
            'customer_validation_pos/static/src/js/**/*',
        ],
    },
    'price': 15.0,
    'currency': "EUR",
    'application': True,
    'installable': True,
    "license": "LGPL-3",
    "images":["static/description/Banner.png"],
}

