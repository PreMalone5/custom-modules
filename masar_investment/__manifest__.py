{
    'name': 'Masar Investors',
    'summary': '',
    'author': 'Irtiqadx',
    'category': 'Investment',
    'description': "",
    'depends': ['base','project','account','custom_project',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/base_menu.xml',
        'views/property_view.xml',
        'views/wallet.xml',
        # 'reports/wallet_report.xml',
        # 'static/description/icon.png'
    ],
    'application': True,
}
