# -*- coding: utf-8 -*-
# Copyright (C) 2018 MAXSNS Corp (http://www.maxsns.com)
# @author Henry Zhou (zhouhenry@live.com)
# License OPL-1 - See https://www.odoo.com/documentation/user/11.0/legal/licenses/licenses.html
{
    'name': 'Web Frozen List View Header',
    'summary': 'Freeze/Stick the backend list view table column headers to the top of the viewport as you scroll down.',
    'description': """
        Avoid your users getting lost in a long list of data as they scroll down on the page.
        """,
    'author': "MAXSNS",
    'website': "http://www.maxsns.com",
    'category': 'Web',
    'version': '1.0.0',
    'images': ['static/description/banner.png'],
    'depends': ['web'],
    'data': [
        'views/assets.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,

    'license': 'OPL-1',
    'price': 19.00,
    'currency': 'EUR',
}
