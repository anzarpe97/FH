# -*- coding: utf-8 -*-
{
    'name': "SW - Sale Order Privileged Confirm & Unlock",
    'summary': "Limited Access on SO Confirmation and Unlocking.",
    'description': "Decide and limit the access of confirming & unlocking sale orders.",
    'author': "Smart Way Business Solutions",
    'website': "https://www.smartway.co",
    'category': 'Accounting',
    'version': '1.0',
    'depends': ['base', 'sale'],
    'data': [
        'security/groups.xml',
        'views/sale_order.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': "Other proprietary",
    'images': ["static/description/image.png"],
}
