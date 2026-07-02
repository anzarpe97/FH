# -*- coding: utf-8 -*-

{
    'name': 'Venezuela Fiscal Reports',
    'author': "Jesús Pozzo",
    'website': "",
    'version' : '1.0',
    'sequence': 1,
    'category' : 'Localization',
    'description' : """
    This module adds the tax reports required by Venezuelan laws

    """,

    'depends': [
        'account',
        'report_xlsx',
        'l10n_ve_withholding'
    ],
    'data': [
        'security/fiscal_reports_security.xml',
        'security/ir.model.access.csv',
        'reports/seniat_vat_ledger_xls.xml',
        'reports/seniat_purchase_ledger_xls.py.xml',
        'reports/seniat_purchase_ledger_report.xml',
        'reports/seniat_sale_ledger_report.xml',
        'views/account_tax_view.xml',
        'views/seniat_vat_ledger_view.xml',
        'views/seniat_iva_txt_view.xml',
        'views/seniat_islr_xml_view.xml',
    ],
    'installable': True,
}

