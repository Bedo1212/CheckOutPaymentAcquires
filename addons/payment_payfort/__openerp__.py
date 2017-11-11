# -*- coding: utf-8 -*-

{
    'name': 'Payfort Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Payment Acquirer: PayFort',
    'version': '1.0',
    'description': """PayFort Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/payfort.xml',
        'views/payment_acquirer.xml',
        'data/payfort.xml',
        'views/payment_payfort_template.xml',
    ],
    'installable': True,
}
