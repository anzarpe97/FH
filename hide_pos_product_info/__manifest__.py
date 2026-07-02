# -*- coding: utf-8 -*-

{
    'name': 'POS Hide Product Info ',
    'version': '16.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'author': 'Aya Sharaf Elden',
    'license': 'AGPL-3',
    'summary': 'Hide POS product info',
    'depends': ['point_of_sale'],
    'website': 'https://www.linkedin.com/in/aya-sharaf-elden-23871190/',
    'data': [
        'views/res_config_settings_view.xml'
    ],
    'installable': True,
    'application': True,
    "assets": {
        "point_of_sale.assets": [
            "hide_pos_product_info/static/src/xml/Screens/ProductScreen/ControlButtons/ProductInfoButton.xml",
        ],
    },
    'images': [
        'static/description/before_config.png',
    ]
}
