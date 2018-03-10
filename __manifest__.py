# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Expense Approval Online',
    'version': '2.0',
    'category': 'Human Resources',
    'sequence': 95,
    'summary': 'Expense Book and Approval Online',
    'description': 'Topica- Expense Book and Approval Online',
    'author':'Hapi Solutions',
    'website': 'http://erp.hapi.solutions',
    'depends': ['base','hr'],
    'data': [
        'views/hr_expense_approval_views.xml',
        'views/hr_expense_approval_payment_views.xml',
        'views/setting_views.xml',
        'views/menu_item.xml',
        'views/quotation_workflow.xml'
    ],
    #’demo': ['data/hr_expense_demo.xml'],
    'installable': True,
    'application': True,
}
