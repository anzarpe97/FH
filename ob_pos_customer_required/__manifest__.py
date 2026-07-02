# -*- coding: utf-8 -*-

{
    'name': 'PoS Customer Required',
    'author': 'Odoo Bin',
    'company': 'Odoo Bin',
    'maintainer': 'Odoo Bin',
    'description': """ PoS Customer Required, customer Required, client Required pos, pos client Required,
    customer Required, point of sale customer, pos customer""",
    'summary': """This module allow you to require customer for pos orders
""",
    'version': '16.0',
    'license': 'OPL-1',
    'depends': ['point_of_sale'],
    'category': 'Point of Sale',
    'demo': [],
    'data': [
        'views/pos_config_view.xml',
    ],
    'assets': {
            'point_of_sale.assets': [
                'ob_pos_customer_required/static/src/js/payment_screen.js',
            ],
    },
    'live_test_url': 'https://youtu.be/LVFXPhGDsx0',
    'images': ['static/description/banner.png'],
    "price": 6,
    "currency": 'USD',
    'installable': True,
    'application': True,
    'auto_install': False,
}
