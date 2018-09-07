# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import fields, models, api, _
from odoo import tools
from odoo import release
from odoo.api import Environment
from odoo.exceptions import UserError


import os
import sys
import xmlrpc
import base64
import time
import datetime
import subprocess
import threading
import logging

_logger = logging.getLogger(__name__)

class form_checker(object):
    """A generic form widget
    """

    template = "/openerp/widgets/form/templates/form.mako"

    params = ['id']
    member_widgets = ['frame', 'concurrency_info']

    def __init__(self, view):
        import xml.dom.minidom

        dom = xml.dom.minidom.parseString(
            tools.ustr(view['arch']).encode('utf-8')
        )
        fields = view['fields']

        values = {}
        self.view_fields = []
        self.nb_couter = 0
        self.parse(dom, fields, values)

    def node_attributes(self, node):
        attrs = node.attributes
    
        if not attrs:
            return {}
        return dict([(str(attrs.item(i).localName), attrs.item(i).nodeValue)
                 for i in range(attrs.length)])

    def parse(self, root=None, fields=None, values=None):
        for node in root.childNodes:

            if node.nodeType not in (node.ELEMENT_NODE, node.TEXT_NODE):
                continue

            attrs = self.node_attributes(node)

            if node.localName=='image':
                pass
            elif node.localName=='separator':
                pass
            elif node.localName=='label':
                pass
            elif node.localName=='newline':
                pass
            elif node.localName=='button':
                pass
            elif node.localName == 'form':
                self.parse(root=node, fields=fields, values=values)
            elif node.localName == 'notebook':
                self.parse(root=node, fields=fields, values=values)
            elif node.localName == 'page':
                pass
            elif node.localName=='group':
                pass
            elif node.localName == 'field':
                name = attrs['name']

                try:
                    fields[name]['link'] = attrs.get('link', '1')
                    fields[name].update(attrs)
                except:
                    raise Exception(
                        _('Invalid view, malformed tag for: %s') % attrs
                    )
                if name in self.view_fields:
                    raise Exception(
                        _('Invalid view, duplicate field: %s') % name
                    )
                self.view_fields.append(name)
            elif node.localName=='hpaned':
                pass
            elif node.localName=='vpaned':
                pass
            elif node.localName in ('child1', 'child2'):
                self.parse(root=node, fields=fields, values=values)
                pass
            elif node.localName=='action':
                pass
            else:
                self.parse(root=node, fields=fields, values=values)
        return True

class MaintenanceCheck(models.Model):
    _name = 'maintenance.check'
    _description = 'Maintenance Check'

    name = fields.Char(
        'Name', size=512, required=True, translate=True
    )
    code = fields.Char(
        'Code', size=64, required=True
    )
    module = fields.Char(
        'Module', size=128, required=True
    )
    description = fields.Text('Description')
    log_ids = fields.One2many(
        'maintenance.check.log', 'check_id', 'Log',
    )

    @api.model
    def check_all_menus(self):
        menu_obj = self.env['ir.ui.menu']
        menus = menu_obj.search([])
        wrong_menus = []
        for menu in menus:
            if not menu.action:
                msg =  'Could not open menu %s with ID %s Exception: no action for menu.' % (
                        tools.ustr(menu.complete_name), menu.id,
                )
                _logger.error(msg)
            if menu.action._name == 'ir.actions.act_window':
                act_window = menu.action
                obj = self.env[act_window.res_model]
                try:
                    if act_window.view_ids:
                        for view in act_window.view_ids:
                            view_get = view(view.view_id.id, view.view_mode)
                            form_checker(view_get)
                    else:
                        first = True
                        for view_mode in act_window.view_mode.split(','):
                            view_id = False
                            if first:
                                view_id = act_window.view_id.id
                                first = False
                            view_get = obj.fields_view_get(view_id, view_mode)
                            form_checker(view_get)
                except Exception as e:
                    wrong_menus.append(menu.complete_name)
                    msg =  'Could not open menu %s. Exception: %s.' % (
                            tools.ustr(menu.complete_name), str(e),
                    )
                    _logger.error(msg)
        if wrong_menus:
            return {
                'found_problem': True,
                'description': u'\n'.join(wrong_menus),
            }
        return {}

    @api.multi
    def do_check(self):
        log_obj = self.env['maintenance.check.log']
        for check in self:
            vals = getattr(self, 'check_%s' % check.code)()
            vals['check_id'] = check.id
            log_obj.create(vals)
        return True

    @api.multi
    def do_fix(self):
        log_obj = self.env['maintenance.check.log']
        for check in self:
            vals = getattr(self, 'fix_%s' % check.code)()
            if vals.get('fixed', False):
                log_ids = log_obj.search([
                    ('check_id','=',check.id),
                    ('found_problem','=',True),
                    ('fixed','=',False),
                ])
                if log_ids:
                    log_obj.write(vals)
        return True


class maintenance_check_log(models.Model):
    _name = 'maintenance.check.log'
    _description = 'maintenance.check.log'
    _rec_name = 'create_date'

    check_id = fields.Many2one(
        'maintenance.check', 'Check', required=True
    )
    create_date = fields.Datetime('Create Date')
    found_problem = fields.Boolean('Found Problem')
    fixed = fields.Boolean('Fixed')
    description = fields.Text('Description')


class maintenance_portal(models.Model):
    _name = 'maintenance.portal'
    _description = 'Maintenance Portal'
    _rec_name = 'host'

    active = fields.Boolean('Active', default=True)
    host = fields.Char('Host', size=128, required=True, default='server.sandas.lt')
    port = fields.Integer('Port', required=True, default=7069)
    login = fields.Char('Login', size=128)
    password = fields.Char('Password', size=128)
    db_name = fields.Char('Database Name', size=128, default='sandas')
    protocol = fields.Selection(
        [('http','http'),('https','https')], 'Protocol', default='https'
    )
    ssh_host = fields.Char('SSH Host', size=128)
    ssh_port = fields.Integer('SSH Port')
    ssh_login = fields.Char('SSH Login', size=128)

class maintenance_server(models.Model):
    _name = 'maintenance.server'
    _description = 'Maintenance Server'
    _rec_name = 'server_path'

    @api.model
    def get_path(self, what):
        if not tools.config.get('addons_path', False):
            return False
        path = os.path.split(tools.config['addons_path'])[0]
        path = os.path.join(path, what)
        return path

    @api.model
    def get_restart_cmd(self):
        if os.getenv('HOME'):
            cmd = os.path.join(os.getenv('HOME'), 'etc', 'init.d')
            cmd = os.path.join(cmd, 'openerp-server-%s' % release.major_version)
            return '%s restart' % cmd
        else:
            return False

    portal_id = fields.Many2one('maintenance.portal', 'Portal', required=True)
    module_ids = fields.One2many('maintenance.server.module', 'server_id', 'Modules')
    application_ids = fields.One2many(
        'maintenance.server.application', 'server_id', 'Application'
    )
    database_ids = fields.One2many(
        'maintenance.server.database', 'server_id', 'Databases'
    )
    versions_archive_path = fields.Char('Versions Archive Path', size=512, default=lambda self: self.get_path('sandas-addons'))
    applications_archive_path = fields.Char(
        'Applications Archive Path', size=512, default=lambda self: self.get_path('sandas-branches')
    )
    addons_path = fields.Char('Addons Path', size=512, default=lambda self: self.get_path('addons'))
    server_path = fields.Char('Server Path', size=512, default=lambda self: self.get_path('server'))
    # web_path = fields.Char('Web Path', size=512, default=get_path('web'))
    # translation_path = fields.Char('Translation Path', size=512)
        
    backup_path = fields.Char('Backup Path', size=512, default=lambda self: self.get_path('backup'))

    restart_cmd = fields.Char('Restart Command', size=512, default=get_restart_cmd)
        
    host = fields.Char('Host', size=128, required=True, default='localhost')
    port = fields.Integer('Port', required=True, default=8069)
    protocol = fields.Selection(
        [('http','http'),('https','https')], 'Protocol', deafult='http'
    )
    run_vacuum = fields.Boolean('Run Vacuum', default=True)

    @api.model
    def run_vacuum_cron(self):
        server_obj = self.env['maintenance.server']
        servers = server_obj.search([('run_vacuum','=',True)])
        for server in servers:
            if sys.platform == 'win32':
                #os.environ["PG_PASSWORD"] = tools.config['db_password'];
                #os.environ["PGPASSWORD"] = tools.config['db_password'];
                os.putenv('PGPASSWORD', tools.config['db_password'])

            for db in server.database_ids:
                if tools.config['pg_path'] and tools.config['pg_path'] != 'None':
                    pg_vacuumdb_cmd = [
                        os.path.join(tools.config['pg_path'], 'vacuumdb')
                    ]
                else:
                    pg_vacuumdb_cmd = ['vacuumdb']
                pg_vacuumdb_cmd.append('-z')
                if tools.config['db_user']:
                    pg_vacuumdb_cmd.append('-U')
                    pg_vacuumdb_cmd.append(tools.config['db_user'])
                if tools.config['db_host']:
                    pg_vacuumdb_cmd.append('-h' + tools.config['db_host'])
                if tools.config['db_port']:
                    pg_vacuumdb_cmd.append('-p ' + str(tools.config['db_port']))
                if sys.platform == 'win32':
                    pg_vacuumdb_cmd.append('-w')

                pg_vacuumdb_cmd.append('-d')
                pg_vacuumdb_cmd.append(db.db_name)
                _logger.info('Vacuum database %s' % (
                        db.db_name
                    )
                )
                res = subprocess.call(pg_vacuumdb_cmd)
                if res != 0:
                    _logger.info(
                        'Vacuum failed for database %s, failed command: %s' % (
                        db.db_name, str(pg_vacuumdb_cmd)
                        )
                    )
                    request_obj = self.env['res.request']
                    request_obj.create({
                        'name': _('Vacuum failed for database %s.') % db.db_name,
                         'state': 'waiting',
                         'act_from': self.env.uid,
                         'act_to': self.env.uid,
                    })
        return True

    @api.model
    def do_backups_threaded(self):
        t = threading.Thread(target=self.do_backups_in_thread)
        t.start()
        return True

    @api.model
    def do_backups_in_thread(self):
        with Environment.manage():
            new_cr = self.pool.cursor()
            new_self = self.with_env(self.env(cr=new_cr))
            try:
                try:
                    new_self.do_backups()
                    new_cr.commit()
                except Exception as e:
                    new_cr.rollback()
                    import traceback
                    import sys
                    tb_s = reduce(lambda x, y: x+y, traceback.format_exception(
                        *sys.exc_info()
                    ))
                    error_msg = tools.exception_to_unicode(e)
                    _logger.error(tb_s)
                    _logger.error(error_msg)
                    raise
            finally:
                new_cr.close()
        return True

    @api.model
    def do_backups(self):
        if sys.platform == 'win32':
            os.environ["PG_PASSWORD"] = tools.config['db_password']
            os.environ["PGPASSWORD"] = tools.config['db_password']

        db_obj = self.env['maintenance.server.database']
        dbs = db_obj.search([('do_backup','=',True)])
        dbs.do_backup_9()
        return True

    @api.model
    def create_link(self, source_dir, dest_dir, overwrite=True):
        _logger.debug('%s -> %s' % (source_dir, dest_dir))
        
        if os.path.exists(source_dir):

            if sys.platform == 'win32':
                _logger.debug('yes %s' % overwrite)

                import distutils.dir_util
                import shutil
                if overwrite and os.path.exists(dest_dir):
                    shutil.rmtree(dest_dir)
                try:
                    distutils.dir_util.copy_tree(source_dir, dest_dir)
                except IOError:
                    pass
                except Exception:
                    pass
                #shutil.copytree(source_dir, dest_dir)
            else:
                if os.path.exists(dest_dir):
                   os.remove(dest_dir)
                os.symlink(source_dir, dest_dir)
        return True

    @api.multi
    def login_to_all_databases(self):
        for server in self:
            for database in server.database_ids:
                if database.db_name == self.env.cr.dbname:
                    continue
                protocol = '%s://' % server.protocol
                url = protocol + server.host + ':' + str(server.port) + '/xmlrpc/'
                rpc_common = xmlrpc.client.ServerProxy(url + 'common')
                rpc_common.login(
                    database.db_name,
                    database.login,
                    database.password
                )
        return True


    @api.multi
    def load_payroll_setup(self):
        for server in self:
            for database in server.database_ids:
                if database.db_name == self.env.cr.dbname:
                    if self.env['ir.module.module'].search([
                        ('name','=','payroll_lt'),
                        ('state','=','installed'),
                    ]):
                        setup_obj = self.env['payroll.calc.load_default_setup']
                        setup = setup_obj.create({})

                        setup.action_load()
                    continue
                protocol = '%s://' % server.protocol
                url = protocol + server.host + ':' + str(server.port) + '/xmlrpc/'
                rpc_common = xmlrpc.client.ServerProxy(url + 'common')
                rpc_object = xmlrpc.client.ServerProxy(url + 'object')

                user_id = rpc_common.login(
                    database.db_name,
                    database.login,
                    database.password
                )
                if rpc_object.execute(
                    database.db_name, user_id, database.password,
                    'ir.module.module', 'search', [
                        ('name','=','payroll_lt'),
                        ('state','=','installed'),
                    ]
                ):
                    setup_id = rpc_object.execute(
                        database.db_name, user_id, database.password,
                        'payroll.calc.load_default_setup', 'create', {}
                    )
                    rpc_object.execute(
                        database.db_name, user_id, database.password,
                        'payroll.calc.load_default_setup', 'action_load', 
                        [setup_id]
                    )
        return True

    @api.multi
    def to_upgrade_module(self, name):

        ir_module_obj = self.env['ir.module.module']
        if not self.database_ids:
            ir_modules = ir_module_obj.search([
                ('name','=',name),
                ('state','=','installed'),
            ])
            if ir_modules:
                ir_modules.button_upgrade()
        else:
            for database in self.database_ids:
                if database.db_name == self.env.cr.dbname:
                    ir_modules = ir_module_obj.search([
                        ('name','=',name),
                        ('state','=','installed'),
                    ])
                    if ir_modules:
                        ir_modules.button_upgrade()
                    continue
                _logger.info('Upgrading modules in database %s' % database.db_name)
                protocol = '%s://' % self.protocol
                url = protocol + self.host + ':' + str(self.port) + '/xmlrpc/'
                rpc_common = xmlrpc.client.ServerProxy(url + 'common')
                user_id = rpc_common.login(
                    database.db_name,
                    database.login,
                    database.password
                )
                rpc_object = xmlrpc.client.ServerProxy(url + 'object')
                ir_module_ids = rpc_object.execute(
                    database.db_name, user_id, database.password,
                    'ir.module.module',
                    'search', [
                        ('name','=',name),
                        ('state','=','installed'),
                    ]
                )
                if ir_module_ids:
                    rpc_object.execute(
                        database.db_name, user_id, database.password,
                        'ir.module.module',
                        'button_upgrade', ir_module_ids
                    )
        return True

    @api.multi
    def update_application_version(self, version):
        appl_obj = self.env['maintenance.server.application']

        for appl_name in (
            'openerp_addons', 'openerp_server', 'openerp_web',
            'openerp_translation'
        ):
            if appl_name not in version:
                continue
            appl = appl_obj.search([
                ('name','=',appl_name),
            ], limit=1)
            if appl:
                if appl.version == version:
                    continue

                appl.write({
                    'version': version,
                })
            else:
                appl_obj.create({
                    'server_id': self.id,
                    'name': appl_name,
                    'version': version,
                })
        return True

    @api.multi
    def update_module_version(self, module_name, version):
        module_obj = self.env['maintenance.server.module']
        module_rec = module_obj.search([
            ('name','=',module_name),
        ])
        if module_rec:
            if module_rec.version == version:
                return False
            module_rec.write({
                'version': version,
            })
        else:
            module_obj.create({
                'server_id': self.id,
                'name': module_name,
                'version': version,
            })
        return True

    @api.multi
    def install_modules(
        self, source_dir, dest_dir, version,
        branch_name=False, force_create_link=False,
        application=False, do_not_upgrade_module=False
    ):
        if not version:
            if [f for f in os.listdir(source_dir) \
                if os.path.isdir(os.path.join(source_dir, f))
            ]:
                if not do_not_upgrade_module:
                    self.to_upgrade_module(application)
                if sys.platform != 'win32':
                    self.create_link(source_dir, os.path.join(dest_dir, application))
        for _dir in os.listdir(source_dir):
            if not (_dir != '.' and _dir != '..' and _dir[0] != '.'):
                continue

            create_link = force_create_link
            if not version or self.update_module_version(_dir, version):
                if not do_not_upgrade_module:
                    self.to_upgrade_module(_dir)
                create_link = True

            if create_link:
                curr_dest_dir = os.path.join(dest_dir, os.path.basename(_dir))
                if not branch_name:
                    source_full_path = os.path.join(source_dir, _dir)
                else:
                    source_full_path = os.path.join(
                        source_dir, _dir, branch_name
                    )
                if os.path.isdir(source_full_path):
                    self.create_link(source_full_path, curr_dest_dir)
        return True

    @api.model
    def unzip_file_into_dir(self, ffile, dirr):
        import zipfile
        os.mkdir(dirr)
        zfobj = zipfile.ZipFile(ffile)
        for name in zfobj.namelist():
            if name.endswith('/'):
                os.mkdir(os.path.join(dirr, name))
            else:
                head, tail = os.path.split(os.path.join(dirr, name))
                if not os.path.exists(head):
                    os.makedirs(head)
                outfile = open(os.path.join(dirr, name), 'wb')
                outfile.write(zfobj.read(name))
                outfile.close()

    @api.multi
    def sync_ids(self):
        for server in self:
            server.sync()
        return True

    @api.multi
    def load_ids(self):
        for server in self:
            server.load()
        return True

    @api.multi
    def load(self):
        portal = self.portal_id

        protocol = '%s://' % portal.protocol
        url = protocol + portal.host + ':' + str(portal.port) + '/xmlrpc/'
        rpc_common = xmlrpc.client.ServerProxy(url + 'common')
        user_id = rpc_common.login(
            portal.db_name,
            portal.login,
            portal.password,
        )
        
        rpc_object = xmlrpc.client.ServerProxy(url + 'object')

        install_ids = rpc_object.execute(
            portal.db_name, user_id, portal.password,
            'portal.maintenance.installation',
            'search', [
                ('installed','=',True),
                ('user_id','=',user_id),
            ], False, 1, 'install_date desc'
        )
        if not install_ids:
            return False

        install = rpc_object.execute(
            portal.db_name, user_id, portal.password,
            'portal.maintenance.installation', 
            'read', install_ids[0], ['version_ids', 'application_ids']
        )
        for application_id in install['application_ids']:
            application = rpc_object.execute(
                portal.db_name, user_id, portal.password, 
                'portal.maintenance.application', 'read',
                application_id, ['name']
            )
            self.update_application_version(application['name'])
        if self.versions_archive_path:
            for version_id in install['version_ids']:
                version = rpc_object.execute(
                    portal.db_name, user_id, portal.password, 
                    'portal.maintenance.version', 'read',
                    version_id, ['name'], 
                )
                for _dir in os.listdir(os.path.join(
                    self.versions_archive_path, version['name']
                )):
                    if not (_dir != '.' and _dir != '..' and _dir[0] != '.'):
                        continue

                    self.update_module_version(_dir, version['name'])
        return True


    @api.multi
    def sync(self, only_auto_install=False):
        if not self.portal_id or not self.portal_id.active:
            return False
        
        appl_obj = self.env['maintenance.server.application']

        portal = self.portal_id

        protocol = '%s://' % portal.protocol
        url = protocol + portal.host + ':' + str(portal.port) + '/xmlrpc/'
        rpc_common = xmlrpc.client.ServerProxy(url + 'common')
        user_id = rpc_common.login(
            portal.db_name,
            portal.login,
            portal.password,
        )
        
        rpc_object = xmlrpc.client.ServerProxy(url + 'object')

        domain = [
            ('installed','=',False),
            ('to_be_installed','=',True),
            ('user_id','=',user_id),
        ]
        if only_auto_install:
            domain.append(('auto_install','=',True))

        install_ids = rpc_object.execute(
            portal.db_name, user_id, portal.password,
            'portal.maintenance.installation',
            'search', domain
        )
        installs = []
        for i in range(10):
            try:
                installs = rpc_object.execute(
                    portal.db_name, user_id, portal.password,
                    'portal.maintenance.installation', 
                    'read', install_ids, ['version_ids', 'application_ids']
                )
                break
            except Exception:
                if i < 9:
                    raise
        for install in installs:
            force_create_links = False
            if self.applications_archive_path:
                if not os.path.exists(self.applications_archive_path):
                    os.makedirs(self.applications_archive_path)
                for application_id in install['application_ids']:
                    for i in range(10):
                        try:
                            application = rpc_object.execute(
                                portal.db_name, user_id, portal.password, 
                                'portal.maintenance.application', 'read',
                                application_id, ['name']
                            )
                            break
                        except Exception:
                            if i < 9:
                                raise
                    application_path = os.path.join(
                        self.applications_archive_path, application['name']
                    )
                    if not os.path.exists(application_path):
                        _logger.info('Downloading %s' % application['name'])
                        application_zip = rpc_object.execute(
                            portal.db_name, user_id, portal.password, 
                            'portal.maintenance.application', 'download', 
                            application['id']
                        )
                        zip_file_name = os.path.join(
                            self.applications_archive_path,
                            '%s.zip' % application['name']
                        )
                        f = open(zip_file_name, 'wb')
                        f.write(base64.decodestring(application_zip.encode('utf-8')))
                        f.close()
                        self.unzip_file_into_dir(
                            zip_file_name, application_path
                        )

                    for appl_name in (
                        'openerp_addons', 'openerp_server', 'openerp_web',
                        'openerp_translation'
                    ):
                        if appl_name not in application['name']:
                            continue
            
                        appl = appl_obj.search([
                            ('name','=',appl_name),
                        ])
                        if appl and appl.version == application['name']:
                            continue

                        if appl_name in ('openerp_addons', 'openerp_server'):
                            _logger.info('Marking base module to upgrade')
                            self.to_upgrade_module('base')
                        _logger.info('Creating link for %s' % application['name'])
                        dest_path = False
                        if appl_name == 'openerp_addons':
                            dest_path = self.addons_path
                            force_create_links = True
                        if appl_name == 'openerp_server':
                            dest_path = self.server_path
                        if appl_name == 'openerp_web':
                            dest_path = self.web_path
                        if appl_name == 'openerp_translation':
                            dest_path = self.translation_path
                        self.create_link(
                            application_path, dest_path, overwrite=False
                        )

                    self.update_application_version(application['name'])
            
            if self.applications_archive_path:
                for application_id in install['application_ids']:
                    application = rpc_object.execute(
                        portal.db_name, user_id, portal.password, 
                        'portal.maintenance.application', 'read',
                        application_id, 
                        ['application', 'version', 'release', 'name']
                    )
                    if application['application'] in (
                        'openerp_addons', 'openerp_server',
                        'openerp_translation', 'openerp_client'
                    ):
                        continue
                    if application['application'].endswith('lib'):
                        continue

                    if self.addons_path:
                        if application['application'] == 'koo':
                            application_path = os.path.join(
                                self.applications_archive_path,
                                application['name'],
                                'server-modules'
                            )
                        elif application['application'] == 'openerp_web':
                            application_path = os.path.join(
                                self.applications_archive_path,
                                application['name'],
                                'addons'
                            )
                        else:
                            application_path = os.path.join(
                                self.applications_archive_path,
                                application['name']
                            )
                        appl_br = appl_obj.search([
                            ('name','=',application['application']),
                            ('server_id','=',self.id),
                        ], limit=1)
                        version_changed = False
                        if appl_br:
                            if appl_br.version != application['name']:
                                appl_br.write({'version': application['name']})
                                version_changed = True
                        else:
                            appl_obj.create({
                                'server_id': self.id,
                                'name': application['application'],
                                'version': application['name'],
                            })
                            version_changed = True

                        if self.addons_path:
                            self.install_modules(
                                application_path,
                                self.addons_path,
                                False,
                                force_create_link=force_create_links,
                                application=application['application'],
                                do_not_upgrade_module=not version_changed
                            )
            
            if self.versions_archive_path:
                if not os.path.exists(self.versions_archive_path):
                    os.makedirs(self.versions_archive_path)
                for version_id in install['version_ids']:
                    for i in range(10):
                        try:
                            version = rpc_object.execute(
                                portal.db_name, user_id, portal.password, 
                                'portal.maintenance.version', 'read',
                                version_id, ['name'], 
                            )
                            break
                        except Exception:
                            if i < 9:
                                raise
                    version_path = os.path.join(
                        self.versions_archive_path, version['name']
                    )
                    if not os.path.exists(version_path):
                        _logger.info('Downloading %s' % version['name'])
                        version_zip = rpc_object.execute(
                            portal.db_name, user_id, portal.password, 
                            'portal.maintenance.version', 'download', 
                            version['id']
                        )
                        zip_file_name = os.path.join(
                            self.versions_archive_path,
                            '%s.zip' % version['name']
                        )
                        f = open(zip_file_name, 'wb')
                        f.write(base64.decodestring(version_zip.encode('utf-8')))
                        f.close()
                        self.unzip_file_into_dir(
                            zip_file_name, version_path
                        )

                    if self.addons_path:
                        self.install_modules(
                            version_path, self.addons_path,
                            version['name'],
                            force_create_link=force_create_links
                        )

            rpc_object.execute(
                portal.db_name, user_id, portal.password,
                'portal.maintenance.installation', 
                'installation_done', [install['id']]
            )
        return bool(installs)

    @api.model
    def run_command(
        self, args, cwd=None, raise_exception=True,
    ):
        _logger.debug('Trying to run command %s in cwd %s.' % (
                str(args), str(cwd)
            ))
        res = subprocess.call(args, cwd=cwd)
        if res != 0 and raise_exception:
            raise UserError(
                _('Error in trying to run command %s. Error code: %s') % (
                    ' '.join(args),
                    res,
                )
            )
        return res

    @api.multi
    def restart_ids(self):
        for server in self:
            if not server.restart_cmd:
                raise UserError(
                    _('Unknown restart command in server.'),
                )
            self.run_command(server.restart_cmd.split(' '))
        return True

    @api.model
    def do_auto_install(self):
        servers = self.search([])
        if not servers:
            return False

        for server in servers:
            if server.sync(
                only_auto_install=True
            ):
                servers.restart_ids()
        return True


class MaintenanceServerModule(models.Model):
    _name = 'maintenance.server.module'
    _description = 'Maintenance Server Module'

    server_id = fields.Many2one(
        'maintenance.server', 'Server', required=True
    )
    name = fields.Char('Name', size=128, required=True)
    version = fields.Char('Version', size=128)


class MaintenanceServerApplication(models.Model):
    _name = 'maintenance.server.application'
    _description = 'Maintenance Server Application'

    server_id = fields.Many2one(
        'maintenance.server', 'Server', required=True
    )
    name = fields.Char('Name', size=128, required=True)
    version = fields.Char('Version', size=128)


class MaintenanceServerDatabase(models.Model):
    _name = 'maintenance.server.database'
    _description = 'Maintenance Server Database'

    server_id = fields.Many2one(
        'maintenance.server', 'Server', required=True
    )
    active = fields.Boolean('Active', default=True)
    login = fields.Char('Login', size=128, required=True, default='admin')
    password = fields.Char('Password', size=128)
    db_name = fields.Char('Database Name', size=128, required=True, default=lambda self: self.env.cr.dbname)
    do_backup = fields.Boolean('Do Backup', default=False)
    backup_ttl = fields.Integer(
        'Backup TTL', help='Backup time to leave in days.', default=30
    )
    upload = fields.Boolean('Upload', default=False)
    upload_folder = fields.Char('Upload Folder', size=512)

    @api.multi
    def do_backup_9(self):
        import subprocess

        #if sys.platform == 'win32':
        #    os.environ["PG_PASSWORD"] = tools.config['db_password'];
        #    os.environ["PGPASSWORD"] = tools.config['db_password'];
            
        for db in self:
            backup_only_fname = '%s-%s.dump' % (
                db.db_name, time.strftime('%Y%m%d')
            )
            backup_fname =  os.path.join(
                db.server_id.backup_path, backup_only_fname
            )
            if os.path.exists(backup_fname):
                continue
            
            if not os.path.exists(db.server_id.backup_path):
                os.makedirs(db.server_id.backup_path)

            if db.backup_ttl:
                for curr_file in os.listdir(db.server_id.backup_path):
                    if len(curr_file) != len(backup_only_fname):
                        continue
                    if curr_file[:len(db.db_name)+1] != db.db_name + '-':
                        continue
                    if curr_file[-5:] != '.dump':
                        continue
                    dt_from_file = curr_file[len(db.db_name)+1:-5]
                    dt = datetime.datetime.strptime(
                        dt_from_file, '%Y%m%d'
                    )
                    if (datetime.datetime.now() - dt).days > db.backup_ttl:
                        os.remove(os.path.join(
                            db.server_id.backup_path, curr_file
                        ))

            if sys.platform == 'win32':
                pg_dump_cmd = [
                    os.path.join(tools.config['pg_path'], 'pg_dump')
                ]
            else:
                if tools.config['pg_path'] and tools.config['pg_path'] != 'None':
                    pg_dump_cmd = [
                        os.path.join(tools.config['pg_path'], 'pg_dump')
                    ]
                else:
                    pg_dump_cmd = ['pg_dump']
            pg_dump_cmd.append('--format=c')
            if tools.config['db_user']:
                pg_dump_cmd.append('-U')
                pg_dump_cmd.append(tools.config['db_user'])
            if tools.config['db_host']:
                pg_dump_cmd.append('-h' + tools.config['db_host'])
            if tools.config['db_port']:
                pg_dump_cmd.append('-p ' + str(tools.config['db_port']))
            if sys.platform == 'win32':
                pg_dump_cmd.append('-w')

            pg_dump_cmd.append('-f' + backup_fname)
            pg_dump_cmd.append(db.db_name)
            _logger.debug('Backup database %s' % (
                    db.db_name
                ))
            
            if sys.platform == 'win32':
                #os.system('SET PGPASSWORD=%s' % tools.config['db_password'])
                os.putenv('PGPASSWORD', tools.config['db_password'])
            _logger.debug('Running backup command: %s' % (
                    ' '.join(pg_dump_cmd)
                ))
            res = subprocess.call(pg_dump_cmd)
            if res != 0:
                _logger.debug(
                    'Backup failed for database %s. Tried this command: %s' % (
                    db.db_name, ' '.join(pg_dump_cmd)
                    )
                )
                request_obj = self.env['res.request']
                request_obj.create({
                    'name': _('Backup failed for database %s.') % (
                        db.db_name
                    ),
                     'state': 'waiting',
                     'act_from': self.env.uid,
                     'act_to': self.env.uid,
                })
                continue

            if db.upload:
                upload_folder = ''
                if db.upload_folder:
                    upload_folder = db.upload_folder
                    if not upload_folder.endswith('/'):
                        upload_folder += '/'
                scp_cmd = ['scp', '-P %d' % db.server_id.portal_id.ssh_port, backup_fname, '%s@%s:%s' % (
                    db.server_id.portal_id.ssh_login,
                    db.server_id.portal_id.ssh_host,
                    upload_folder,
                )]
                res = subprocess.call(scp_cmd)
                if res != 0:
                    _logger.debug('Upload backup failed for database %s' % (
                            db.db_name
                        ))
                    request_obj = self.env['res.request']
                    request_obj.create({
                        'name': _('Upload backup failed for database %s. With command %s.') % (
                            db.db_name, ' '.join(scp_cmd)
                        ),
                         'state': 'waiting',
                         'act_from': self.env.uid,
                         'act_to': self.env.uid,
                    })
                    continue
        return True

class MaintenanceContractWizard(models.Model):
    _name = 'maintenance.contract.wizard'

    name = fields.Char('Contract ID', size=256, required=True)
    password = fields.Char('Password', size=64, required=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('validated', 'Validated'),
         ('unvalidated', 'Unvalidated')
         ], 'States', default='draft'
    )
    date_from = fields.Date('Starting Date', required=True)
    date_to = fields.Date('Ending Date', required=True)

    @api.multi
    def action_validate(self):
        if not self:
            return False

        contract_obj = self.env['maintenance.contract']

        contract_modules = contract_obj.create_all_installed_modules()

        contract_obj.create({
            'name' : self[0]['name'],
            'password' : self[0]['password'],
            'date_start' : self[0]['date_from'],
            'date_stop' : self[0]['date_to'],
            'kind' : 'full',
            'module_ids' : [(6,0,contract_modules.mapped('id'))],
        })

        return self.write({
            'state': 'validated'
        })


