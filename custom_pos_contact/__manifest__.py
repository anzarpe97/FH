# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

{
    'name': 'POS Custom contact',
    'category': 'Sales/Point of Sale',
    'summary': 'This module is used to customized contact of point of sale when a user adds a product in the cart and validates payment and print contact, then the user can see the client name on POS contact. | Custom contact | POS Reciept | Payment | POS Custom contact',
    'description': "Customized our point of sale contact",
    'version': '16.0.1.0',
    'website': 'https://www.kanakinfosystems.com',
    'author': 'Kanak Infosystems LLP.',
    'depends': ['base', 'point_of_sale'],
    'assets': {
        'point_of_sale.assets': [
            "custom_pos_contact/static/src/xml/pos.xml",
        ],
    },
    'installable': True,
}
