# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

{
    'name': 'Config BLS Stock',
    'version': '1.0',
    'category': 'Stock',
    'sequence': 14,
    'summary': 'Config BLS Stock',
    'description': """""",
    'author': 'Sandas',
    'images': [],
    'depends': ['config_sanitex_delivery'],
    'data': [
        'views/base.xml',
        'transportation_view.xml',
        'invoice_view.xml',
        'product_data.xml',
        'company_view.xml',
        'product_view.xml',
        'stock_data.xml',
        'partner_data.xml',
        'sale_view.xml',
        'stock_view.xml',
        'wizard/do_invoice_result_view.xml',
        'wizard/send_print_document_view.xml',
        'wizard/get_ubl_zip_view.xml',
        'invoice_report.xml',
        'sequence_data.xml',
        'security/ir.model.access.csv',
        'wizard/stock_route_create_cmr_view.xml',
        'document_data.xml',
    ],
    'demo': [],
    'test': [],
    'qweb': [
        'static/src/xml/base.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}