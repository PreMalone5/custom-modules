{
    'name': 'Test App',
    'summary': 'TEST',
    'author': 'Seif Hazem',
    'category': 'TEST',
    'description': "",
    'depends': ['base','project','account','custom_project',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/base_menu.xml',
        'views/property_view.xml',
        # 'reports/wallet_report.xml',
    ],
    'application': True,
}
