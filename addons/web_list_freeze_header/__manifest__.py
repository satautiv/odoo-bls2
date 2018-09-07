# -*- coding: utf-8 -*-
{
    'name': 'Odoo List View Freeze Header',
    'summary': 'Freeze/Stick the backend list view table column headers to the top of the viewport as you scroll down.',
    'description': """
        Avoid your users getting lost in a long list of data as they scroll down on the page.
        """,
    'author': "MAXSNS/Sandas",
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
}
