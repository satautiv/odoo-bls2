{
    "name" : "Sandas Maintenance",
    "version" : "1.0",
    "author" : "Sandas",
    "website" : "www.sandas.eu",
    "category" : "Sandas",
    "depends" : ["base"],
    "data" : [
        'security/group_data.xml',
        'menu_view.xml',
        "ir_cron_view.xml",

        "maintenance_view.xml",
        "maintenance_data.xml",
        "wizard/update_store_fields_view.xml",
        "module_view.xml",

        "security/ir.model.access.csv"
    ],
    'demo': [],
    'test': [],
    'images' : [],
    "description": """
Sandas Maintenance module. Automates migration of databases.
    """,
    "license": "Other proprietary",
    "installable" : True,
    "auto_install" : False,
}