# Copyright (C) Softhealer Technologies.
# Part of Softhealer Technologies.
# -*- coding: utf-8 -*-

{
    "name": "POS Product Variants Popup | Point Of Sale Product Variants Popup | Point Of Sale Alternative Product Popup",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Point Of Sale",
    "license": "OPL-1",
    "summary": "POS Product Multi variant Select Product Multiple variants POS Product Variants Point OF Sale Multi Variants POS Relevent Product Popup Product variant pop-up point of sales product template pos product attributes multiple product variants Odoo",
    "description": """This module helps POS users to choose product variants from the pop-up on the POS screen. Sometimes POS user is not aware of which product template contains which product variant. So our module displays the product template on the POS screen, when you click on the template it shows relevant variants. If you don't have variants then it direct add product to the cart. We provide alternative product suggestions from the pop-up window so when the pop-up opens, it shows all variants & relevant products of the product. You can also close the pop-up after selecting the single variant using the auto close pop-up feature.""",
    "version": "16.0.5",
    'depends': ['point_of_sale'],
    "data": [
        'views/res_config_settings.xml',
        'views/product_template.xml',
    ],
    'assets': {'point_of_sale.assets': [
                                        'sh_pos_product_variant/static/src/scss/pos.scss',
                                        'sh_pos_product_variant/static/src/js/**/*',
                                        'sh_pos_product_variant/static/src/xml/**/*',
                                        ],
               },
    'images': ['static/description/background.png', ],
    'installable': True,
    "price": 25,
    "currency": "EUR"
}
