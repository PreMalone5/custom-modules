{
    'name': 'Custom Project Fields',
    'summary': '',
    'author': 'Irtiqadx',
    'version': '1.0',
    'depends': ['project','account'],
    'data': [
        'security/ir.model.access.csv',  # Security rules
        'views/project_project_view.xml',       # XML views
        'views/cus_project.xml',
        'views/cus_kanban.xml',
        'views/cus_form.xml',
        'reports/proj_report.xml',
    ],
}