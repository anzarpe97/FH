###############################################################################
# 
# Copyleft: 2023-Present.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
{
    'name': "Localización Vat Ledger Venezuela",
    'description': """
        **Localización VENEZUELA Withholding**

        Fix Custom Ticket Fiscal by Andrés Castillo
    """,

    'author': "Jesús Pozzo - Fix Custom Ticket Fiscal by Andrés Castillo",
    'website': "",
    'version': '16.0.8',
    'category': 'Localization',
    'license': 'AGPL-3',
    'depends': [
        'account', 
        'l10n_ve_base',
        'l10n_ve_withholding', 
        'report_xlsx', 
        'l10n_ve_igtf_purchase',
        '10n_ve_dual_currency_bs'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/account_vat_ledger_views.xml',
        'wizard/account_wizard_views.xml',
        'report/account_vat_ledger_report.xml',
    ],

}
