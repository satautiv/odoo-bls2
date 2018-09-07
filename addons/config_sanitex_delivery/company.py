# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import api, models, fields
from datetime import datetime, timedelta
from odoo.tools import config
from odoo import _

import xmlrpc
import logging

_logger = logging.getLogger(__name__)

DATE_FIELDS = {
    'sale.order': 'delete_transportation_tasks_using_date',
    'stock.route': 'delete_routes_using_date',
    'account.invoice': 'delete_invoices_using_date',
    'stock.package': 'delete_packages_using_date',
    'account.invoice.container': 'delete_containers_using_date',
    'transportation.order': 'delete_transportation_orders_using_date',
}

class AtlasServers(models.Model):
    _name = 'atlas.server'
    _description = 'Atlas Server'

    name = fields.Char('Name', size=128, required=True)
    ip = fields.Char('IP', size=32, required=True)
    port = fields.Integer('Port', required=True, default=11069)
    database_ids = fields.One2many('atlas.server.database', 'server_id', 'Databases')

    @api.multi
    def connect_xml_rpc(self):
        return xmlrpc.client.ServerProxy('%s://%s:%s/xmlrpc/object' % (
            'http', self.ip, self.port
        ))

class AtlasServerDatabase(models.Model):
    _name = 'atlas.server.database'
    _description = 'Atlas Database'

    login = fields.Char('Login', size=64, required=True, default='admin')
    user_id = fields.Integer('User ID', readonly=True)
    password = fields.Char('Password', size=64, required=True)
    name = fields.Char('Name', size=64, required=True)
    server_id = fields.Many2one('atlas.server', 'Atlas Server', required=True)

    @api.model
    def get_user_id(self, username, password, url, database):
        common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
        uid = common.authenticate(database, username, password, {})
        return uid

    @api.multi
    def update_user_id(self):
        for database in self:
            if not database.server_id:
                continue
            user_id = self.get_user_id(
                database.login, database.password,
                'http://' + database.server_id.ip + ':' + str(database.server_id.port),
                database.name
            )
            database.write({'user_id': user_id})

    @api.model
    def create(self, vals):
        database = super(AtlasServerDatabase, self).create(vals)
        database.update_user_id()
        return database

    @api.multi
    def write(self, vals):
        res = super(AtlasServerDatabase, self).write(vals)
        if 'login' in vals.keys():
            self.update_user_id()
        return res

    @api.multi
    def call_method(self, model, method, args=None, connection=None):
        if connection is None:
            connection = self.server_id.connect_xml_rpc()
        if args is None:
            return connection.execute_kw(
                self.name, self.user_id, self.password,
                model, method
            )
        return connection.execute_kw(
            self.name, self.user_id, self.password,
            model, method, args
        )

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    @api.model
    def _get_drivers(self):
        return self.env['printer']._get_default_drivers()

    @api.model
    def _get_create_date_for_model(self, model):
        return self.env['ir.model.fields'].search([('model_id.model','=',model),('name','=','create_date')])

    @api.model
    def _get_default_date_for_removing_sale_orders(self):
        return self._get_create_date_for_model('sale.order')

    @api.model
    def _get_default_date_for_removing_invoices(self):
        return self._get_create_date_for_model('account.invoice')

    @api.model
    def _get_default_date_for_removing_containers(self):
        return self._get_create_date_for_model('account.invoice.container')

    @api.model
    def _get_default_date_for_removing_routes(self):
        return self._get_create_date_for_model('stock.route')

    @api.model
    def _get_default_date_for_removing_packages(self):
        return self._get_create_date_for_model('stock.package')

    @api.model
    def _get_default_date_for_removing_transportation_orders(self):
        return self._get_create_date_for_model('transportation.order')

    @api.model
    def _get_languages(self):
        return self.env['res.lang'].get_available()

    packaging_category_id = fields.Many2one(
        'product.category', 'Default Product Category',
        help='Used when creating packages'
    )
    use_contract = fields.Boolean(
        'Use Contracts',
        help='Check this field if you want to use contracts functionality'
    )
    sanitex_owner_partner_id = fields.Many2one(
        'res.partner', 'Sanitex Owner',
        help='Owner Filled in in Route'
    )
    bls_owner_partner_id = fields.Many2one(
        'res.partner', 'BLS Owner',
        help='Owner Filled in in Route'
    )
    do_not_process_intermediate_objects = fields.Boolean(
        'Do Not Process Intermediate Objects',
        help='Check this field if you don\'t want to create objects when they are imported to Odoo. They will be put to queue'
    )
    log_cron = fields.Boolean('Log cron')
    cron_domain = fields.Char('Import Domain', size=256,
        help='This domain is used when cron selects which intermediate objects to process'
    )
    company_code = fields.Char('Code', help='Code for synchronization')
    export_ivaz = fields.Boolean('Export IVAZ', default=False)
    ivaz_export_server = fields.Char('IVAZ Export Server', size=256, default='http://192.168.101.129:8085/waybill2vmi/waybills.json')
    ivaz_export_token = fields.Char('IVAZ Export Token', size=256)
    report_server = fields.Char('Reports Server', size=256, default='http://192.168.52.229/PdfDoc/PdfDoc.ashx?req=pdfdocument')
    report_location = fields.Char('Report File Store Location', size=256)
    export_tare_document = fields.Boolean('Export Tare Documents', default=False)
    tare_export_server = fields.Char('Tare Export Server', size=256, default='http://192.168.101.129:3001/api/taredocuments')
    tare_export_token = fields.Char('Tare Export Token', size=256)
    tare_export_source = fields.Char('Tare Export Source', size=64)
    default_driver = fields.Selection(_get_drivers, 'Default Driver')
    ssh_password = fields.Char('SSH Password', size=32)
    unlinkt_old_objects_after_days = fields.Integer('Unlink Old Objects After', default=30, help='''
stock.route.integration.intermediate
delivery.integration.log
''')
    delete_reports_after = fields.Integer('Delete Report Files After', default=1)
    delete_report_history_after = fields.Integer('Delete Report History After', default=90)

    delete_transportation_tasks_after = fields.Integer('Delete Transportation Tasks After', default=356)
    delete_transportation_tasks_using_date = fields.Many2one('ir.model.fields', 'Delete Transportation Tasks Using',
                                                             domain=[('model_id.model','=','sale.order'),('ttype','in',['date', 'datetime'])],
                                                             default=_get_default_date_for_removing_sale_orders, help='If left empty create date will be used'
                                                             )
    delete_invoices_after = fields.Integer('Delete Invoices After', default=356)
    delete_invoices_using_date = fields.Many2one('ir.model.fields', 'Delete Invoices Using',
                                                 domain=[('model_id.model','=','account.invoice'),('ttype','in',['date', 'datetime'])],
                                                 default=_get_default_date_for_removing_invoices, help='If left empty create date will be used'
                                                 )
    delete_packages_after = fields.Integer('Delete Packages After', default=356)
    delete_packages_using_date = fields.Many2one('ir.model.fields', 'Delete Packages Using',
                                                 domain=[('model_id.model','=','stock.package'),('ttype','in',['date', 'datetime'])],
                                                 default=_get_default_date_for_removing_packages, help='If left empty create date will be used'
                                                 )
    delete_routes_after = fields.Integer('Delete Routes After', default=356)
    delete_routes_using_date = fields.Many2one('ir.model.fields', 'Delete Routes Using',
                                               domain=[('model_id.model','=','stock.route'),('ttype','in',['date', 'datetime'])],
                                               default=_get_default_date_for_removing_routes, help='If left empty create date will be used'
                                               )
    delete_containers_after = fields.Integer('Delete Containers After', default=356)
    delete_containers_using_date = fields.Many2one('ir.model.fields', 'Delete Containers Using',
                                                   domain=[('model_id.model','=','account.invoice.container'),('ttype','in',['date', 'datetime'])],
                                                   default=_get_default_date_for_removing_containers, help='If left empty create date will be used'
                                                   )
    delete_transportation_orders_after = fields.Integer('Delete Transportation Orders After', default=356)
    delete_transportation_orders_using_date = fields.Many2one('ir.model.fields', 'Delete Transportation Orders Using',
                                                   domain=[('model_id.model','=','transportation.order'),('ttype','in',['date', 'datetime'])],
                                                   default=_get_default_date_for_removing_transportation_orders, help='If left empty create date will be used'
                                                   )
    log_delete_progress = fields.Boolean('Log Progress', default=False, help='Show progress of deletion cron in log')
    allowed_driver_ids = fields.Many2many('printer.driver', 'driver_company_rel', 'company_id', 'driver_id', 'Allowed Drivers')
    log_report_xml = fields.Boolean('Log Report Data', default=False)
    fax = fields.Char('Fax', size=64)
    limit_of_route_rest_export = fields.Integer('Route Export Limit', default=50)
    ivaz_source = fields.Char('IVAZ Source', size=64, default='Odoo')
    stuck_integration_obj_time = fields.Integer('Stuck Integration Object Time in Minutes', default=20)
    default_account_id = fields.Many2one('account.account', 'Default Account', help='Account for creating Invoices from Import')
    route_export_api_version = fields.Integer('Route Export Version', default=1)
    monitoring_server = fields.Char('Monitoring Server', size=256, default='http://192.168.101.132:9019/api/console')
    monitoring_token = fields.Char('Monitoring Token', size=256)
    import_language = fields.Selection(_get_languages, 'Import Language', default='lt_LT')
    pod_integration_limit_ids = fields.One2many('pod.integration', 'company_id', "POD Integration Limit")
    report_language = fields.Char('Report Language', size=32, help='Report Language')
    atlas_server_ids = fields.Many2many('atlas.server', 'company_server_rel', 'server_id', 'company_id', 'Atlas Servers')
    loadlist_report_sender_id = fields.Many2one('product.owner', 'Loadlist Sender',
        help='When printing Loadlist report, contact information of this owner will be given.'
    )
    user_faster_export = fields.Boolean('User faster export', default=False,
        help='Export to csv or excel.'
    )
    use_new_numbering_method = fields.Boolean('Use New Numbering Method', default=False)

    @api.multi
    def get_sender_for_loadlist_report(self):
        # Spausdinant draivą kaip siuntėjo informacija visada turi būti ta pati(kaip kažkurio savininko),
        # bet ta savininko informacija skiriasi priklausomai ar tai Lietuvos ar Latvijos ar Estijos serveris
        # Ši funkcija grąžina reikiamą savininką.

        owner = self.loadlist_report_sender_id
        if not owner:
            owner = self.env['product.owner'].search([('owner_code','in',['BSO', 'BL2'])], limit=1)
        return owner

    @api.multi
    def do_use_new_numbering_method(self):
        return self.use_new_numbering_method

    @api.model
    def get_put_in_queue(self, function_to_put_in_queue):
        if function_to_put_in_queue == '_extend_tasks':
            return not config.get('do_not_put__extend_tasks_in_queue', False)
        return True

    @api.model
    def get_default_account(self):
        acc = self.env['res.users'].browse(self.env.uid).company_id.default_account_id
        if not acc:
            acc = self.env['account.account'].search([('code','=','111100')], limit=1)
        return acc

    @api.multi
    def get_address(self):
        parts = []
        if self.street:
            parts.append(self.street)
        if self.street2:
            parts.append(self.street2)
        if self.city:
            parts.append(self.city)
        if self.state_id and self.state_id.name:
            parts.append(self.state_id.name)
        if self.zip:
            parts.append(self.zip)
        if self.country_id:
            parts.append(self.country_id.name)
        return ', '.join(parts)
    
    @api.model
    def get_allowed_printer_drivers(self):
        return [(driver.code, driver.name) for driver in self.allowed_driver_ids]

    @api.multi
    def get_date_field_for_removing_object(self, model=False):
        # Trinant senus objektus, objekto senumas bus tikrinamas pagal
        # datos laukelį, kurį grąžins ši funkcija. Datos laukelis nusistato
        # prie įmonės nustatymų, jei nenustatyta grąžinama bus create_date.
        # Jei nepaduodamas modelis grąžinamas dictionary su visais variantais

        if model:
            if model not in DATE_FIELDS.keys():
                return 'create_date'
            else:
                field = getattr(self, DATE_FIELDS[model])
                if field:
                    return field.name
                else:
                    return 'create_date'
        else:
            res = {}
            for model_key in DATE_FIELDS.keys():
                field = getattr(self, DATE_FIELDS[model_key])
                if field:
                    res[model_key] = field.name
                else:
                    res[model_key] = 'create_date'
            return res


    @api.model
    def cron_delete_old_objects(self):
        self.env['stock.route'].cron_delete_old_routes()
        self.env['account.invoice.container'].cron_delete_old_containers()
        self.env['stock.package'].cron_delete_old_packages()
        self.env['account.invoice'].cron_delete_old_account_invoices()
        self.env['sale.order'].cron_delete_old_transportation_tasks()
        self.env['transportation.order'].cron_delete_old_transportation_orders()
        self.clean_up_database()

    @api.model
    def clean_up_database(self):
        for model_tuple in [
            ('sale.order', 'sale_order'),
            ('sale.order.line', 'sale_order_line'),
            ('account.invoice', 'account_invoice'),
            ('account.invoice.line', 'account_invoice_line'),
            ('stock.package', 'stock_package'),
            ('stock.route', 'stock_route'),
            ('stock.package.document', 'stock_package_document'),
            ('account.invoice.container', 'account_invoice_container'),
        ]:
            sql = '''
                SELECT
                    mm.id
                FROM
                    mail_message as mm
                    LEFT JOIN ''' + model_tuple[1] + ''' as temp on (temp.id=mm.res_id)
                WHERE
                    mm.model = %s
                    AND temp.id is null
                LIMIT
                    1000
            '''
            where = (model_tuple[0],)
            self.env.cr.execute(sql, where)
            result = self.env.cr.fetchall()
            ids_to_del = [r[0] for r in result]
            while ids_to_del:
                delete_sql = '''
                    DELETE 
                    FROM
                        mail_message
                    WHERE 
                        id in %s
                '''
                delete_where = (tuple(ids_to_del),)
                _logger.info('Deleteing from mail_message (%s, %s)' % (str(len(ids_to_del)), model_tuple[1]))
                self.env.cr.execute(delete_sql, delete_where)
                self.env.cr.commit()
                self.env.cr.execute(sql, where)
                result = self.env.cr.fetchall()
                ids_to_del = [r[0] for r in result]

        sql = '''
            SELECT
                count(*)
            FROM
                mail_followers
        '''
        self.env.cr.execute(sql)
        result = self.env.cr.fetchall()
        _logger.info('Deleteing from mail_followers (%s)' % (str(result[0])))
        delete_sql = '''
            DELETE FROM mail_followers
        '''
        self.env.cr.execute(delete_sql)



    @api.multi
    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        if {'delete_transportation_tasks_after', 'delete_routes_after', 'delete_invoices_after'} & set(vals.keys()):
            self.env['stock.route.integration.intermediate'].update_skip_import_values()
        return res

    @api.multi
    def open_statistics(self):
        stat_env = self.env['statistics.integration']
        stats = stat_env.create_if_not_exists()
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'statistics.integration',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'res_id': stats.id,
        }

    @api.multi
    def get_route_export_version(self):
        user = self.env['res.users'].browse(self.env.uid)
        if user:
            company = user.company_id
            if company and company.route_export_api_version:
                return company.route_export_api_version
        return 1


class StatisticsIntegration(models.Model):
    _name = 'statistics.integration'
    _description = 'Integration Statistics'

    statistics_line_ids = fields.One2many(
        'statistics.integration.line', 'statistics_id',
        'Lines by Integration'
    )
    statistics_by = fields.Selection([
        ('time_d','Time (days)'),
        ('time_h','Time (hours)'),
        ('count','Count'),
        ('count_p', 'Count %')
    ], 'Statitstics By')
    value1 = fields.Integer('Last')
    value2 = fields.Integer('Last')
    value3 = fields.Integer('Last')
    last_update = fields.Datetime('Last Update', readonly=True)

    @api.multi
    def create_lines(self):
        for stat in self:
            line_env = self.env['statistics.integration.line']
            functions = line_env._get_selection_list()
            for function_tuple in functions:
                line = line_env.search([
                    ('statistics_id','=',stat.id),
                    ('function','=',function_tuple[0])
                ])
                if not line:
                    line.create({
                        'statistics_id': stat.id,
                        'function': function_tuple[0]
                    })

    @api.multi
    def recount(self):
        self.refresh()
        return {
            "type": "ir.actions.dialog_reload",
        }

    @api.multi
    def refresh(self):
        for stat in self:
            stat.create_lines()
            stat.statistics_line_ids.refresh()

    @api.model
    def create_if_not_exists(self):
        stat = self.search([], limit=1)
        if not stat:
            stat = self.create({})
        stat.create_lines()
        return stat

class StatisticsIntegrationLine(models.Model):
    _name = 'statistics.integration.line'
    _description = 'Integration Statistics Line'

    @api.model
    def _get_selection_list(self):
        return self.env['stock.route.integration.intermediate'].get_selection_values()

    statistics_id = fields.Many2one(
        'statistics.integration', 'Statistics',
        ondelete='cascade', readonly=True
    )
    function = fields.Selection(_get_selection_list, 'Function', readonly=True)
    value1 = fields.Char('Value 1', size=64, readonly=True)
    value2 = fields.Char('Value 2', size=64, readonly=True)
    value3 = fields.Char('Value 3', size=64, readonly=True)

    @api.model
    def format_value(self, value):
        if value is None:
            return '0'
        if value > 60:
            minutes = int(value) // 60
            sec = int(value - minutes*60)
            return str(minutes) + 'min ' + str(sec) + 's'
        else:
            return str(int(value)) + 's'

    @api.multi
    def refresh(self):
        for line in self:
            line_vals = {}
            stat_by = line.statistics_id.statistics_by
            values_by = [line.statistics_id.value1, line.statistics_id.value2, line.statistics_id.value3]
            value_i = 0
            for value_by in values_by:
                value_i += 1

                if stat_by == 'count':
                    where = ''
                    limit = ' limit %s ' % str(value_by)
                elif stat_by == 'count_p':
                    where = ''
                    self.env.cr.execute('''
                        SELECT 
                            count(*) 
                        FROM 
                            stock_route_integration_intermediate
                        WHERE
                            processed = True
                            AND function = '%s'
                    ''' % line.function)
                    count = self.env.cr.fetchall()
                    if count:
                        count = int(count[0][0] * (value_by / 100.0))
                    else:
                        count = 0
                    limit = ' limit %s ' % str(count)
                elif stat_by == 'time_d':
                    now = datetime.now()
                    days_ago = (now - timedelta(days=value_by)).strftime('%Y-%m-%d 23:59:59')
                    where = ' AND end_time >= \'%s\' ' % days_ago
                    limit = ''
                elif stat_by == 'time_h':
                    now = datetime.now()
                    days_ago = (now - timedelta(hours=value_by)).strftime('%Y-%m-%d %H:%M:%S')
                    where = ' AND end_time >= \'%s\' ' % days_ago
                    limit = ''

                sql = '''
                    SELECT
                        AVG(duration), COUNT(*)
                    FROM
                        (SELECT
                            duration
                        FROM
                            stock_route_integration_intermediate
                        WHERE
                            processed = True
                            AND function = '%s'
                            %s
                        ORDER BY 
                            id DESC
                        %s
                        ) temp
                    ''' % (line.function, where, limit)
                self.env.cr.execute(sql)
                result = self.env.cr.fetchall()
                if result:
                    average = result[0][0]
                    count = result[0][1]
                else:
                    average = 0
                    count = 0
                line_vals['value'+str(value_i)] = self.format_value(average) + ' [' + str(count) + '] ' + _('integrations')
            line.write(line_vals)