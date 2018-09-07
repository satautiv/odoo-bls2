# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

# from datetime import datetime, timedelta
# import time
from odoo import fields, models, _, tools, api, SUPERUSER_ID
from odoo.api import Environment
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval
import odoo.addons.decimal_precision as dp

import json
import time
from datetime import datetime, timedelta
import traceback
import threading
from xml.dom.minidom import Document
import requests
import pytz
from pytz import timezone
import psycopg2

import uuid

import logging
_logger = logging.getLogger(__name__)

ROUTE_IMPORT_CREATE_OBJECTS = {
    'created_product_ids': {
        'object': 'product.product',
        'name': _('Product')
    },
    'created_partner_ids': {
        'object': 'res.partner',
        'name': _('Customer')
    },
    'created_possid_ids': {
        'object': 'res.partner',
        'name': _('POSSID')
    },
    'created_sale_ids': {
        'object': 'sale.order',
        'name': _('Sale order')
    },
    'created_sale_line_ids': {
        'object': 'sale.order.line',
        'name': _('Sale Order Line')
    },
    'created_invoice_ids': {
        'object': 'account.invoice',
        'name': _('Invoice')
    },
    'created_invoice_line_ids': {
        'object': 'account.invoice.line',
        'name': _('Invoice Line')
    },
    'created_route_ids': {
        'object': 'stock.route',
        'name': _('Route')
    },
    'created_driver_ids': {
        'object': 'stock.location',
        'name': _('Driver')
    },
    'created_package_ids': {
        'object': 'stock.package',
        'name': _('Package')
    },
    'created_package_lines_ids': {
        'object': 'stock.package.line',
        'name': _('Package Line')
    },
    'created_owner_ids': {
        'object': 'product.owner',
        'name': _('Owner')
    },
}

ROUTE_IMPORT_UPDATE_OBJECTS = {
    'updated_product_ids': {
        'object': 'product.product',
        'name': _('Product')
    },
    'updated_owner_ids': {
        'object': 'product.owner',
        'name': _('Owner')
    },
    'updated_partner_ids': {
        'object': 'res.partner',
        'name': _('Customer')
    },
    'updated_possid_ids': {
        'object': 'res.partner',
        'name': _('POSSID')
    },
    'updated_sale_ids': {
        'object': 'sale.order',
        'name': _('Sale order')
    },
    'updated_sale_line_ids': {
        'object': 'sale.order.line',
        'name': _('Sale Order Line')
    },
    'updated_invoice_ids': {
        'object': 'account.invoice',
        'name': _('Invoice')
    },
    'updated_invoice_line_ids': {
        'object': 'account.invoice.line',
        'name': _('Invoice Line')
    },
    'updated_route_ids': {
        'object': 'stock.route',
        'name': _('Route')
    },
    'updated_driver_ids': {
        'object': 'stock.location',
        'name': _('Driver')
    },
    'updated_package_ids': {
        'object': 'stock.package',
        'name': _('Package')
    },
    'updated_package_lines_ids': {
        'object': 'stock.package.line',
        'name': _('Package Line')
    },
}                         

ROUTE_STATES = {
    'draft' : _('Still in the warehouse'), 
    'released': _('Route started'),
    'closed': _('Closed')
}

SANITEX_OWNER_ID = 'SNX'
DEFAULT_PACKAGE_DOCUMENT_TYPE = 'invoice'
DRIVER_WAREHOUSE = 'DRIVERS'
PACKAGE_CONTANER_UPDATE_FIELDS = [
    'sender_id', 'delivery_date', 'buyer_id', 
    'buyer_address_id', 'internal_order_number', 'planned_collection',
    'buyer_name', 'buyer_posid', 'sender_name', 'sender_posid', 'owner_id',
    'picking_warehouse_id'
]

SETTINGS_FOR_IMPORT_SKIPPING = {}

SKIP_IMPORT_BY_DATE = {
    'CreateOrder': 'shiping_date',
    'CreateRoute': 'date',
    'CreateInvoice': 'invoice_date',
    'CreatePackage': 'delivery_date',
    'create_packing': False,
    'quantity_by_customer': False,
    'CreateClient': False,
    'CreatePOSID': False,
    'CreateOwner': False,
    'IVAZexport': False,
    'TareDocumentExport': False,
    'CreateSupplierInvoice': False,
}

SKIP_IMPORT_AFTER_DAYS = {}

GROUP_TO_SEE_ALL_WAREHOUSES = 'stock.group_stock_manager'

def utc_str_to_local_str(utc_str=None, date_format='%Y-%m-%d %H:%M:%S', timezone_name='Europe/Vilnius'):
    if not utc_str:
        utc_str = time.strftime(date_format)
    utc_datetime = datetime.strptime(utc_str, date_format).replace(tzinfo=pytz.utc).astimezone(timezone(timezone_name))
    return utc_datetime.strftime(date_format)


def str_date_to_timestamp(date_string=None, date_format='%Y-%m-%d %H:%M:%S.%f'):
    if not date_string:
        return datetime.now().timestamp()
    datetime_date = datetime.strptime(date_string, date_format)
    return datetime_date.timestamp()

def get_local_time_timestamp():
    return datetime.now().replace(tzinfo=pytz.utc).astimezone(timezone('Europe/Vilnius')).timestamp()

def date_to_iso_format(str_date=None, date_date=None, date_format='%Y-%m-%d %H:%M:%S', timezone_name='Europe/Vilnius'):
    if not date_date:
        if not str_date:
            str_date = time.strftime(date_format)
        if timezone_name:
            date_date = datetime.strptime(str_date, date_format).replace(tzinfo=pytz.utc).astimezone(timezone(timezone_name))
        else:
            date_date = datetime.strptime(str_date, date_format)
    result_string = date_date.strftime('%Y-%m-%dT%H:%M:%S')
    result_string += '.' + date_date.strftime('%f')[:3]
    result_string += date_date.strftime('%z')[:3] + ':' + date_date.strftime('%z')[-2:]
    return result_string

def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


class StockRouteNumber(models.Model):
    _name = 'stock.route.number'
    
    name = fields.Char("Name", size=128, required=True)
    id = fields.Integer('ID', readonly=False)
    external_route_id = fields.Char('External Route ID', size=128, readonly=True)
    license_plate = fields.Char('License Plate', readonly=True, size=32)
    driver = fields.Char('Driver', readonly=True, size=64)
    date = fields.Date('Date', readonly=True)
    weight = fields.Float('Weight', digits=dp.get_precision('Stock Weight'))
    distance = fields.Integer('Distance', readonly=True)
    intermediate_id = fields.Many2one(
        'stock.route.integration.intermediate', 'Created by', readonly=True, index=True
    )
    source = fields.Char('Source', readonly=True, size=64)
    estimated_start = fields.Datetime('Estimated Start')
    estimated_finish = fields.Datetime('Estimated Finish')

    @api.multi
    def get_qty_cancelled(self):
        user = self.env['res.users'].browse(self.env.uid)
        wh_ids = user.get_current_warehouses().mapped('id')
        if not wh_ids:
            return 0
        sql = '''
            SELECT
                count(distinct(external_sale_order_id))
            FROM
                sale_order
            WHERE
                route_number_id = %s
                AND ((
                        warehouse_id in %s
                        AND route_id is null
                        AND previous_task_received = True
                        AND state = 'cancel'
                    )
                    OR 
                    (
                        shipping_warehouse_id in %s
                        AND warehouse_id not in %s
                        AND route_state_received = False
                        AND state = 'cancel'
                    )
                )
        '''
        self.env.cr.execute(sql, (self.id, tuple(wh_ids), tuple(wh_ids), tuple(wh_ids)))
        return self.env.cr.fetchall()[0][0]

    @api.model
    def create_if_not_exists(self, vals):
        if vals.get('external_route_id', False):
            self.env.cr.execute('''
                SELECT
                    id
                FROM
                    stock_route_number
                WHERE
                    name = %s
                    AND external_route_id = %s
            ''', (vals['name'], vals['external_route_id']))
            results = self.env.cr.fetchall()
            if results:
                return self.browse(results[0][0])
        return self.create(vals)


    @api.multi
    def get_all_sale_ids(self):
        sql = '''
            SELECT
                id
            FROM
                sale_order
            WHERE
                route_number_id = %s
        '''
        self.env.cr.execute(sql, (self.id,))
        return self.env['sale.order'].browse([sale_res[0] for sale_res in self.env.cr.fetchall()])

    @api.model
    def append_number(self, name):
        if not self.search([('name','=',name)]):
            self.create({'name': name})
        return True

    @api.multi
    def create_route_template(self):
        template_env = self.env['stock.route.template']
        for number in self:
            template = template_env.with_context(
                search_by_user=False,
                get_current_routes=False
            ).search([
                ('route_no_id','=',number.id)
            ], limit=1)
            if not template:
                template = template_env.create_route_template(number)
            context = self.env.context or {}
            template.with_context(context).update_picking_warehouse_id_filter()
            template.with_context(context).update_shipping_warehouse_id_filter()
            # templates.update_template()

    # qty_planned = self.route_no_id.get_total_planned_tasks()
    # qty_in_warehouse = self.route_no_id.get_in_warehouse_tasks()
    # qty_in_route = self.route_no_id.get_in_route_tasks()
    # qty_not_received = self.route_no_id.get_total_not_received_tasks()


    @api.multi
    def get_in_warehouse_tasks(self):
        user = self.env['res.users'].browse(self.env.uid)
        wh_ids = user.get_current_warehouses().mapped('id')
        if not wh_ids:
            return 0
        sql = '''
            SELECT
                count(id)
            FROM
                sale_order
            WHERE
                route_number_id = %s
                AND warehouse_id in %s
                AND route_id is null
                AND previous_task_received = True
                AND has_related_document = True
        '''
        self.env.cr.execute(sql, (self.id, tuple(wh_ids)))
        return self.env.cr.fetchall()[0][0]
    
    @api.multi
    def get_in_warehouse_tasks_weight(self):
        user = self.env['res.users'].browse(self.env.uid)
        wh_ids = user.get_current_warehouses().mapped('id')
        if not wh_ids:
            return 0
        sql = '''
            SELECT
                sum(total_weight)
            FROM
                sale_order
            WHERE
                route_number_id = %s
                AND warehouse_id in %s
                AND route_id is null
                AND previous_task_received = True
                AND has_related_document = True
        '''
        self.env.cr.execute(sql, (self.id, tuple(wh_ids)))
        return self.env.cr.fetchall()[0][0]

    @api.multi
    def get_in_route_tasks(self):
        user = self.env['res.users'].browse(self.env.uid)
        wh_ids = user.get_current_warehouses().mapped('id')
        if not wh_ids:
            return 0
        sql = '''
            SELECT
                count(distinct(external_sale_order_id))
            FROM
                sale_order
            WHERE
                route_number_id = %s
                AND warehouse_id in %s
                AND (shipping_warehouse_id not in %s 
                    OR warehouse_id = shipping_warehouse_id)
                AND route_id is not null
        '''
        self.env.cr.execute(sql, (self.id, tuple(wh_ids), tuple(wh_ids)))
        return self.env.cr.fetchall()[0][0]

    @api.multi
    def get_tasks_in_route(self):
        user = self.env['res.users'].browse(self.env.uid)
        wh_ids = user.get_current_warehouses().mapped('id')
        if not wh_ids:
            return self.env['sale.order'].browse([])
        sql = '''
            SELECT
                id
            FROM
                sale_order
            WHERE
                route_number_id = %s
                AND warehouse_id in %s
                AND (shipping_warehouse_id not in %s 
                    OR warehouse_id = shipping_warehouse_id)
                AND route_id is not null
        '''
        self.env.cr.execute(sql, (self.id, tuple(wh_ids), tuple(wh_ids)))
        return self.env['sale.order'].browse([sale_res[0] for sale_res in self.env.cr.fetchall()])


    @api.multi
    def get_in_released_route_tasks(self):
        user = self.env['res.users'].browse(self.env.uid)
        wh_ids = user.get_current_warehouses().mapped('id')
        if not wh_ids:
            return 0
        sql = '''
            SELECT
                count(distinct(external_sale_order_id))
            FROM
                sale_order so
                left join stock_route sr on (sr.id = so.route_id)
            WHERE
                so.route_number_id = %s
                AND so.warehouse_id in %s
                AND so.route_id is not null
                AND sr.state in ('released', 'closed')
        '''
        self.env.cr.execute(sql, (self.id, tuple(wh_ids)))
        return self.env.cr.fetchall()[0][0]

    @api.multi
    def get_total_not_received_tasks(self):
        user = self.env['res.users'].browse(self.env.uid)
        wh_ids = user.get_current_warehouses().mapped('id')
        if not wh_ids:
            return 0
        sql = '''
            SELECT
                count(distinct(external_sale_order_id))
            FROM
                sale_order
            WHERE
                route_number_id = %s
                AND ((
                        shipping_warehouse_id in %s
                        AND warehouse_id not in %s
                        AND route_state_received = False
                        AND state != 'cancel'
                    )
                    OR 
                    (
                        warehouse_id in %s
                        AND route_id is null
                        AND previous_task_received = True
                        AND has_related_document = False
                        AND state != 'cancel'
                    )
                )
        '''
        self.env.cr.execute(sql, (self.id, tuple(wh_ids), tuple(wh_ids), tuple(wh_ids)))
        return self.env.cr.fetchall()[0][0]

    @api.multi
    def get_total_planned_tasks(self):
        user = self.env['res.users'].browse(self.env.uid)
        wh_ids = user.get_current_warehouses().mapped('id')
        if not wh_ids:
            return 0
        sql = '''
            SELECT
                count(distinct(external_sale_order_id))
            FROM
                sale_order
            WHERE
                route_number_id = %s
                AND (warehouse_id in %s
                OR shipping_warehouse_id in %s)
        '''
        self.env.cr.execute(sql, (self.id, tuple(wh_ids), tuple(wh_ids)))
        return self.env.cr.fetchall()[0][0]

    @api.model
    def get_if_fully_released(self, planned=None, cancelled=None):
        released = self.get_in_released_route_tasks()
        if planned is None:
            planned = self.get_total_planned_tasks()
        if cancelled is None:
            cancelled = self.get_qty_cancelled()
        if released + cancelled == planned:
            return True
        else:
            return False

    @api.multi
    def action_open_sales(self):
        sale_action = self.env.ref('config_sanitex_delivery.action_sanitex_all_sales_menu').read({})[0]
        sale_action['domain'] = [('route_number_id','=',self.id)]

        return sale_action
        
    @api.multi
    def get_task_to_put_in_route(self):
        user = self.env['res.users'].browse(self.env.uid)
        wh_ids = user.get_current_warehouses().mapped('id')
        if not wh_ids:
            return 0
        sql = '''
            SELECT
                id
            FROM
                sale_order
            WHERE
                route_number_id = %s
                AND warehouse_id in %s
                AND route_id is null
                AND previous_task_received = True
                AND has_related_document = True
        '''
        self.env.cr.execute(sql, (self.id, tuple(wh_ids)))
        res = self.env['sale.order'].browse([sql_res[0] for sql_res in self.env.cr.fetchall()])
        return res

class StockRouteIntegrationIntermediateLock(models.Model):
    _name = 'stock.route.integration.intermediate.lock'
    _description = 'Intermediate table Lock for importing routes'

    intermediate_id = fields.Many2one('stock.route.integration.intermediate', 'Intermediate',
        ondelete='cascade'
    )

    _sql_constraints = [
        ('intermediate_uniq', 'unique (intermediate_id)', 'Lock should be unique per intermediate!'),
    ]

class StockRouteIntegrationIntermediate(models.Model):
    _name = 'stock.route.integration.intermediate'
    _description = 'Intermediate table for importing routes'
    
    @api.model
    def get_selection_values(self):
        pod_integration_env = self.env['pod.integration']
        iceberg_integration_env = self.env['iceberg.integration']
        return [
            ('CreateOrder','CreateOrder'),
            ('CreateRoute','CreateRoute'),
            ('CreateInvoice','CreateInvoice'),
            ('CreatePackage','CreatePackage'),
            ('create_packing','create_packing'),
            ('quantity_by_customer','quantity_by_customer'),
            ('CreateClient','CreateClient'),
            ('CreatePartner','CreatePartner'),
            ('CreatePOSID','CreatePOSID'),
            ('CreateOwner','CreateOwner'),
            ('IVAZexport','IVAZexport'),
            ('TareDocumentExport','TareDocumentExport'),
            ('CreateSupplierInvoice','CreateSupplierInvoice'),
            ('RESTRoutesByVersion','RESTRoutesByVersion'),
            ('RESTOdooStatus','RESTOdooStatus'),
            ('OrderExternalPackets','OrderExternalPackets'),
            ('CreateDOSLocation','CreateDOSLocation'),
        ] + pod_integration_env.get_pod_integration_function_selection()\
        + iceberg_integration_env.get_iceberg_integration_function_selection()

    lock_id = fields.Integer('Intermediate')
    # lock_id = fields.Many2one('stock.route.integration.intermediate.lock', 'Intermediate')
    datetime = fields.Datetime('Created')
    received_values = fields.Text('Received Values', readonly=True)
    received_values_show = fields.Text('Received Values', readonly=True)
    processed = fields.Boolean('Processed', readonly=True, default=False)
    function = fields.Selection(get_selection_values, 'Function', readonly=False)
    return_results = fields.Text('Results', readonly=True)
    created_product_ids = fields.One2many('product.product', 'intermediate_id', 'Products', readonly=True)
    created_partner_ids = fields.One2many('res.partner', 'intermediate_id', 'Partners/addresses', readonly=True)
    created_sale_ids = fields.One2many('sale.order', 'intermediate_id', 'Sales', readonly=True)
    created_invoice_ids = fields.One2many('account.invoice', 'intermediate_id', 'Invoices', readonly=True)
    created_route_ids = fields.One2many('stock.route', 'intermediate_id', 'Routes', readonly=True)
    created_package_ids = fields.One2many('stock.package', 'intermediate_id', 'Packages', readonly=True)
    created_customer_stocks = fields.One2many(
        'sanitex.product.partner.stock', 'intermediate_id', 'Created Customer Stocks'
    )
    traceback_string = fields.Text('Traceback', readonly=False)
    updated_product_ids = fields.Many2many(
        'product.product', 'intermediate_updated_product_rel', 
        'intermediate_id', 'product_id', 'Products', readonly=True
    )
    updated_partner_ids = fields.Many2many(
        'res.partner', 'intermediate_updated_partner_rel', 
        'intermediate_id', 'product_id', 'Partners/POSSID', readonly=True
    )
    updated_sale_ids = fields.Many2many(
        'sale.order', 'intermediate_updated_sale_rel', 
        'intermediate_id', 'product_id', 'Sales', readonly=False
    )
    updated_invoice_ids = fields.Many2many(
        'account.invoice', 'intermediate_updated_invoice_rel', 
        'intermediate_id', 'product_id', 'Invoices', readonly=True
    )
    updated_route_ids = fields.Many2many(
        'stock.route', 'intermediate_updated_route_rel', 
        'intermediate_id', 'product_id', 'Routes', readonly=True
    )
    updated_package_ids = fields.Many2many(
        'stock.package', 'intermediate_updated_package_rel', 
        'intermediate_id', 'package_id', 'Packages', readonly=True
    )
    updated_customer_stocks = fields.Many2many(
        'sanitex.product.partner.stock', 'intermediate_updated_stocks_rel',
        'log_id', 'stock_id', 'Updated Customer Stocks'
    )
    route_to_ivaz_id = fields.Many2one('stock.route', 'Route to IVAZ', readonly=True)
    start_time = fields.Datetime('Start Time', readonly=True)
    end_time = fields.Datetime('End Time', readonly=True)
    duration = fields.Integer('Duration', readonly=True,
        help='The time(in seconds) during which the object was created since import object started to process'
    )
    duration2 = fields.Integer('Duration2', readonly=True,
        help='The time(in minutes) during which the object was created since import object was created'
    )

    repeat = fields.Integer('Repeat', readonly=True, default=0)
    tare_document_id = fields.Char('Tare Document ID', size=64, readonly=True)
    tare_document_source = fields.Char('Tare Document Source', size=64, readonly=True)
    count = fields.Integer('Count', readonly=True, default=0)
    skip = fields.Boolean('Skip', readonly=True, default=False)

    original_id =fields.Integer('ID in BLS server', readonly=True, help='Used for syncing from BLS server, testing')

#     reported = fields.Boolean("Reported", readonly=True, default=False)
    process_time_checked = fields.Boolean("Process Time Checked", readonly=True, default=False)
    next_process_at = fields.Datetime('Next Process At', readonly=True)
    next_process_in = fields.Integer('Next Process In', readonly=True, default=0)

    _rec_name = 'datetime'
    _order = 'datetime DESC'

    @api.model
    def cron_put_back_in_queue(self):
        _logger.info('Returning to queue skipped intermediates.')
        search_for_skipped_sql = '''
            UPDATE
                stock_route_integration_intermediate
            SET
                skip=False
            WHERE
                skip=True
                AND processed=False
                AND next_process_at < %s
                AND next_process_in <= 4230
            RETURNING
                id
        '''
        search_for_skipped_where = (time.strftime('%Y-%m-%d %H:%M:%S'),)
        self.env.cr.execute(search_for_skipped_sql, search_for_skipped_where)
        edited_intermediates = self.env.cr.fetchall()
        _logger.info('Returned %s intermediate objects to queue.' % str(len(edited_intermediates)))


    @api.model
    def update_skip_import_values(self):
        global SKIP_IMPORT_AFTER_DAYS
        company = self.env['res.users'].browse(self.env.uid).company_id
        SKIP_IMPORT_AFTER_DAYS.update({
            'CreateOrder': company.delete_transportation_tasks_after,
            'CreateRoute': company.delete_routes_after,
            'CreateInvoice': company.delete_invoices_after,
            'CreatePackage': company.delete_packages_after,
        })
    
    @api.multi
    def do_skip_import(self, import_vals):
        intermediate_function = self.read(['function'])[0]['function']
        skip = False
        date_field = SKIP_IMPORT_BY_DATE.get(intermediate_function, False)
        if date_field and import_vals.get(date_field, False):
            day_count = SKIP_IMPORT_AFTER_DAYS.get(intermediate_function, -1)
            if day_count < 0:
                self.update_skip_import_values()
                day_count = SKIP_IMPORT_AFTER_DAYS.get(intermediate_function, -1)
                if day_count < 0:
                    # TODO: mesti į logą
                    raise UserError('NĖRA DIENŲ')
            date_to_skip = (datetime.now() - timedelta(days=day_count)).strftime('%Y-%m-%d')
            if date_to_skip > import_vals[date_field]:
                skip = _('Objet you trying to import is too old.')

        return skip

    @api.model
    def do_skip_import_by_timestamp(self, timestamp, table, external_id_field, external_id):
        sql = '''
            SELECT
                id
            FROM
                ''' + table + '''
            WHERE
                ''' + external_id_field + ''' = %s
                AND import_timestamp > %s
        '''
        self.env.cr.execute(sql, (external_id, timestamp))
        results = self.env.cr.fetchall()
        if results:
            skip = True
        else:
            skip = False
        return skip
        
    @api.model
    def sync_from_bls_server(self):
        # naudojama testavimui
        import xmlrpc
        protocol = 'http'
        host = 'localhost'
        port = 4869
        if self.env.cr.dbname == 'backup_11_bls_lv_180528':
            port = 8880
        if self.env.cr.dbname == 'backup_11_bls_180803':
            port = 4269
        dbname = 'bls'
        uid = 1
        user_pw = 'Vudsadeim1'
        objects = {
            'CreateOrder': 'sale.order',
            'CreateRoute': 'stock.route',
            'OrderExternalPackets': 'stock.route',
            'CreateInvoice': 'account.invoice',
            'CreatePackage': 'stock.package',
            'create_packing': 'product.product',
            'quantity_by_customer': 'product.product',
            'CreateClient': 'res.partner',
            'CreatePOSID': 'res.partner',
            'CreateOwner': 'product.owner',
        }

        rpc_object_from = xmlrpc.client.ServerProxy('%s://%s:%s/xmlrpc/object' % (
            protocol, host, port
        ))
        self.env.cr.execute('select max(original_id) from stock_route_integration_intermediate')
        res = self.env.cr.fetchall()
        if res[0] and res[0][0]:
            domain = [('id','>', res[0][0])]
        else:
            domain = [('id','>',1703985)]
        domain.append(('function','in',[
            'CreateTransportationOrder', 'CreateDespatchAdvice', 'CreateOrder',
            'CreateRoute','CreateRoute',
            'CreateInvoice','CreateInvoice',
            'CreatePackage','CreatePackage',
            'create_packing','create_packing',
            'quantity_by_customer','quantity_by_customer',
            'CreateClient','CreateClient',
            'CreatePartner','CreatePartner',
            'CreatePOSID','CreatePOSID',
            'CreateOwner','CreateOwner',
            'OrderExternalPackets','OrderExternalPackets'
        ]))
        # domain = ['|',('function','=','CreateOwner')] + domain
        _logger.info('Importing intermediates %s://%s:%s/xmlrpc/object' % (protocol, host, port))
        _logger.info('Importing intermediates %s' % str(domain))
        ids = rpc_object_from.execute(
            dbname, uid, user_pw,
	        'stock.route.integration.intermediate', 'search', domain, 0, False, 'id'
        )
        _logger.info('Found %s intermediates to import' % str(len(ids)))
        list_of_list_of_ids = chunks(ids, 100)
        for list_of_ids in list_of_list_of_ids:
            res_reads = rpc_object_from.execute(dbname, uid, user_pw, 'stock.route.integration.intermediate', 'read',
                                               list_of_ids, ['function', 'received_values'])
            for res_read in res_reads:
                id = res_read['id']
                if self.search([('original_id','=',id)]):
                    continue
                if res_read['function'] in ['CreateTransportationOrder', 'CreateDespatchAdvice']:
                    self.create({
                        'function': res_read['function'],
                        'received_values': res_read['received_values'],
                        'original_id': id,
                        'datetime': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
                if res_read['function'] not in objects.keys():
                    continue
                if port == 4269 and res_read['function'] in ['CreateInvoice']:
                    continue

                val_str = res_read['received_values']
                vals = json.loads(val_str)
                if res_read['function'] == 'CreateRoute':
                    for val in vals:
                        for ord_dict in val.get('orders', []):
                            if ord_dict.get('external_packet_ids', False):
                                del ord_dict['external_packet_ids']
                new_id = getattr(self.env[objects[res_read['function']]], res_read['function'])(vals)
                if isinstance(new_id, int):
                    self.browse(new_id).write({'original_id': id})
                else:
                    break
            self.env.cr.commit()

    @api.model_cr
    def init(self):
        cr = self.env.cr
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('intermediate_updated_product_rel_intermediate_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX intermediate_updated_product_rel_intermediate_id_index ON intermediate_updated_product_rel (intermediate_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('intermediate_updated_partner_rel_intermediate_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX intermediate_updated_partner_rel_intermediate_id_index ON intermediate_updated_partner_rel (intermediate_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('intermediate_updated_sale_rel_intermediate_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX intermediate_updated_sale_rel_intermediate_id_index ON intermediate_updated_sale_rel (intermediate_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('intermediate_updated_invoice_rel_intermediate_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX intermediate_updated_invoice_rel_intermediate_id_index ON intermediate_updated_invoice_rel (intermediate_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('intermediate_updated_route_rel_intermediate_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX intermediate_updated_route_rel_intermediate_id_index ON intermediate_updated_route_rel (intermediate_id)')    
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('intermediate_updated_package_rel_intermediate_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX intermediate_updated_package_rel_intermediate_id_index ON intermediate_updated_package_rel (intermediate_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('intermediate_updated_stocks_rel_intermediate_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX intermediate_updated_stocks_rel_intermediate_id_index ON intermediate_updated_stocks_rel (log_id)')
     
            
    
    @api.multi
    def get_objects(self, created=True, updated=True, model='all'):
        objects = {
            'product.product' : [],
            'res.partner' : [],
            'sale.order' : [],
            'sale.order.line' : [],
            'account.invoice' : [],
            'account.invoice.line' : [],
            'stock.route' : [],
            'stock.location' : [],
            'stock.package' : [],
            'stock.package.document' : [],
            'account.invoice.container' : [],
            'sanitex.product.partner.stock' : [],
        }
        for intermediate in self:
            if model in ['all', 'product.product'] and intermediate.function in ['CreateOrder', 'CreateInvoice', 'create_packing', 'quantity_by_customer']:
                if created and intermediate.created_product_ids:
                    objects['product.product'] += intermediate.created_product_ids.mapped('id')
                if updated and intermediate.updated_product_ids:
                    objects['product.product'] += intermediate.updated_product_ids.mapped('id')
                    
            if model in ['all', 'res.partner'] and intermediate.function in ['CreateClient','CreatePOSID']:
                if created and intermediate.created_partner_ids:
                    objects['res.partner'] += intermediate.created_partner_ids.mapped('id')
                if updated and intermediate.updated_partner_ids:
                    objects['res.partner'] += intermediate.updated_partner_ids.mapped('id')
                    
            if model in ['all', 'sale.order'] and intermediate.function in ['CreateOrder']:
                if created and intermediate.created_sale_ids:
                    objects['sale.order'] += intermediate.created_sale_ids.mapped('id')
                if updated and intermediate.updated_sale_ids:
                    objects['sale.order'] += intermediate.updated_sale_ids.mapped('id')
                    
            if model in ['all', 'account.invoice'] and intermediate.function in ['CreateInvoice']:
                if created and intermediate.created_invoice_ids:
                    objects['account.invoice'] += intermediate.created_invoice_ids.mapped('id')
                if updated and intermediate.updated_invoice_ids:
                    objects['account.invoice'] += intermediate.updated_invoice_ids.mapped('id')
                    
            if model in ['all', 'stock.route'] and intermediate.function in ['CreateRoute']:
                if created and intermediate.created_route_ids:
                    objects['stock.route'] += intermediate.created_route_ids.mapped('id')
                if updated and intermediate.updated_route_ids:
                    objects['stock.route'] += intermediate.updated_route_ids.mapped('id')
                    
            if model in ['all', 'stock.package'] and intermediate.function in ['CreatePackage']:
                if created and intermediate.created_package_ids:
                    objects['stock.package'] += intermediate.created_package_ids.mapped('id')
                if updated and intermediate.updated_package_ids:
                    objects['stock.package'] += intermediate.updated_package_ids.mapped('id')
                    
            if model in ['all', 'sanitex.product.partner.stock'] and intermediate.function in ['quantity_by_customer']:
                if created and intermediate.created_customer_stocks:
                    objects['sanitex.product.partner.stock'] += intermediate.created_customer_stocks.mapped('id')
                if updated and intermediate.updated_customer_stocks:
                    objects['sanitex.product.partner.stock'] += intermediate.updated_customer_stocks.mapped('id')
                    
        for key in list(objects.keys()):
            if not objects[key]:
                del objects[key]
        return objects
    
    @api.model
    def show_open(self, object, ids):
        view_external_ids = {
            'product.product' : 'config_sanitex_delivery.action_sanitex_product_menu',
            'res.partner' : 'config_sanitex_delivery.action_sanitex_partner_menu',
            'sale.order' : 'config_sanitex_delivery.action_sanitex_sales_menu',
            'account.invoice' : 'account.action_invoice_tree1',
            'stock.route' : 'config_sanitex_delivery.action_stock_routes',
            'stock.package' : 'config_sanitex_delivery.action_stock_package',
            'sanitex.product.partner.stock' : 'config_sanitex_delivery.action_sanitex_product_partner_stock',
        }
        
        action = self.env.ref(view_external_ids[object])
        view = action.read()[0]
        view['domain'] = [('id','in',ids)]
        view['context'] = {}
        return view
    
    @api.multi
    def open_related_objects(self):
        objects = self.get_objects()
        if len(objects.keys()) == 0:
            raise UserError(_('No objects were created'))
        elif len(objects.keys()) == 1:
            key = list(objects.keys())[0]
            return self.env['stock.route.integration.intermediate'].show_open(
                key, objects[key]
            )
        else:
            context = self.env.context or {}
            ctx = context.copy()
            ctx['objects'] = objects.keys()
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'integration.open_objects.osv',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': ctx,
                'nodestroy': True,
            }
    
    @api.model
    def cron_remove_old_objects(self):
        company = self.env['res.users'].browse(self.env.uid).company_id
        days_after = company.unlinkt_old_objects_after_days
        context = self.env.context or {}
        ctx = context.copy()
        ctx['allow_to_delete_integration_obj'] = True
        _logger.info('Removing old Intermediate objects (%s days old)' % str(days_after)) 
        today = datetime.now()
        delete_until = (today - timedelta(days=days_after)).strftime('%Y-%m-%d %H:%M:%S')
        old_intermediate_objects = self.search([
            ('processed','=',True),
            ('datetime','<=',delete_until)
        ], limit=20)
        
        while old_intermediate_objects:
            _logger.info('Deleting %s' % str(old_intermediate_objects.mapped('id'))) 
            old_intermediate_objects.with_context(ctx).unlink()
            self.env.cr.commit()
            old_intermediate_objects = self.search([
                ('processed','=',True),
                ('datetime','<=',delete_until)
            ], limit=20)
            
    @api.model
    def do_not_update_vals(self, object=''):
        return True 

    @api.model
    def get_allowed_selection_values(self, model, code_field):
        values = []
        model_obj = self.env[model]
        models = model_obj.search([])
        for model in models:
            model_rec = model.read([code_field])
            if isinstance(model_rec, list):
                model_rec = model_rec[0]
            if model_rec[code_field] not in values:
                values.append(model_rec[code_field])
        return values
            
    @api.model
    def check_selection_values(self, field, value, all_values):
        result = ''
        if value not in all_values:
            result = _('Given value \'%s\' for field \'%s\' doesn\'t match any of allowed values(%s)') %(value, field, ', '.join(all_values))
        return result

    @api.model
    def check_import_values(self, list_of_dict, keys_to_check, result={}, prefix=''):
        i = 0
        if prefix:
            prefix += ' '
        for dict_vals in list_of_dict:
            i = i + 1
            for field in keys_to_check:
                if field not in dict_vals.keys():
                    msg = _('You have to fill in value: %s') % field
                    index = prefix + str(i)
                    if index in result.keys():
                        result[index].append(msg)
                    else:
                        result[index] = [msg]
        return True

    @api.model
    def remove_same_values(self, record, vals):
        object_read = record.read(vals.keys())[0]
        for field in list(vals.keys())[:]:
            if field in object_read.keys():
                #many2one
                if isinstance(object_read[field], tuple):
                # if type(object_read[field]) == type(()):
                    if vals[field] == object_read[field][0]:
                        del vals[field]
                #many2many
                elif isinstance(object_read[field], list):
                # elif type(object_read[field]) == type([]):
                    if not vals[field]:
                        if not object_read[field]:
                            del vals[field]
                    elif vals[field][0] and vals[field][0][0] == 6:
                        if vals[field][0][2] == object_read[field]:
                            del vals[field]
                    else:
                        for add_item in vals[field][:]:
                            if add_item[0] == 4:
                                if object_read[field] and add_item[1] in object_read[field]:
                                    vals[field].remove(add_item)
                                    if not vals[field]:
                                        del vals[field]
                #float
                elif isinstance(object_read[field], float):
                # elif type(object_read[field]) == type(1.1):
                    if isinstance(vals[field], type(object_read[field])):
                    # if type(vals[field]) != type(object_read[field]):
                        try:
                            vals[field] = float(vals[field])
                        except:
                            pass
                    round_number = max(len(str(object_read[field]+1.0).split('.')[1]), len(str(vals[field]+1.0).split('.')[1]))
                    if field == 'weight':
                        round_number = 4
                    if round(vals[field], round_number) == round(object_read[field], round_number):
                        del vals[field]
                #other
                elif vals[field] == object_read[field]:
                    del vals[field]
        return True

    @api.multi
    def process(self):
        for intermediate in self:
            intermediate.process_intermediate_object()
        return True

    @api.model
    def check_order_vals(self, dict_vals):
        if 'external_customer_id' in dict_vals.keys() and 'externalcustomer_id' not in dict_vals.keys():
            dict_vals['externalcustomer_id'] = dict_vals['external_customer_id']
        if 'externalcustomer_id' in dict_vals.keys() and 'external_customer_id' not in dict_vals.keys():
            dict_vals['external_customer_id'] = dict_vals['externalcustomer_id']
        return True

    @api.model
    def check_invoice_vals(self, dict_vals):
        if 'external_customer_id' in dict_vals.keys() and 'externalcustomer_id' not in dict_vals.keys():
            dict_vals['externalcustomer_id'] = dict_vals['external_customer_id']
        if 'externalcustomer_id' in dict_vals.keys() and 'external_customer_id' not in dict_vals.keys():
            dict_vals['external_customer_id'] = dict_vals['externalcustomer_id']
        return True

    @api.model
    def check_route_vals(self, dict_vals):
        return True
    
    @api.multi
    def get_received_values_as_dict(self):
        # iš tarpinio objekto nuskaito gautas reikšmes.
        # Skaitoma tiesiai iš bazės nes taip naudojasi mažiau RAM'ų.
        
        self.env.cr.execute('''
            SELECT 
                received_values 
            FROM 
                stock_route_integration_intermediate 
            WHERE 
                id = %s''' % str(self.id)
        )
        str_values = self.env.cr.fetchall()[0][0]
        try:
            vals_list = json.loads(str_values)
        except:
            json_acceptable_string = str_values.replace("'", "\"")
            vals_list = json.loads(json_acceptable_string)
        return vals_list
    
    @api.multi
    def process_intermediate_object_owner(self):
        
        results = {}
        results['owners'] = []
#         str_owners = self.received_values
        
        context = self._context or {}
        commit = not context.get('no_commit', False)
        
#         try:
#             owners_vals_list = json.loads(str_owners)
#         except:
#             json_acceptable_string = str_owners.replace("'", "\"")
#             owners_vals_list = json.loads(json_acceptable_string)
        owners_vals_list = self.get_received_values_as_dict()
        processed = True
        
        ctx = context.copy()
        
        for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
            ctx[created_object_ids_name] = []
            
        for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
            ctx[updated_object_ids_name] = []
        ctx['intermediate_id'] = self.id
        
        trb = ''
        for owner_dict in owners_vals_list:
            msg = ''
            
            result = {}
            result['owner'] = owner_dict['external_owner_id']
            result['created_objects'] = []
            result['result'] = _('Owner was created successfully')
            result['error'] = False
            try:
                owner_vals = {}
                
                owner_vals['product_owner_external_id'] = owner_dict['external_owner_id']
                if 'owner_code' in owner_dict.keys():
                    owner_vals['owner_code'] = owner_dict['owner_code']
                if 'name' in owner_dict.keys():
                    owner_vals['name'] = owner_dict['name']
                if 'ref' in owner_dict.keys():
                    owner_vals['ref'] = owner_dict['ref']
                if 'lang' in owner_dict.keys():
                    owner_vals['lang'] = owner_dict['lang']
                if 'vat' in owner_dict.keys():
                    owner_vals['vat'] = owner_dict['vat']
                if 'waybilldeclaredatefrom' in owner_dict.keys():
                    owner_vals['waybill_declare_date_from'] = owner_dict['waybilldeclaredatefrom']
                if 'waybilldeclare' in owner_dict.keys():
                    if owner_dict['waybilldeclare'] == 'Y':
                        owner_vals['waybill_declare'] = True
                    elif owner_dict['waybilldeclare'] == 'N':
                        owner_vals['waybill_declare'] = False
                if 'active' in owner_dict.keys():
                    if owner_dict['active'] == 'Y':
                        owner_vals['active'] = True
                    elif owner_dict['active'] == 'N':
                        owner_vals['active'] = False
                if 'phone' in owner_dict.keys():
                    owner_vals['phone'] = owner_dict['phone']
                if 'regaddress' in owner_dict.keys():
                    owner_vals['reg_address'] = owner_dict['regaddress']
                if 'phone2' in owner_dict.keys():
                    owner_vals['logistics_phone'] = owner_dict['phone2']
                
                        
                if 'firm_id' in owner_dict.keys():
                    comps = self.env['res.company'].search([
                        ('company_code','=',owner_dict['firm_id'])
                    ])
                    if comps:
                        owner_vals['company_id'] = comps[0].id
                    else:
                        raise UserError(_('No Company found with code %s') %owner_dict['firm_id'])
                    
                
                self.env['product.owner'].with_context(ctx).create_owner(owner_vals)
                msg = ctx.get('owner_message', _('Success'))
            except UserError as e:
                err_note = _('Failed to create owner: %s') % (tools.ustr(e),)
                msg += err_note
                processed = False
                trb += traceback.format_exc() + '\n\n'
                result['error'] = True
                if commit:
                    self.env.cr.rollback()
            except Exception as e:
                err_note = _('Failed to create owner: %s') % (tools.ustr(e),)
                msg += err_note
                processed = False
                trb += traceback.format_exc() + '\n\n'
                result['error'] = True
                if commit:
                    self.env.cr.rollback()
            
            result['result'] = msg
            
            for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
                if ctx.get(created_object_ids_name, []):
                    result['created_objects'].append({
                        'name': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['name'],
                        'object': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['object'],
                        'created_ids': ctx[created_object_ids_name]
                    })
            for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
                ctx[created_object_ids_name] = []
#                 
#             for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
#                 ctx[updated_object_ids_name] = []
            
            
            results['owners'].append(result)
        log_vals = {
            'processed': processed,
            'return_results': str(json.dumps(results, indent=2)),
            'traceback_string': trb
        }
        updated_vals = {}
        for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
            if ctx.get(updated_object_ids_name, []):
                updated_ids = []
                for updated_tuple in ctx[updated_object_ids_name]:
                    if updated_tuple[1] not in updated_ids:
                        updated_ids.append(updated_tuple[1])
                updated_vals[updated_object_ids_name] = [(6,0,updated_ids)]
        log_vals.update(updated_vals)
        self.write(log_vals)

        return results

    @api.model
    def process_intermediate_object_client(self):
        part_obj = self.env['res.partner']
        comp_obj = self.env['res.company']
        own_lang_obj = self.env['partner.owner.language']
        own_obj = self.env['product.owner']
        
        context = self.env.context or {}
        
        results = {}
        results['clients'] = []
        client_vals_list = self.get_received_values_as_dict()
        processed = True
        
        ctx = context.copy()
        
        for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
            ctx[created_object_ids_name] = []
            
        for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
            ctx[updated_object_ids_name] = []
        ctx['intermediate_id'] = self.id
        ctx['skip_partner_check'] = True
        ctx['tracking_disable'] = True

        
        
        trb = ''
        for client_dict in client_vals_list:
            msg = ''
            result = {}
            result['client'] = client_dict.get('external_customer_id', client_dict.get('external_partner_id', False))
            result['created_objects'] = []
            result['result'] = _('Client was created successfully')
            result['error'] = False
            try:
                client_vals = {}
                
                client_vals['external_customer_id'] = client_dict.get('external_customer_id', client_dict.get('external_partner_id', False))
                if not client_vals['external_customer_id']:
                    raise UserError(_('External id is missing'))
                if 'customer_name' in client_dict.keys():
                    client_vals['name'] = client_dict['customer_name']
                if 'customer_ref' in client_dict.keys():
                    client_vals['ref'] = client_dict['customer_ref']
                if 'customer_vat' in client_dict.keys():
                    client_vals['vat'] = client_dict['customer_vat']
                if 'address' in client_dict.keys():
                    client_vals['street'] = client_dict['address']
                if 'address_country' in client_dict.keys():
                    client_vals['country'] = client_dict['address_country']
                if 'address_phone' in client_dict.keys():
                    client_vals['phone'] = client_dict['address_phone']
                if 'address_fax' in client_dict.keys():
                    client_vals['fax'] = client_dict['address_fax']
                if 'address_street' in client_dict.keys():
                    client_vals['street2'] = client_dict['address_street']
                if 'address_city' in client_dict.keys():
                    client_vals['city'] = client_dict['address_city']
                if 'address_region' in client_dict.keys():
                    client_vals['region'] = client_dict['address_region']
                if 'address_zipcode' in client_dict.keys():
                    client_vals['zip'] = client_dict['address_zipcode']
                if 'type' in client_dict.keys():
                    client_vals['sanitex_type'] = client_dict['type']
                if 'customer_active' in client_dict.keys():
                    if client_dict['customer_active'] == 'Y':
                        client_vals['active'] = True
                    elif client_dict['customer_active'] == 'N':
                        client_vals['active'] = False

                if 'partner_name' in client_dict.keys():
                    client_vals['name'] = client_dict['partner_name']
                if 'partner_ref' in client_dict.keys():
                    client_vals['ref'] = client_dict['partner_ref']
                if 'partner_vat' in client_dict.keys():
                    client_vals['vat'] = client_dict['partner_vat']
                if 'supplier_code' in client_dict.keys():
                    client_vals['supplier_code'] = client_dict['supplier_code']

                if client_dict.get('partner_type', 'customer') == 'supplier':
                    client_vals['supplier'] = True
                    client_vals['customer'] = False
                else:
                    client_vals['supplier'] = False
                    client_vals['customer'] = True
                        
                if 'company_id' in client_dict.keys():
                    comp = comp_obj.search([('company_code','=',client_dict['company_id'])], limit=1)
                    if comp:
                        client_vals['company_id'] = comp.id
                    else:
                        raise UserError(_('No Company found with code %s') %client_dict['company_id'])
                client = part_obj.with_context(ctx).create_partner(client_vals)
                owner_langs = own_lang_obj.browse([])
                for owner_lang_dict in client_dict.get('owners', []):
                    if not owner_lang_dict.get('lang', '').strip() or owner_lang_dict.get('lang', '') == ' ':
                        continue
                    owner_lang_vals = {}
                    owner_lang_vals['partner_id'] = client.id
                    
                    owner = own_obj.search([('product_owner_external_id','=',owner_lang_dict['owner_id'])], limit=1)
                    if owner:
                        owner_lang_vals['owner_id'] = owner.id
                    else:
                        raise UserError(_('No Owner found with external ID %s') %owner_lang_dict['owner_id'])

                    owner_lang_vals['lang'] = owner_lang_dict['lang'].lower()
                    owner_lang = own_lang_obj.create_if_not_exist(owner_lang_vals)
                    owner_langs += owner_lang
                owner_langs_to_delete = client.owner_lang_ids - owner_langs
                if owner_langs_to_delete:
                    owner_langs_to_delete.unlink()
        
                msg = ctx.get('clinet_message', _('Success'))
            except UserError as e:
                err_note = _('Failed to create client: %s') % (tools.ustr(e),)
                msg += err_note
                processed = False
                trb += traceback.format_exc() + '\n\n'
                result['error'] = True
                self.env.cr.rollback()
            except Exception as e:
                raise
                err_note = _('Failed to create client: %s') % (tools.ustr(e),)
                msg += err_note
                processed = False
                trb += traceback.format_exc() + '\n\n'
                result['error'] = True
                self.env.cr.rollback()
            
            result['result'] = msg
            
            for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
                if ctx.get(created_object_ids_name, []):
                    result['created_objects'].append({
                        'name': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['name'],
                        'object': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['object'],
                        'created_ids': ctx[created_object_ids_name]
                    })
            for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
                ctx[created_object_ids_name] = []
            
            
            results['clients'].append(result)
        log_vals = {
            'processed': processed,
            'return_results': str(json.dumps(results, indent=2)),
            'traceback_string': trb
        }
        updated_vals = {}
        for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
            if ctx.get(updated_object_ids_name, []):
                updated_ids = []
                for updated_tuple in ctx[updated_object_ids_name]:
                    if updated_tuple[1] not in updated_ids:
                        updated_ids.append(updated_tuple[1])
                updated_vals[updated_object_ids_name] = [(6,0,updated_ids)]
        log_vals.update(updated_vals)
        self.write(log_vals)
        return results

    @api.multi
    def process_intermediate_object_posid(self):
        part_obj = self.env['res.partner']

        context = self.env.context or {}
        
        ctx_active = context.copy()
        ctx_active['active_test'] = False
        results = {}
        results['posids'] = []
        posid_vals_list = self.get_received_values_as_dict()
        processed = True
        
        ctx = context.copy()
        
        for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
            ctx[created_object_ids_name] = []
            
        for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
            ctx[updated_object_ids_name] = []
        ctx['intermediate_id'] = self.id
        ctx['skip_partner_check'] = True
        ctx['tracking_disable'] = True

        trb = ''
        for posid_dict in posid_vals_list:
            msg = ''
            
            result = {}
            result['posid'] = posid_dict['external_buyer_address_id']
            result['created_objects'] = []
            result['result'] = _('POSID was created successfully')
            result['error'] = False
            try:
                posid_vals = {}

                posid_vals['external_customer_id'] = posid_dict['external_buyer_address_id']
                organisation = part_obj.with_context(ctx_active).search([
                    ('external_customer_id','=',posid_dict['external_customer_id'])
                ], limit=1)
                if organisation:
                    posid_vals['parent_id'] = organisation.id
                else:
                    raise UserError(_('Can\'t find client with external ID %s') % posid_dict['external_customer_id'])
                if 'buyer_address_possid_name' in posid_dict.keys():
                    posid_vals['name'] = posid_dict['buyer_address_possid_name']
                if 'buyer_address_name' in posid_dict.keys():
                    posid_vals['posid_name'] = posid_dict['buyer_address_name']
                if 'buyer_address' in posid_dict.keys():
                    posid_vals['street'] = posid_dict['buyer_address']
                if 'buyer_address_country' in posid_dict.keys():
                    posid_vals['country'] = posid_dict['buyer_address_country']
                if 'buyer_address_phone' in posid_dict.keys():
                    posid_vals['phone'] = posid_dict['buyer_address_phone']
                if 'buyer_address_fax' in posid_dict.keys():
                    posid_vals['fax'] = posid_dict['buyer_address_fax']
                if 'buyer_address_street' in posid_dict.keys():
                    posid_vals['street2'] = posid_dict['buyer_address_street']
                if 'buyer_address_city' in posid_dict.keys():
                    posid_vals['city'] = posid_dict['buyer_address_city']
                if 'buyer_address_region' in posid_dict.keys():
                    posid_vals['region'] = posid_dict['buyer_address_region']
                if 'buyer_address_zip' in posid_dict.keys():
                    posid_vals['zip'] = posid_dict['buyer_address_zip']
                if 'buyer_address_email' in posid_dict.keys():
                    posid_vals['email'] = posid_dict['buyer_address_email']
                if 'buyer_address_possid_code' in posid_dict.keys():
                    posid_vals['possid_code'] = posid_dict['buyer_address_possid_code']
                if 'buyer_address_district' in posid_dict.keys():
                    posid_vals['district'] = posid_dict['buyer_address_district']
                    
                
                if 'buyer_address_active' in posid_dict.keys():
                    if posid_dict['buyer_address_active'] == 'Y':
                        posid_vals['active'] = True
                    elif posid_dict['buyer_address_active'] == 'N':
                        posid_vals['active'] = False
                part_obj.with_context(ctx).create_partner(posid_vals, True)
                msg = ctx.get('posid_message', _('Success'))
            except UserError as e:
                err_note = _('Failed to create posid: %s') % (tools.ustr(e),)
                msg += err_note
                processed = False
                trb += traceback.format_exc() + '\n\n'
                result['error'] = True
                self.env.cr.rollback()
            except Exception as e:
                err_note = _('Failed to create posid: %s') % (tools.ustr(e),)
                msg += err_note
                processed = False
                trb += traceback.format_exc() + '\n\n'
                result['error'] = True
                self.env.cr.rollback()
            
            result['result'] = msg
            
            for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
                if ctx.get(created_object_ids_name, []):
                    result['created_objects'].append({
                        'name': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['name'],
                        'object': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['object'],
                        'created_ids': ctx[created_object_ids_name]
                    })
            for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
                ctx[created_object_ids_name] = []
            
            
            results['posids'].append(result)
        log_vals = {
            'processed': processed,
            'return_results': str(json.dumps(results, indent=2)),
            'traceback_string': trb
        }
        updated_vals = {}
        for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
            if ctx.get(updated_object_ids_name, []):
                updated_ids = []
                for updated_tuple in ctx[updated_object_ids_name]:
                    if updated_tuple[1] not in updated_ids:
                        updated_ids.append(updated_tuple[1])
                updated_vals[updated_object_ids_name] = [(6,0,updated_ids)]
        log_vals.update(updated_vals)
        self.write(log_vals)

        return results

    @api.multi
    def process_intermediate_object_package(self):
        part_obj = self.env['res.partner']
        pack_obj = self.env['stock.package']
        doc_obj = self.env['stock.package.document']
        cont_obj = self.env['account.invoice.container']
        own_obj = self.env['product.owner']
        comp_obj = self.env['res.company']
        loc_obj = self.env['stock.location']
        transport_type_obj = self.env['transport.type']
        
        context = self.env.context or {}

        results = {}
        results['packages'] = []
        
        package_vals_list = self.get_received_values_as_dict()
        processed = True

        ctx = context.copy()
        
        for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
            ctx[created_object_ids_name] = []
            
        for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
            ctx[updated_object_ids_name] = []
        ctx['intermediate_id'] = self.id

        trb = ''
        for package_dict in package_vals_list:
            msg = ''
#             trb = ''
            skip = False
            result = {}
            result['package'] = package_dict['external_packet_id']
            result['created_objects'] = []
            result['result'] = _('Package was created successfully')
            result['error'] = False
            try:
                package_vals = {}

                skip_import = self.do_skip_import(package_dict)
                if skip_import:
                    msg = skip_import
                    skip = True
                    raise UserError(_('Import object is too old to be imported'))

                package_vals['external_package_id'] = package_dict['external_packet_id']
                
                #sender
                if 'external_sender_id' in package_dict.keys():
                    sender = part_obj.search([
                        ('external_customer_id','=',package_dict['external_sender_id'])
                    ], limit=1)
                    if not sender:
                        raise UserError(_('There are no partner with external id: %s') %package_dict['external_sender_id'])
                    package_vals['sender_id'] = sender.id
                 
                #sender address
                if 'external_sender_address_id' in package_dict.keys():
                    sender_address = part_obj.search([
                        ('external_customer_address_id','=',package_dict['external_sender_address_id'])
                    ], limit=1)
                    if not sender_address:
                        raise UserError(_('There are no POSID with external id: %s') %package_dict['external_sender_address_id'])
                    
                    package_vals['sender_address_id'] = sender_address.id
                    
                #buyer
                if 'external_buyer_id' in package_dict.keys():
                    buyer = part_obj.search([
                        ('external_customer_id','=',package_dict['external_buyer_id'])
                    ], limit=1)
                    if not buyer:
                        raise UserError(_('There are no partner with external id: %s') %package_dict['external_buyer_id'])
                    package_vals['buyer_id'] = buyer.id
                 
                #buyer address
                if 'external_buyer_address_id' in package_dict.keys():
                    buyer_address = part_obj.search([
                        ('external_customer_address_id','=',package_dict['external_buyer_address_id'])
                    ], limit=1)
                    if not buyer_address:
                        raise UserError(_('There are no POSID with external id: %s') %package_dict['external_buyer_address_id'])
                    package_vals['buyer_address_id'] = buyer_address.id
                
                
                if 'packet_date' in package_dict.keys():
                    package_vals['packet_date'] = package_dict['packet_date']
                if 'orignal_packet_number' in package_dict.keys():
                    package_vals['orignal_packet_number'] = package_dict['orignal_packet_number']
                if 'planned_packet' in package_dict.keys():
                    package_vals['planned_packet'] = package_dict['planned_packet']
                if 'pick_up_date' in package_dict.keys():
                    package_vals['pickup_date'] = package_dict['pick_up_date']
                if 'no_collection' in package_dict.keys():
                    package_vals['no_collection'] = package_dict['no_collection']
                if 'no_delivery' in package_dict.keys():
                    package_vals['no_delivery'] = package_dict['no_delivery']
                if 'delivery_date' in package_dict.keys():
                    package_vals['delivery_date'] = package_dict['delivery_date']
                if 'internal_order_number' in package_dict.keys():
                    package_vals['internal_order_number'] = package_dict['internal_order_number']
                if 'packet_temp_mode' in package_dict.keys():
                    package_vals['packet_temp_mode'] = package_dict['packet_temp_mode']
                if 'packet_type' in package_dict.keys():
                    package_vals['packet_type'] = package_dict['packet_type']
                if 'comment' in package_dict.keys():
                    package_vals['comment'] = package_dict['comment']
                if 'parceltype' in package_dict.keys():
                    package_vals['parceltype'] = package_dict['parceltype']
                if 'picking_direction' in package_dict.keys():
                    package_vals['collection_direction'] = package_dict['picking_direction']
                if 'delivery_direction' in package_dict.keys():
                    package_vals['delivery_direction'] = package_dict['delivery_direction']
    
                if 'picking_warehouse_id' in package_dict.keys():
                    warehouse_code = package_dict['picking_warehouse_id']
                    warehouse = loc_obj.get_location_warehouse_id_from_code(warehouse_code, False, create_if_not_exists=True)
                    package_vals['picking_warehouse_id'] = warehouse.id
                    package_vals['location_code'] = warehouse_code
                
                if 'transport_types' in package_dict.keys():
                    package_vals['transport_type_id'] = transport_type_obj.create_if_not_exists(package_dict['transport_types']).id
                
                if 'firm_id' in package_dict.keys():
                    comp = comp_obj.search([
                        ('company_code','=',package_dict['firm_id'])
                    ], limit=1)
                    if comp:
                        package_vals['company_id'] = comp.id
                    else:
                        raise UserError(_('No Company found with code %s') %package_dict['firm_id'])
                
                if 'owner_id' in package_dict.keys():
                    owner = own_obj.with_context(find_ignored=False).search([
                        ('product_owner_external_id','=',package_dict['owner_id'])
                    ], limit=1)
                    if owner:
                        package_vals['owner_id'] = owner.id
                    else:
                        raise UserError(_('No Owner found with external ID %s') %package_dict['owner_id'])

                ctx['package_message'] = []
                package = pack_obj.with_context(ctx).create_package(package_vals)
                
                for document_dict in package_dict.get('documents', []):
                    document_vals = {}
                    document_vals['external_document_id'] = document_dict['external_document_id']
                    document_vals['package_id'] = package.id
                    
                    if 'document_number' in document_dict.keys():
                        document_vals['document_number'] = document_dict['document_number']
                    if 'document_type' in document_dict.keys():
                        document_vals['document_type'] = document_dict['document_type']
                    if 'external_invoice_id' in document_dict.keys():
                        document_vals['external_invoice_id'] = document_dict['external_invoice_id']
                    
                    doc_obj.with_context(ctx).create_document(document_vals)
                
                for container_dict in package_dict.get('container', []):
                    container_vals = {}
                    container_vals['id_external'] = container_dict['external_container_id']
                    container_vals['package_id'] = package.id
                    
                    if 'package_nr' in container_dict.keys():
                        container_vals['container_no'] = container_dict['package_nr']
                    if 'package_weight' in container_dict.keys():
                        container_vals['weight'] = container_dict['package_weight']
                    cont_obj.with_context(ctx).create_container(container_vals)
                
                msg = ctx.get('package_message', _('Success'))
                package.create_transportation_task_after_package_import()
                package.create_account_invoice_after_package_import()
            except UserError as e:
                if not skip:
                    err_note = _('Failed to create package: %s') % (tools.ustr(e),)
                    msg += err_note
                    processed = False
                    trb += traceback.format_exc() + '\n\n'
                    result['error'] = True
                    self.env.cr.rollback()
            except Exception as e:
                err_note = _('Failed to create package: %s') % (tools.ustr(e),)
                msg += err_note
                processed = False
                trb += traceback.format_exc() + '\n\n'
                result['error'] = True
                self.env.cr.rollback()
            
            result['result'] = msg
            
            for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
                if ctx.get(created_object_ids_name, []):
                    result['created_objects'].append({
                        'name': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['name'],
                        'object': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['object'],
                        'created_ids': ctx[created_object_ids_name]
                    })
            for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
                ctx[created_object_ids_name] = []
            
            
            results['packages'].append(result)
        log_vals = {
            'processed': processed,
            'return_results': str(json.dumps(results, indent=2)),
            'traceback_string': trb
        }
        updated_vals = {}
        for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
            if ctx.get(updated_object_ids_name, []):
                updated_ids = []
                for updated_tuple in ctx[updated_object_ids_name]:
                    if updated_tuple[1] not in updated_ids:
                        updated_ids.append(updated_tuple[1])
                updated_vals[updated_object_ids_name] = [(6,0,updated_ids)]
        log_vals.update(updated_vals)
        self.write(log_vals)
        return results

    @api.multi
    def process_intermediate_object_order(self):
        part_obj = self.env['res.partner']
        own_obj = self.env['product.owner']
        so_obj = self.env['sale.order']
        sol_obj = self.env['sale.order.line']
        prod_obj = self.env['product.product']
        loc_obj = self.env['stock.location']
        comp_obj = self.env['res.company']
        transport_type_obj = self.env['transport.type']
        
        context = self.env.context or {}
        
        results = {}
        results['sales'] = []
        order_vals_list = self.get_received_values_as_dict()
        processed = True

        ctx = context.copy()
        
        for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
            ctx[created_object_ids_name] = []
            
        for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
            ctx[updated_object_ids_name] = []
        ctx['intermediate_id'] = self.id
        ctx['skip_weight_calculation'] = True
        ctx['skip_task_line_recount'] = True
        ctx['do_not_update_product'] = self.do_not_update_vals('product.product')
        trb = ''
        for order_dict in order_vals_list:
            msg = ''
            result = {}
            result['sale'] = order_dict['external_sale_order_id']
            result['created_objects'] = []
            result['result'] = _('Sale was created successfully')
            result['error'] = False
            cancel = False
            skip = False
            check_to_cancel = False
            try:
                self.check_order_vals(order_dict)
                order_vals = {}

                skip_import = self.do_skip_import(order_dict)
                if skip_import:
                    msg = skip_import
                    skip = True
                    raise UserError(_('Import object is too old to be imported'))
                skip_import = self.do_skip_import_by_timestamp(
                    int(order_dict['timestamp'], 16), 'sale_order',
                    'external_sale_order_id', order_dict['external_sale_order_id']
                )
                if skip_import:
                    msg = skip_import
                    skip = True
                    raise UserError(_('Import object already imported(By TimeStamp)'))


                #partner
                if 'externalcustomer_id' in order_dict.keys():
                    partner = part_obj.search([
                        ('external_customer_id','=',order_dict['externalcustomer_id'])
                    ], limit=1)
                    if partner:
                        partner_id = partner.id
                    else:
                        raise UserError(_('There are no partner with external id: %s') %order_dict['externalcustomer_id'])
                    order_vals['partner_id'] = partner_id

                    # temp_so = so_obj.new(order_vals)
                    # temp_so.onchange_partner_id()
                    # order_vals.update(temp_so._convert_to_write(temp_so._cache))
                    order_vals['partner_invoice_id'] = partner_id

                #buyer address
                if 'external_buyer_address_id' in order_dict.keys():
                    buyer_address = part_obj.search([
                        ('external_customer_address_id','=',order_dict['external_buyer_address_id'])
                    ], limit=1)
                    if buyer_address:
                        buyer_address_id = buyer_address.id
                    else:
                        raise UserError(_('There are no POSID with external id: %s') %order_dict['external_buyer_address_id'])
                    order_vals['partner_shipping_id'] = buyer_address_id
                 
                #order
                if 'warehouse_id' in order_dict.keys():
                    warehouse_code = order_dict['warehouse_id']
                    location, warehouse = loc_obj.get_location_warehouse_id_from_code(warehouse_code, True, create_if_not_exists=True)
                    order_vals['warehouse_id'] = warehouse.id
                    order_vals['picking_location_id'] = location.id
                
                if 'picking_warehouse_id' in order_dict.keys():
                    warehouse_code = order_dict['picking_warehouse_id']
                    location, picking_warehouse = loc_obj.get_location_warehouse_id_from_code(warehouse_code, True, create_if_not_exists=True)
                    order_vals['warehouse_id'] = picking_warehouse.id
                    order_vals['picking_location_id'] = location.id
                
                order_vals['external_sale_order_id'] = order_dict['external_sale_order_id']
                if 'document_name' in order_dict.keys():
                    order_vals['name'] = order_dict['document_name']
                if 'picking_list' in order_dict.keys():
                    order_vals['selection_sheet'] = order_dict['picking_list']
                if 'cash' in order_dict.keys():
                    order_vals['cash'] = order_dict['cash']
                if 'cash_amount' in order_dict.keys():
                    order_vals['cash_amount'] = order_dict['cash_amount']
                if 'alcohol' in order_dict.keys():
                    order_vals['alcohol'] = order_dict['alcohol']
                if 'tobacco' in order_dict.keys():
                    order_vals['tobacco'] = order_dict['tobacco']
                if 'route_type' in order_dict.keys():
                    order_vals['route_type'] = order_dict['route_type']
                if 'comment' in order_dict.keys():
                    order_vals['comment'] = order_dict['comment']
                if 'delivering_goods_time' in order_dict.keys():
                    order_vals['delivered_goods_time'] = order_dict['delivering_goods_time']
                if 'delivering_goods_by_routing_program' in order_dict.keys():
                    order_vals['delivering_goods_by_routing_program'] = order_dict['delivering_goods_by_routing_program']
                if 'delivery_number' in order_dict.keys():
                    order_vals['delivery_number'] = order_dict['delivery_number']
                if 'order_type' in order_dict.keys():
                    order_vals['order_type'] = order_dict['order_type']
                if 'delivery_type' in order_dict.keys():
                    order_vals['delivery_type'] = order_dict['delivery_type']
                if 'customer_region' in order_dict.keys():
                    order_vals['customer_region'] = order_dict['customer_region']
                if 'customer_loading_type' in order_dict.keys():
                    order_vals['customer_loading_type'] = order_dict['customer_loading_type']
                if 'direction' in order_dict.keys():
                    order_vals['direction'] = order_dict['direction']
                if 'document_type' in order_dict.keys():
                    order_vals['document_type'] = order_dict['document_type']
                if 'shiping_date' in order_dict.keys():
                    order_vals['shipping_date'] = order_dict['shiping_date']
                if 'timestamp' in order_dict.keys():
                    order_vals['import_timestamp'] = int(order_dict['timestamp'], 16)

                if 'firm_id' in order_dict.keys():
                    comp = comp_obj.search([
                        ('company_code','=',order_dict['firm_id'])
                    ], limit=1)
                    if comp:
                        order_vals['company_id'] = comp.id
                    else:
                        raise UserError(_('No Company found with code %s') %order_dict['firm_id'])
                    
                if 'state' in order_dict.keys():
                    if order_dict['state'] == 'cancel':
                        cancel = True
                        
                if 'transport_types' in order_dict.keys():
                    transport_type = transport_type_obj.search([
                        ('code','=',order_dict['transport_types'])
                    ], limit=1)
                    if transport_type:
                        order_vals['transport_type_id'] = transport_type.id
                    else:
                        order_vals['transport_type_id'] = transport_type_obj.create({
                            'code': order_dict['transport_types'],
                            'name': order_dict['transport_types'],
                        }).id

                if 'owner_id' in order_dict.keys():
                    owner = own_obj.with_context(find_ignored=False).search([
                        ('product_owner_external_id','=',order_dict['owner_id'])
                    ], limit=1)
                    if owner:
                        order_vals['owner_id'] = owner.id
                    else:
                        raise UserError(_('No Owner found with external ID %s') %order_dict['owner_id'])

                ctx['sale_message'] = []
                sale = so_obj.with_context(ctx).create_sale(order_vals)

                line_no = 0
                #order_lines
                for line_dict in order_dict.get('order_lines', []):
                    line_no += 1

                    line_vals = {}
                    line_vals['order_id'] = sale.id
                    line_vals['external_sale_order_line_id'] = line_dict['external_sale_order_line_id']
                    line_vals['line_no'] = line_no
                    line_vals['sequence'] = line_no

                    #product
                    if 'external_product_id' in line_dict.keys():
                        product_vals = {
                            'external_product_id': line_dict['external_product_id']
                        }
                        if 'product_code' in line_dict.keys():
                            product_vals['default_code'] = line_dict['product_code']
                        if 'product_name' in line_dict.keys():
                            product_vals['name'] = line_dict['product_name']
                            
                        product_vals['type_of_product'] = line_dict.get('product_type', 'produktas')
                            
                        product = prod_obj.with_context(ctx).create_product(product_vals)
                        line_vals['product_id'] = product.id

                        line_vals['name'] = product_vals['name']
                        line_vals['product_uom'] = prod_obj.get_default_uom_for_product(line_dict['sale_order_line_uom'])
                        # temp_sol = sol_obj.new(line_vals)
                        # temp_sol.product_id_change()
                        # line_vals.update(temp_sol._convert_to_write(temp_sol._cache))
                    
                    if 'sale_order_line_qty' in line_dict.keys():
                        line_vals['product_uom_qty'] = line_dict['sale_order_line_qty']
                        line_vals['product_uos_qty'] = line_dict['sale_order_line_qty']

                    if 'sale_order_line_confirmed_qty' in line_dict.keys() and not sale.processed_with_despatch:
                        line_vals['picked_qty'] = line_dict['sale_order_line_confirmed_qty']
                        if not check_to_cancel and line_dict['sale_order_line_confirmed_qty'] == 0.0:
                            check_to_cancel = True
                    
                    if 'sale_order_line_uom' in line_dict.keys():
                        line_vals['uom'] = line_dict['sale_order_line_uom']

                    if 'sale_order_line_amount_wth_tax' in line_dict.keys() and 'sale_order_line_qty' in line_dict.keys():# and 'sale_order_line_tax_amount' in line_dict.keys():
                        line_vals['price_unit'] = \
                            line_dict['sale_order_line_amount_wth_tax'] / line_dict.get('sale_order_line_qty', 1.0)
                    sol_obj.with_context(ctx).create_sale_line(line_vals)
                sale.update_weight_and_pallete_with_sql()
                sale.with_context(context).recount_lines_numbers()
                if cancel:
                    sale.action_cancel()
                sale.create_container_for_sale()
                sale.create_transportation_order_for_sale()
                sale.actions_after_creating_task()
                if check_to_cancel:
                    sale.cancel_action_if_none_is_confirmed()
                    
                msg = ctx.get('sale_message', [_('Success')])[0]
                
            except UserError as e:
                if not skip:
                    skip = False
                    err_note = _('Failed to create sale: %s') % (tools.ustr(e),)
                    msg += err_note
                    processed = False
                    trb += traceback.format_exc() + '\n\n'
                    result['error'] = True
                    self.env.cr.rollback()

            except Exception as e:
                err_note = _('Failed to create sale: %s') % (tools.ustr(e),)
                msg += err_note
                processed = False
                trb += traceback.format_exc() + '\n\n'
                result['error'] = True
                self.env.cr.rollback()
            
            result['result'] = msg
            for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
                if ctx.get(created_object_ids_name, []):
                    result['created_objects'].append({
                        'name': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['name'],
                        'object': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['object'],
                        'created_ids': ctx[created_object_ids_name]
                    })
            for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
                ctx[created_object_ids_name] = []
            
            results['sales'].append(result)

        log_vals = {
            'processed': processed,
            'return_results': str(json.dumps(results, indent=2)),
            'traceback_string': trb
        }
        updated_vals = {}
        for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
            if ctx.get(updated_object_ids_name, []):
                updated_ids = []
                for updated_tuple in ctx[updated_object_ids_name]:
                    if updated_tuple[1] not in updated_ids:
                        updated_ids.append(updated_tuple[1])
                updated_vals[updated_object_ids_name] = [(6,0,updated_ids)]
        log_vals.update(updated_vals)
        # self.write(log_vals)
        resultss = str(json.dumps(results, indent=2))
        try:
            resultss.encode('utf-8').decode('unicode-escape')
        except:
            pass
        sql = '''
            UPDATE
                stock_route_integration_intermediate
            SET
                processed = %s,
                return_results = %s,
                traceback_string = %s
            WHERE
                id = %s
        '''
        self.env.cr.execute(sql, (processed, resultss, trb, self.id))
        return results

    @api.multi
    def process_intermediate_object_invoice(self):
        part_obj = self.env['res.partner']
        ai_obj = self.env['account.invoice']
        curr_obj = self.env['res.currency']
        link_obj = self.env['stock.route.integration.intermediate.missing_links']
        sol_obj = self.env['sale.order.line']
        prod_obj = self.env['product.product']
        ail_obj = self.env['account.invoice.line']
        comp_obj = self.env['res.company']
        own_obj = self.env['product.owner']
        loc_obj = self.env['stock.location']
        
        context = self.env.context or {}
        
        results = {}
        results['invoices'] = []
        invoice_vals_list = self.get_received_values_as_dict()
        processed = True

        ctx = context.copy()
        
        for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
            ctx[created_object_ids_name] = []
            
        for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
            ctx[updated_object_ids_name] = []
            
        ctx['intermediate_id'] = self.id
        ctx['do_not_update_product'] = self.do_not_update_vals('product.product')
        ctx['skip_weight_calculation'] = True
        trb = ''
        for invoice_dict in invoice_vals_list:
            msg = ''
            skip = False
            result = {}
            cancel = False
            no_sale = True
            result['invoice'] = invoice_dict['external_invoice_id']
            result['created_objects'] = []
            result['result'] = _('Invoice was created successfully')
            result['error'] = False
            related_task_lines = sol_obj.browse([])
            try:
                self.check_invoice_vals(invoice_dict)
                invoice_vals = {}
                invoice_vals['external_invoice_id'] = invoice_dict['external_invoice_id']


                skip_import = self.do_skip_import(invoice_dict)
                if skip_import:
                    msg = skip_import
                    skip = True
                    raise UserError(_('Import object is too old to be imported'))

                #partner
                if 'external_customer_id' in invoice_dict.keys():
                    partner = part_obj.search([
                        ('external_customer_id','=',invoice_dict['external_customer_id'])
                    ], limit=1)
                    if not partner:
                        raise UserError(_('There are no partner with external id: %s') %invoice_dict['external_customer_id'])
        
                    invoice_vals['partner_id'] = partner.id

                    # temp_ai = ai_obj.new(invoice_vals)
                    # temp_ai._onchange_partner_id()
                    # invoice_vals.update(temp_ai._convert_to_write(temp_ai._cache))

                    invoice_vals['partner_invoice_id'] = partner.id
                 
                #buyer address
                if 'external_buyer_address_id' in invoice_dict.keys():
                    buyer_address = part_obj.search([
                        ('external_customer_address_id','=',invoice_dict['external_buyer_address_id'])
                    ], limit=1)
                    if not buyer_address:
                        raise UserError(_('There are no POSID with external id: %s') %invoice_dict['external_buyer_address_id'])
                    invoice_vals['partner_shipping_id'] = buyer_address.id
                    invoice_vals['posid'] = buyer_address.possid_code or ''
                    
                invoice_vals['type'] = 'out_invoice'
                if 'cash_amount' in invoice_dict.keys():
                    invoice_vals['cash_amount'] = invoice_dict['cash_amount']
                if 'document_id_for_ivaz' in invoice_dict.keys():
                    invoice_vals['document_id_for_ivaz'] = invoice_dict['document_id_for_ivaz']
                if 'invoice_no' in invoice_dict.keys():
                    invoice_vals['name'] = invoice_dict['invoice_no']
                    invoice_vals['number'] = invoice_dict['invoice_no']
                if 'NKRO' in invoice_dict.keys():
                    invoice_vals['nkro_number'] = invoice_dict['NKRO']
                if 'NSAD' in invoice_dict.keys():
                    invoice_vals['nsad_number'] = invoice_dict['NSAD']
                if 'invoice_date' in invoice_dict.keys():
                    invoice_vals['date_invoice'] = invoice_dict['invoice_date']
                if 'timestamp' in invoice_dict.keys():
                    invoice_vals['import_timestamp'] = int(invoice_dict['timestamp'], 16)
                if 'invoice_time' in invoice_dict.keys():
                    invoice_vals['time_invoice'] = invoice_dict['invoice_time'][11:16]
                    invoice_vals['document_create_datetime'] = invoice_dict['invoice_time'][:-2]
                if 'firm_id' in invoice_dict.keys():
                    comp = comp_obj.search([
                        ('company_code','=',invoice_dict['firm_id'])
                    ])
                    if comp:
                        invoice_vals['company_id'] = comp.id
                    else:
                        raise UserError(_('No Company found with code %s') %invoice_dict['firm_id'])
                
                
                if 'picking_warehouse_id' in invoice_dict.keys():
                    warehouse_code = invoice_dict['picking_warehouse_id']
                    location, picking_warehouse = loc_obj.get_location_warehouse_id_from_code(
                        warehouse_code, True, create_if_not_exists=True
                    )
                    invoice_vals['picking_warehouse_id'] = picking_warehouse.id
                    invoice_vals['picking_location_id'] = location.id
                
                
                if 'owner_id' in invoice_dict.keys():
                    owner = own_obj.with_context(find_ignored=False).search([
                        ('product_owner_external_id','=',invoice_dict['owner_id'])
                    ])
                    if owner:
                        invoice_vals['owner_id'] = owner.id
                    else:
                        raise UserError(_('No Owner found with external ID %s') %invoice_dict['owner_id'])
                
                    
                if "state" in invoice_dict.keys():
                    invoice_vals['sanitex_state'] = invoice_dict['state']
                if 'primary_id' in invoice_dict.keys():
                    primary_inv = ai_obj.search([
                        ('external_invoice_id','=',invoice_dict['primary_id'])
                    ])
                    if primary_inv:
                        invoice_vals['primary_invoice_id'] = primary_inv.id
                        if primary_inv.state != 'cancel':
                            primary_inv.action_cancel_bls()
                            cancel = True
                        
                #valiuta
                if 'invoice_currency' in invoice_dict.keys():
                    curr = curr_obj.search([
                        ('name','=',invoice_dict['invoice_currency'])
                    ])
                    if curr:
                        invoice_vals['currency_id'] = curr.id

                ctx['invoice_message'] = []
                invoice = ai_obj.with_context(ctx).create_invoice(invoice_vals)

                for invoice_line_dict in invoice_dict.get('invoice_lines', []):
                    invoice_line_vals = {}
                    invoice_line_vals['external_invoice_line_id'] = invoice_line_dict['external_invoice_line_id']
                    invoice_line_vals['invoice_id'] = invoice.id
                    
                    #product
                    if 'external_product_id' in invoice_line_dict.keys():
                        product_vals = {
                            'external_product_id': invoice_line_dict['external_product_id'],
        #                             'uom_id': line_dict['product_code'],
                        }
                        if 'product_code' in invoice_line_dict.keys():
                            product_vals['default_code'] = invoice_line_dict['product_code']
                        if 'product_name' in invoice_line_dict.keys():
                            product_vals['name'] = invoice_line_dict['product_name']
                            
                        product_vals['type_of_product'] = invoice_line_dict.get('product_type', 'produktas')
                            
                        product = prod_obj.with_context(ctx).create_product(product_vals)
                        invoice_line_vals['product_id'] = product.id

                        #9 versijos pakeitimas:
                        # temp_ail = ail_obj.new(invoice_line_vals)
                        # temp_ail._onchange_product_id()
                        # invoice_line_vals.update(temp_ail._convert_to_write(temp_ail._cache))

                    invoice_line_vals['name'] = invoice_line_dict['product_name']
                    invoice_line_vals['uom_id'] = prod_obj.get_default_uom_for_product()
                    if 'invoice_line_uom' in invoice_line_dict.keys():
                        invoice_line_vals['uom'] = invoice_line_dict['invoice_line_uom']
                    if 'invoice_line_price' in invoice_line_dict.keys():
                        invoice_line_vals['price_unit'] = invoice_line_dict['invoice_line_price']
                    if 'invoice_line_qty' in invoice_line_dict.keys():
                        invoice_line_vals['quantity'] = invoice_line_dict['invoice_line_qty']
                    
                    invoice_line_vals['sale_order_line_ids'] = []
                    if invoice_line_dict.get('sale_order_line_ids', []):
                        no_sale = False
                    for sale_order_line_ext_id in invoice_line_dict.get('sale_order_line_ids', []):
                        
                        sol = sol_obj.search([
                            ('external_sale_order_line_id','=',sale_order_line_ext_id)
                        ], limit=1)
                        if sol:
                            invoice_line_vals['sale_order_line_ids'] = [(4,sol.id)]
                            related_task_lines += sol
                        else:
                            if not link_obj.search([
                                ('object_from','=','account.invoice.line'),
                                ('object_to','=','sale.order.line'),
                                ('exernal_id_from','=',invoice_line_dict['external_invoice_line_id']),
                                ('exernal_id_to','=',sale_order_line_ext_id),
                            ]):
                                link_obj.create({
                                    'object_from': 'account.invoice.line',
                                    'object_to': 'sale.order.line',
                                    'exernal_id_from': invoice_line_dict['external_invoice_line_id'],
                                    'exernal_id_to': sale_order_line_ext_id
                                })

                    ail_obj.with_context(ctx).create_invoice_line(invoice_line_vals)
                invoice.update_sale_orders()
                invoice.invoice_line_ids.with_context(skip_weight_calculation=False).update_total_weight()
                if cancel:
                    invoice.action_cancel()
                elif no_sale and invoice_dict.get('state2','') != 'cancel':
                    invoice.create_sale()
#                 route_obj.route_create(cr, uid, route_vals, context=ctx)
                msg = ctx.get('invoice_message', _('Success'))
                related_task_lines.with_context(recompute=False).mapped('order_id').update_cash_amount()
                invoice.update_amounts()
                invoice.update_line_count()
            except UserError as e:
                if not skip:
                    err_note = _('Failed to create invoice: %s') % (tools.ustr(e),)
                    msg += err_note
                    processed = False
                    trb += traceback.format_exc() + '\n\n'
                    result['error'] = True
                    self.env.cr.rollback()
            except Exception as e:
                err_note = _('Failed to create invoice: %s') % (tools.ustr(e),)
                msg += err_note
                processed = False
                trb += traceback.format_exc() + '\n\n'
                result['error'] = True
                self.env.cr.rollback()

            result['result'] = msg
            
            for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
                if ctx.get(created_object_ids_name, []):
                    result['created_objects'].append({
                        'name': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['name'],
                        'object': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['object'],
                        'created_ids': ctx[created_object_ids_name]
                    })
            for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
                ctx[created_object_ids_name] = []
            
            
            results['invoices'].append(result)
        log_vals = {
            'processed': processed,
            'return_results': str(json.dumps(results, indent=2)),
            'traceback_string': trb
        }
        updated_vals = {}
        for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
            if ctx.get(updated_object_ids_name, []):
                updated_ids = []
                for updated_tuple in ctx[updated_object_ids_name]:
                    if updated_tuple[1] not in updated_ids:
                        updated_ids.append(updated_tuple[1])
                updated_vals[updated_object_ids_name] = [(6,0,updated_ids)]
        log_vals.update(updated_vals)
        # self.write(log_vals)
        resultss = str(json.dumps(results, indent=2))
        try:
            resultss.encode('utf-8').decode('unicode-escape')
        except:
            pass
        sql = '''
            UPDATE
                stock_route_integration_intermediate
            SET
                processed = %s,
                return_results = %s,
                traceback_string = %s
            WHERE
                id = %s
        '''
        self.env.cr.execute(sql, (processed, resultss, trb, self.id))
        return results

    @api.multi
    def process_intermediate_object_route_packets(self):
        context = self.env.context or {}
        commit = not context.get('no_commit', False)

        # loc_env = self.env['stock.location']
        # so_env = self.env['sale.order']
        # no_env = self.env['stock.route.number']
        # link_env = self.env['stock.route.integration.intermediate.missing_links']
        link2_env = self.env['stock.route.integration.missing_links.new']
        pack_env = self.env['stock.package']

        results = {}
        trb = ''
        results['routes'] = []
        route_vals_list = self.get_received_values_as_dict()
        processed = True
        for route_package_link_dict in route_vals_list:
            skip = False
            msg = ''
            result = {}
            result['error'] = False
            try:
                result['order'] = route_package_link_dict['order_no']
                result['result'] = _('Link was created successfully')
                if route_package_link_dict.get('external_packet_ids', False):
                    route_package_link_dict['order_no'] = '-'.join(route_package_link_dict['order_no'].split('-')[1:])
                    updated_order_ext_id_dict = link2_env.create_or_update_route_packing_transfer_info(route_package_link_dict)
                    if {
                        'external_packet_ids', 'stock_number_id', 'delivery_type', 'picking_warehouse_id', 'shiping_warehouse_id'
                    }.issubset(set(updated_order_ext_id_dict.keys())):
                        stock_number_id = updated_order_ext_id_dict['stock_number_id']
                        delivery_number = updated_order_ext_id_dict.get('delivery_number', '')
                        packages = pack_env.search([
                            ('external_package_id','in',updated_order_ext_id_dict['external_packet_ids'])
                        ])
                        not_find_external_ids = \
                            list(set(updated_order_ext_id_dict['external_packet_ids'])-set(packages.mapped('external_package_id')))
                        packages.create_transportation_tasks(
                            updated_order_ext_id_dict['delivery_type'], updated_order_ext_id_dict['shiping_warehouse_id'],
                            updated_order_ext_id_dict['picking_warehouse_id'], stock_number_id, delivery_number
                        )
                        if not_find_external_ids:
                            link2_env.create_missing_package_information(
                                not_find_external_ids, stock_number_id, updated_order_ext_id_dict['delivery_type'],
                                updated_order_ext_id_dict['shiping_warehouse_id'], updated_order_ext_id_dict['picking_warehouse_id'], delivery_number
                            )

                if commit:
                    self.env.cr.commit()
            except UserError as e:
                if not skip:
                    err_note = _('Failed to create route: %s') % (tools.ustr(e),)
                    msg += err_note
                    processed = False
                    trb = traceback.format_exc() + '\n\n'
                    result['error'] = True
                    self.env.cr.rollback()
            except Exception as e:
                err_note = _('Failed to create route: %s') % (tools.ustr(e),)
                msg += err_note
                processed = False
                trb = traceback.format_exc() + '\n\n'
                result['error'] = True
                self.env.cr.rollback()

            result['result'] = msg


        results['routes'].append(result)
        log_vals = {
            'processed': processed,
            'return_results': str(json.dumps(results, indent=2)),
            'traceback_string': trb
        }
        self.write(log_vals)
        return results
        
    @api.multi
    def process_intermediate_object_route(self):
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        
        loc_env = self.env['stock.location']
        so_env = self.env['sale.order']
        no_env = self.env['stock.route.number']
        # link_env = self.env['stock.route.integration.intermediate.missing_links']
        link2_env = self.env['stock.route.integration.missing_links.new']
        pack_env = self.env['stock.package']
        template_env = self.env['stock.route.template']
        part_env = self.env['res.partner']

        templates_to_remove = template_env.browse([])
        results = {}
        trb = ''
        results['routes'] = []
        route_vals_list = self.get_received_values_as_dict()
        processed = True
        for route_dict in route_vals_list:
            skip = False
            msg = ''
            result = {}
            result['error'] = False
            try:
                result['route'] = route_dict['external_route_id']
                result['result'] = _('Route was created successfully')

                skip_import = self.do_skip_import(route_dict)
                if skip_import:
                    msg = skip_import
                    skip = True
                    raise UserError(_('Import object is too old to be imported'))

                #vairuotojas
                location_id = False
                license_plate = ''
                driver_name = ''
                receiver = ''

                route_vals = {
                    'external_route_id': route_dict['external_route_id'],
                    'date': route_dict['date'],
                    'weight': route_dict.get('weight', 0.0),
                    'distance': route_dict.get('route_length', 0),
                    'source': route_dict.get('source', ''),
                    'estimated_start': route_dict.get('estimated_start', False),
                    'estimated_finish': route_dict.get('estimated_finish', False),
                }

                if 'driver_name' in route_dict.keys():
                    locations = loc_env.search([
                        ('name','=',route_dict['driver_name'])
                    ])
                    if locations:
                        location = locations[0]
                        license_plate = location.license_plate
                        location_id = location.id
                    else:
                        driver_name = route_dict['driver_name']
                    route_vals['driver'] = route_dict['driver_name']
                if 'car_number' in route_dict.keys():
                    license_plate = route_dict['car_number']
                    route_vals['license_plate'] = license_plate
                if 'receiver' in route_dict.keys():
                    receiver = route_dict['receiver']
                    route_vals['name'] = receiver
                stock_number = no_env.create_if_not_exists(route_vals)
                stock_number.write({'intermediate_id': self.id})
                for order_ext_id_dict in route_dict.get('orders', []):
                    if 'active' not in order_ext_id_dict.keys():
                        order_ext_id_dict['active'] = 'Y'
                    
                    active = False
                    if order_ext_id_dict['active'] == 'Y':
                        active = True
                        
                    if order_ext_id_dict.get('order_id', False):
                        order_ext_id = order_ext_id_dict['order_id']
                        
                        sales = so_env.get_first_sale_order_by_external_id(order_ext_id)
                        
                        #susirandam visus susijusius sandėlius
                        ship_wh = loc_env.get_location_warehouse_id_from_code(
                            order_ext_id_dict['shiping_warehouse_id'], create_if_not_exists=True
                        )
                        ship_wh_id = ship_wh.id
                        pick_loc, pick_wh = loc_env.get_location_warehouse_id_from_code(
                            order_ext_id_dict['picking_warehouse_id'], True, create_if_not_exists=True
                        )
                        pick_loc_id = pick_loc.id
                        pick_wh_id = pick_wh.id
                        delivery_number = order_ext_id_dict.get('delivery_number', '')
                        if sales:
                            sale = sales[0]      
                            #Jei randamas pardavimas kuriam reikia pridėti importuojamą maršrutą
                            if active:
                                # jei maršrutą ir susijusius sandėlius reikia pridėti 
                                # egzistuojančiam pardavimui
                                sale_vals = {
                                    'route_number_id': stock_number.id
                                }
                                if location_id:
                                    sale_vals['driver_id'] = location_id
                                if license_plate:
                                    sale_vals['license_plate'] = license_plate
                                if driver_name:
                                    sale_vals['driver_name'] = driver_name
                                sale_vals['shipping_warehouse_id'] = ship_wh_id
                                sale_vals['warehouse_id'] = pick_wh_id
                                sale_vals['picking_location_id'] = pick_loc_id
                                sale_vals['order_number_by_route'] = delivery_number
                                if not sale.route_id:
                                    sale.write(sale_vals)
                                else:
                                    sale.copy_sale_for_replanning(additional_vals=sale_vals)
#                                 if not sale.related_route_ids:
#                                 if not sale.route_id:
#                                     sale.continue_chain(ship_wh_id, warehouse_id=pick_wh_id)
                            else:
                                #jei nuo egzistuojančio pardavimo reikia nuimti maršruto numerį
                                sale.write({'route_number': ''})
                                if sale.route_template_id:
                                    templates_to_remove |= sale.route_template_id
                        else:
                            # jei pardavimo, kuriam reikia pridėti importuojamą maršrutą, nėra, tada į
                            # trūkstamų ryšių lentelę sukuriame objektus pagal kuriuos reikiamos 
                            # reikšmės įsirašys kai bus sukurtas trūkstamas pardavimas 
                            # ištriname senus susijusius sąryšius jeigu jie egzistavo
                            if active:
                                vals_for_missing_sale = {
                                    'order_number_by_route': delivery_number,
                                    'warehouse_id': pick_wh_id,
                                    'shipping_warehouse_id': ship_wh_id,
                                    'route_number_id': stock_number.id
                                }
                                link2_env.create_missing_task_information(id_to=order_ext_id, vals=vals_for_missing_sale)

                            # existing_missing_links = link_env.search([
                            #     ('object_from','=','sale.order'),
                            #     ('exernal_id_from','=',order_ext_id)
                            # ])
                            # existing_missing_links.unlink()
                            # if active:
                            #     #kuriame trūkstamus sąryšius
                            #     sale_wh_vals = {
                            #         'warehouse_id': pick_wh_id,
                            #         'shipping_warehouse_id': ship_wh_id,
                            #         'route_number_id': stock_number.id
                            #     }
                            #     for key_field in sale_wh_vals.keys():
                            #         link_vals = {
                            #             'object_from': 'sale.order',
                            #             'field': key_field,
                            #             'exernal_id_from': order_ext_id,
                            #             'exernal_id_to': str(sale_wh_vals[key_field])
                            #         }
                            #         link_env.create(link_vals)
                    elif order_ext_id_dict.get('external_packet_ids', False):
                        delivery_number = order_ext_id_dict.get('delivery_number', '')
                        packages = pack_env.search([
                            ('external_package_id','in',order_ext_id_dict['external_packet_ids'])
                        ])
                        not_find_external_ids = \
                            list(set(order_ext_id_dict['external_packet_ids'])-set(packages.mapped('external_package_id')))
                        packages.create_transportation_tasks(
                            order_ext_id_dict['delivery_type'], order_ext_id_dict['shiping_warehouse_id'],
                            order_ext_id_dict['picking_warehouse_id'], stock_number.id, delivery_number
                        )
                        if not_find_external_ids:
                            link2_env.create_missing_package_information(
                                not_find_external_ids, stock_number.id, order_ext_id_dict['delivery_type'],
                                order_ext_id_dict['shiping_warehouse_id'], order_ext_id_dict['picking_warehouse_id'], delivery_number
                            )
                    else:
                        updated_order_ext_id_dict = link2_env.create_or_update_route_packing_transfer_info(order_ext_id_dict, stock_number)
                        if updated_order_ext_id_dict.get('external_packet_ids', False):
                            delivery_number = updated_order_ext_id_dict.get('delivery_number', '')
                            packages = pack_env.search([
                                ('external_package_id','in',updated_order_ext_id_dict['external_packet_ids'])
                            ])
                            not_find_external_ids = \
                                list(set(updated_order_ext_id_dict['external_packet_ids'])-set(packages.mapped('external_package_id')))
                            packages.create_transportation_tasks(
                                updated_order_ext_id_dict['delivery_type'], updated_order_ext_id_dict['shiping_warehouse_id'],
                                updated_order_ext_id_dict['picking_warehouse_id'], stock_number.id, delivery_number
                            )
                            if not_find_external_ids:
                                link2_env.create_missing_package_information(
                                    not_find_external_ids, stock_number.id, updated_order_ext_id_dict['delivery_type'],
                                    updated_order_ext_id_dict['shiping_warehouse_id'], updated_order_ext_id_dict['picking_warehouse_id'], delivery_number
                                )
                        else:
                            if active and order_ext_id_dict.get('owner_id', False) \
                                and order_ext_id_dict.get('order_no', False) \
                            :
                                # Kartais gali taip nutikiti, kad į maršrutą įdėta tokia užduotis ar siunta,
                                # kurios odoo sistemoje nėra ir niekada nebus, bet vistiek tokias užduotis nori
                                # matyti ruošinyje. Tokios užduotys neturės dokumentų ir negalės būti įkeltos į
                                # maršrutą. Jas atsifiltruoti galima pagal placeholder_for_route_template reikšmę True.

                                if not so_env.search([('name','=',order_ext_id_dict['order_no'])], limit=1):
                                    owner = self.env['product.owner'].search([
                                        ('product_owner_external_id','=',order_ext_id_dict['owner_id'])
                                    ])
                                    ship_wh = loc_env.get_location_warehouse_id_from_code(
                                        order_ext_id_dict['shiping_warehouse_id'], create_if_not_exists=True
                                    )
                                    ship_wh_id = ship_wh.id
                                    pick_loc, pick_wh = loc_env.get_location_warehouse_id_from_code(
                                        order_ext_id_dict['picking_warehouse_id'], True, create_if_not_exists=True
                                    )

                                    placeholder_sale_vals = {
                                        'placeholder_for_route_template': True,
                                        'name': order_ext_id_dict['order_no'],
                                        'owner_id': owner.id,
                                        'warehouse_id': pick_wh.id,
                                        'picking_location_id': pick_loc.id,
                                        'shipping_warehouse_id': ship_wh_id,
                                        'external_sale_order_id': order_ext_id_dict['order_no'],
                                        'delivery_type': order_ext_id_dict['delivery_type'] == 'deliver' and 'delivery' or 'collection',
                                        'order_number_by_route': order_ext_id_dict.get('delivery_number', ''),
                                        'route_number_id': stock_number.id,
                                        'shipping_date': route_dict.get('date', False),
                                        'state': 'blank',
                                        'show': True,
                                        'replanned': False,
                                        'sequence': 1,
                                        'company_id': self.env.user.company_id.id,
                                        'order_package_type': 'package',
                                    }
                                    posid = order_ext_id_dict.get('external_buyer_address_id', False)
                                    if posid:
                                        partner_posid = part_env.search([('possid_code','=',posid)])
                                        if partner_posid:
                                            placeholder_sale_vals['partner_shipping_id'] = partner_posid.id
                                            if partner_posid.parent_id:
                                                placeholder_sale_vals['partner_id'] = partner_posid.parent_id.id
                                                placeholder_sale_vals['partner_invoice_id'] = partner_posid.parent_id.id
                                    if placeholder_sale_vals['delivery_type'] == 'collection':
                                        placeholder_sale_vals['related_document_indication'] = 'yes'
                                        placeholder_sale_vals['has_related_document'] = True
                                        placeholder_sale_vals['previous_task_received'] = True
                                    placeholder_task = so_env.with_context(
                                        sale_message=[], skip_missing_links=True
                                    ).create_sale(placeholder_sale_vals)
                                    if placeholder_sale_vals['delivery_type'] == 'collection':
                                        placeholder_task.create_container_for_sale()
                                    placeholder_task.create_transportation_order_for_sale()

                templates_to_remove.remove_if_empty()
                if commit:
                    self.env.cr.commit()    
            except UserError as e:
                if not skip:
                    err_note = _('Failed to create route: %s') % (tools.ustr(e),)
                    msg += err_note
                    processed = False
                    trb = traceback.format_exc() + '\n\n'
                    result['error'] = True
                    self.env.cr.rollback()
            except Exception as e:
                err_note = _('Failed to create route: %s') % (tools.ustr(e),)
                msg += err_note
                processed = False
                trb = traceback.format_exc() + '\n\n'
                result['error'] = True
                self.env.cr.rollback()
            
            result['result'] = msg
            
            
        results['routes'].append(result)
        log_vals = {
            'processed': processed,
            'return_results': str(json.dumps(results, indent=2)),
            'traceback_string': trb
        }
        self.write(log_vals)
        return results
            
    @api.multi
    def process_intermediate_object_dos_location(self):
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        loc_env = self.env['stock.location']
        wh_env = self.env['stock.warehouse']

        processed = True
        msg = ''
        trb = ''
        result = {
            'error': False
        }
        try:
            dos_location_vals = self.get_received_values_as_dict()
            if not dos_location_vals.get('code', False):
                raise UserError(_('Location code is missing.'))
            if not dos_location_vals.get('pref', False):
                raise UserError(_('Pref code is missing.'))

            warehouse = wh_env.with_context(active_test=False).search([
                ('code','=',dos_location_vals['pref'])
            ], limit=1)

            if not warehouse:
                warehouse = wh_env.with_context(dos_warehouse=True).create_wh_if_not_exists(dos_location_vals['pref'])

            location = loc_env.with_context(active_test=False).search([
                ('code','=',dos_location_vals['code'])
            ], limit=1)

            location_vals = {
                'code': dos_location_vals['code']
            }
            if 'name' in dos_location_vals:
                location_vals['name'] = dos_location_vals['name']
            if 'name_lt' in dos_location_vals:
                location_vals['name_lt'] = dos_location_vals['name_lt']
            if 'name_lv' in dos_location_vals:
                location_vals['name_lv'] = dos_location_vals['name_lv']
            if 'name_lt' in dos_location_vals:
                location_vals['name_lt'] = dos_location_vals['name_lt']
            if 'name_en' in dos_location_vals:
                location_vals['name_en'] = dos_location_vals['name_en']
            if 'name_ee' in dos_location_vals:
                location_vals['name_ee'] = dos_location_vals['name_ee']
            if 'name_ru' in dos_location_vals:
                location_vals['name_ru'] = dos_location_vals['name_ru']
            if 'address' in dos_location_vals:
                location_vals['load_address'] = dos_location_vals['address']
            if 'country_code' in dos_location_vals:
                location_vals['country_code'] = dos_location_vals['country_code']
            if 'vat_code' in dos_location_vals:
                location_vals['vat_code'] = dos_location_vals['vat_code']
            if 'reg_code' in dos_location_vals:
                location_vals['reg_code'] = dos_location_vals['reg_code']
            if 'active' in dos_location_vals:
                location_vals['active'] = dos_location_vals['active']
            location_vals['location_id'] = warehouse.lot_stock_id.id
                
            if location:
                if 'location_id' in location_vals:
                    del location_vals['location_id']
                self.remove_same_values(location, location_vals)
                
                if location_vals:
                    location.write(location_vals)
                msg = 'Location updated. ID: %s' % str(location.id)
            else:
                location_vals['dos_location'] = True
                if 'active' not in location_vals:
                    location_vals['active'] = True
                location_vals['usage'] = 'internal'
                location = loc_env.create(location_vals)
                msg = 'Location created. ID: %s' % str(location.id)
        except UserError as e:
            if context.get('from_rest_api', False):
                raise
            err_note = _('Failed to create location: %s') % (tools.ustr(e),)
            msg = err_note
            trb = traceback.format_exc() + '\n\n'
            processed = False
            result['error'] = True
            self.env.cr.rollback()
        except Exception as e:
            if context.get('from_rest_api', False):
                raise
            err_note = _('Failed to create location: %s') % (tools.ustr(e),)
            msg = err_note
            trb = traceback.format_exc() + '\n\n'
            processed = False
            result['error'] = True
            self.env.cr.rollback()
        
        result['result'] = msg
        log_vals = {
            'processed': processed,
            'return_results': str(json.dumps(result, indent=2)),
            'traceback_string': trb
        }
        self.write(log_vals)
        if commit:
            self.env.cr.commit()
    
    @api.multi
    def process_intermediate_object_packing_new(self):
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        
        prod_obj = self.env['product.product']
        comp_obj = self.env['res.company']
        own_obj = self.env['product.owner']
        barcode_env = self.env['product.barcode']
        packing_env = self.env['product.packing']
        tax_env = self.env['account.tax']
        part_env = self.env['res.partner']
        
        results = {}
        results['products'] = []
        
        intermediate = self
        list_of_product_vals = self.get_received_values_as_dict()
        processed = True
        ctx = context.copy()
        
        for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
            ctx[created_object_ids_name] = []
            
        for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
            ctx[updated_object_ids_name] = []
            
        ctx['intermediate_id'] = intermediate.id
        ctx['update_type'] = True
        trb = ''
        for product_vals in list_of_product_vals:
            msg = ''
            result = {
                'created_objects': [],
                'result': _('Product was created successfully'),
                'product': product_vals['external_product_id']
            }
            result['error'] = False
            try:
                vals = {}
                vals['external_product_id'] = product_vals['external_product_id']
                if 'product_name' in product_vals:
                    vals['name'] = product_vals['product_name']
                if 'product_default_code' in product_vals:
                    vals['default_code'] = product_vals['product_default_code']
                else:
                    vals['default_code'] = ''
                if 'product_weight' in product_vals:
                    vals['weight'] = product_vals['product_weight']
                if 'average_weight' in product_vals:
                    vals['average_weight'] = product_vals['average_weight']
                if 'product_standart_price' in product_vals:
                    vals['standard_price'] = product_vals['product_standart_price']
  
                if 'product_name_english' in product_vals:
                    vals['name_english'] = product_vals['product_name_english']
                else:
                    vals['name_english'] = ''
                if 'product_name_russian' in product_vals:
                    vals['name_russian'] = product_vals['product_name_russian']
                else:
                    vals['name_russian'] = ''
                if 'product_weight_neto' in product_vals:
                    vals['weight_neto'] = product_vals['product_weight_neto']
                if 'minimal_qty_multiple' in product_vals:
                    vals['minimal_qty_multiple'] = product_vals['minimal_qty_multiple']
                if 'deposit_qty' in product_vals:
                    vals['deposit_qty'] = product_vals['deposit_qty']
                if 'main_packing_qty' in product_vals:
                    vals['small_package_size'] = product_vals['main_packing_qty']
                if 'second_packing_qty' in product_vals:
                    vals['big_package_size'] = product_vals['second_packing_qty']
                if 'qty_packet_on_pallet' in product_vals:
                    vals['packages_per_pallet'] = product_vals['qty_packet_on_pallet']
                if 'minimal_qty_multiple_fs' in product_vals:
                    vals['minimal_qty_multiple_fs'] = product_vals['minimal_qty_multiple_fs']
                if 'packages_in_row' in product_vals:
                    vals['package_count_in_row'] = product_vals['packages_in_row']
                if 'tlic' in product_vals:
                    vals['tlic'] = product_vals['tlic']
                if 'timestamp' in product_vals.keys():
                    vals['bls_import_timestamp'] = int(product_vals['timestamp'], 16)

                vals['type_of_product'] = product_vals.get('product_type', 'package')
                
                if 'weight_type' in product_vals:
                    vals['product_type'] = product_vals['weight_type']
                    
                if 'certificate' in product_vals:
                    if product_vals['certificate'] == 'certificate_required':
                        vals['certificate'] = 'N'
                    elif product_vals['certificate'] == 'no_certificate':
                        vals['certificate'] = 'T'
                    elif product_vals['certificate'] == 'expiration_date_required':
                        vals['certificate'] = 'G'
                        
                if 'active' in product_vals.keys():
                    if product_vals['active'] == 'Y':
                        vals['active'] = True
                    elif product_vals['active'] == 'N':
                        vals['active'] = False
                        
                if 'firm_id' in product_vals.keys():
                    comps = comp_obj.search([('company_code','=',product_vals['firm_id'])])
                    if comps:
                        vals['company_id'] = comps[0].id
                    else:
                        raise UserError(_('No Company found with code %s') %product_vals['firm_id'])
                
                if 'external_owner_id' in product_vals.keys():
                    owner_vals = {
                        'product_owner_external_id': product_vals['external_owner_id']
                    }
                    if 'owner_code' in product_vals.keys():
                        owner_vals['owner_code'] = product_vals['owner_code']
                    owner = own_obj.create_owner(owner_vals)
                    if owner:
                        vals['owner_id'] = owner.id
                
                if 'vat_tarif' in product_vals.keys():
                    tax = tax_env.get_taxes(float(product_vals['vat_tarif']))
                    if tax:
                        vals['vat_tariff_id'] = tax[0].id
                    else:
                        raise UserError(_('There are no sale tax object with amount %s') % product_vals['vat_tarif'])
                    
                if 'releated_product_id' in product_vals.keys():
                    rel_products = prod_obj.search([('external_product_id','=',product_vals['releated_product_id'])])
                    if rel_products:
                        vals['related_product_id'] = rel_products[0].id
                    else:
                        _logger.info(_('There are no product with external_id %s') % product_vals['releated_product_id'])
                    
                if 'deposit_id' in product_vals.keys() and product_vals['deposit_id'] != "0":
                    try:
                        int(product_vals['deposit_id'])
                    except:

                        # Praleidžiam kai atsiunčia '0', nes tikriausiai tokiu atveju turėjo nieko nesiųsti
                        dep_products = prod_obj.search([('external_product_id','=',product_vals['deposit_id'])])
                        if dep_products:
                            vals['deposit_id'] = dep_products[0].id
                        else:
                            _logger.info(_('There are no product with external_id %s') % product_vals['deposit_id'])

                if 'external_supplier_id' in product_vals.keys():
                    supplier = part_env.search([
                        ('external_customer_id','=',product_vals['external_supplier_id'])
                    ], limit=1)
                    if not supplier:
                        _logger.info(_('There are no supplier with external id: %s') % product_vals['external_supplier_id'])
                    else:
                        vals['supplier_id'] = supplier.id


                product = prod_obj.with_context(ctx).create_product(vals)

               
                #barkodai

                barcodes = barcode_env.browse()
                for barcode_dict in product_vals.get('Barcodes', []):
                    barcode_vals = {}
                    barcode_vals['product_id'] = product.id

                    barcode_vals['barcode'] = barcode_dict['barcode']
                    barcode_vals['type'] = barcode_dict['barcode_type']
                    if barcode_vals['type'] == 'vienetas':
                        barcode_vals['type'] = 'unit'
                    elif barcode_vals['type'] == u'pagrindinė pakuotė':
                        barcode_vals['type'] = 'primary_packaging'
                    elif barcode_vals['type'] == u'papildoma pakuotė':
                        barcode_vals['type'] = 'additional_packaging'
                    elif barcode_vals['type'].upper() == u'paletės barkodas'.upper():
                        barcode_vals['type'] = 'pallet_barcode'
                    elif barcode_vals['type'] == u'tarpinė pakuotė':
                        barcode_vals['type'] = 'additional_packaging'
                    
                    barcode = barcode_env.create_if_not_exist(barcode_vals)
                    barcodes += barcode
                barcodes_to_delete = product.barcode_ids - barcodes
                if barcodes_to_delete:
                    barcodes_to_delete.unlink()
               
                #pakuotės
                packings = packing_env.browse()
                for packing_dict in product_vals.get('AccountPacking', []):
                    packing_vals = {}
                    packing_vals['product_id'] = product.id
                    
                    packing_vals['type'] = packing_dict['packing_type']
                    if packing_vals['type'] == u'pirminė':
                        packing_vals['type'] = 'primary'
                    elif packing_vals['type'] == u'antrinė':
                        packing_vals['type'] = 'secondary'
                    elif packing_vals['type'] == u'tretinė':
                        packing_vals['type'] = 'tertiary'
                        
                    packing_vals['neto_weight'] = packing_dict['packing_neto_weight']
                    packing_vals['bruto_weight'] = packing_dict['packing_bruto_weight']
                    packing_vals['material'] = packing_dict['material']
                    
                    packing = packing_env.create_if_not_exist(packing_vals)
                    packings += packing
                    
                packings_to_delete = product.packing_ids - packings
                if packings_to_delete:
                    packings_to_delete.unlink()
                    
                if commit:
                    self.env.cr.commit() 
                msg = ctx.get('product_message', _('Success')) 
            except UserError as e:
                err_note = _('Failed to create product: %s') % (tools.ustr(e),)
                msg += err_note
                trb = traceback.format_exc() + '\n\n'
                processed = False
                result['error'] = True
                self.env.cr.rollback()
            except Exception as e:
                err_note = _('Failed to create product: %s') % (tools.ustr(e),)
                msg += err_note
                trb = traceback.format_exc() + '\n\n'
                processed = False
                result['error'] = True
                self.env.cr.rollback()
                
            result['result'] = msg
            
            for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
                if ctx.get(created_object_ids_name, []):
                    result['created_objects'].append({
                        'name': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['name'],
                        'object': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['object'],
                        'created_ids': ctx[created_object_ids_name]
                    })
            for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
                ctx[created_object_ids_name] = []
            
            
            results['products'].append(result)

        log_vals = {
            'processed': processed,
            'return_results': str(json.dumps(results, indent=2)),
            'traceback_string': trb
        }
        updated_vals = {}
        for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
            if ctx.get(updated_object_ids_name, []):
                updated_ids = []
                for updated_tuple in ctx[updated_object_ids_name]:
                    if updated_tuple[1] not in updated_ids:
                        updated_ids.append(updated_tuple[1])
                updated_vals[updated_object_ids_name] = [(6,0,updated_ids)]
        log_vals.update(updated_vals)
        self.write(log_vals)
        prod_obj.reset_tax_cache()
        return results
    
#     def process_intermediate_object_packing(self, cr, uid, id, context=None):
#         #nebenaudojama
#         if context is None:
#             context = {}
#         commit = not context.get('no_commit', False)
# #         log_obj = self.env('delivery.integration.log')
# #         usr_obj = self.env('res.users')
# #         ex_id_obj = self.env('ir.model.data')
#         prod_obj = self.env('product.product')
#         comp_obj = self.env('res.company')
# #         part_obj = self.env('res.partner')
#         own_obj = self.env('product.owner')
#         
#         results = {}
#         results['products'] = []
#         
#         intermediate = self.browse(cr, uid, id, context=context)
#         str_products = intermediate.received_values
#         try:
#             list_of_product_vals = json.loads(str_products)
#         except:
#             json_acceptable_string = str_products.replace("'", "\"")
#             list_of_product_vals = json.loads(json_acceptable_string)
#         processed = True
#         ctx = context.copy()
#         
#         for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
#             ctx[created_object_ids_name] = []
#             
#         for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
#             ctx[updated_object_ids_name] = []
#             
#         ctx['intermediate_id'] = id
#         ctx['update_type'] = True
#         trb = ''
#         for product_vals in list_of_product_vals:
#             msg = ''
#             result = {
#                 'created_objects': [],
#                 'result': _('Product was created successfully'),
#                 'product': product_vals['external_product_id']
#             }
#             try:
#                 vals = {}
#                 vals['external_product_id'] = product_vals['external_product_id']
#                 if 'product_name' in product_vals:
#                     vals['name'] = product_vals['product_name']
#                 if 'product_default_code' in product_vals:
#                     vals['default_code'] = product_vals['product_default_code']
#                 if 'product_weight' in product_vals:
#                     vals['weight'] = product_vals['product_weight']
#                 if 'product_standart_price' in product_vals:
#                     vals['standard_price'] = product_vals['product_standart_price']
#                                                 
#                 vals['type_of_product'] = product_vals.get('product_type', 'package')
#                 if 'active' in product_vals.keys():
#                     if product_vals['active'] == 'Y':
#                         vals['active'] = True
#                     elif product_vals['active'] == 'N':
#                         vals['active'] = False
#                         
#                 if 'firm_id' in product_vals.keys():
#                     comp_ids = comp_obj.search(cr, uid, [
#                         ('company_code','=',product_vals['firm_id'])
#                     ], context=context)
#                     if comp_ids:
#                         vals['company_id'] = comp_ids[0]
#                     else:
#                         raise UserError(_('No Company found with code %s') %product_vals['firm_id'])
#                 
# #                 if 'owner_id' in product_vals.keys():
# #                     part_ids = part_obj.search(cr, uid, [
# #                         ('owner_code','=',product_vals['owner_id'])
# #                     ], context=context)
# #                     if part_ids:
# #                         vals['owner_id'] = part_ids[0]
#                 if 'external_owner_id' in product_vals.keys():
#                     owner_vals = {
#                         'product_owner_external_id': product_vals['external_owner_id']
#                     }
#                     if 'owner_code' in product_vals.keys():
#                         owner_vals['owner_code'] = product_vals['owner_code']
#                     owner_id = own_obj.create_owner(cr, uid, owner_vals, context=context)
#                     if owner_id:
#                         vals['owner_id'] = owner_id
#                     
#                 prod_obj.create_product(
#                     cr, uid, vals, context=ctx
#                 )
#                 if commit:
#                     cr.commit() 
#                 msg = ctx.get('product_message', _('Success')) 
#             except UserError as e:
#                 err_note = _('Failed to create product: %s') % (tools.ustr(e),)
#                 msg += err_note
#                 trb = traceback.format_exc() + '\n\n'
#                 processed = False
#                 cr.rollback()
#             except Exception as e:
#                 err_note = _('Failed to create product: %s') % (tools.ustr(e),)
#                 msg += err_note
#                 trb = traceback.format_exc() + '\n\n'
#                 processed = False
#                 cr.rollback()
#                 
# #             result['message'] = msg
#             result['result'] = msg
#             
#             for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
#                 if ctx.get(created_object_ids_name, []):
#                     result['created_objects'].append({
#                         'name': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['name'],
#                         'object': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['object'],
#                         'created_ids': ctx[created_object_ids_name]
#                     })
#             for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
#                 ctx[created_object_ids_name] = []
#             
#             
#             results['products'].append(result)
#         log_vals = {
#             'processed': processed,
#             'return_results': str(json.dumps(results, indent=2)),
#             'traceback': trb
#         }
#         updated_vals = {}
#         for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
#             if ctx.get(updated_object_ids_name, []):
#                 updated_ids = []
#                 for updated_tuple in ctx[updated_object_ids_name]:
#                     if updated_tuple[1] not in updated_ids:
#                         updated_ids.append(updated_tuple[1])
#                 updated_vals[updated_object_ids_name] = [(6,0,updated_ids)]
# #         log_obj.write(cr, uid, [log_id], {
# #             'returned_information': str(json.dumps(res, indent=2)),
# #             'traceback': trb
# #         }, context=context)
#         log_vals.update(updated_vals)
#         self.write(cr, uid, [id], log_vals, context=context)
# 
#         return results

    @api.multi
    def process_intermediate_object_quantity(self):
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        ctx = context.copy()
        ctx['from_xmlrpc'] = True
        part_obj = self.env['res.partner']
        prod_obj = self.env['product.product']
        part_stck_obj = self.env['sanitex.product.partner.stock']
        comp_obj = self.env['res.company']
        
        results = {}
        results['quantities'] = []
        list_of_quantities_vals = self.get_received_values_as_dict()
        updated_stock_ids = []
        for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
            ctx[created_object_ids_name] = []
        
        for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
            ctx[updated_object_ids_name] = []
        processed = True
        trb = ''
        for product_stock_dict in list_of_quantities_vals:
            msg = ''
            result = {
                'external_product_id': product_stock_dict['external_product_id'],
                'external_customer_id': product_stock_dict['external_customer_id'],
                'created_objects': [],
                'result': _('Stock was created successfully'),
            }
            result['error'] = False    
            try:
#             if True:
                stocks = {}
                address = part_obj.search([
                    ('external_customer_address_id','=',product_stock_dict['external_customer_address_id'])
                ], limit=1)
                
                #PRODUCT
                product_vals = {
                    'external_product_id': product_stock_dict['external_product_id'],
                }
                if 'product_weight' in product_stock_dict.keys():
                    product_vals['weight'] = product_stock_dict['product_weight']
                if 'product_name' in product_stock_dict.keys():
                    product_vals['name'] = product_stock_dict['product_name']
                if 'product_default_code' in product_stock_dict.keys():
                    product_vals['default_code'] = product_stock_dict['product_default_code']
                                                
                product_vals['type_of_product'] = product_stock_dict.get('product_type', 'package')

                product = prod_obj.with_context(ctx).create_product(product_vals)
                
                if address:
                    stocks['partner_id'] = address.id
                else:
                    stocks['external_posid_id'] = product_stock_dict['external_customer_address_id']
                
                stocks['product_id'] = product.id
                stocks['additional_qty_available'] = product_stock_dict['product_qty']
                stocks['intermediate_id'] = self.id
                        
                if 'firm_id' in product_stock_dict.keys():
                    comp = comp_obj.search([
                        ('company_code','=',product_stock_dict['firm_id'])
                    ], limit=1)
                    if comp:
                        stocks['company_id'] = comp.id
                    else:
                        raise UserError(_('No Company found with code %s') %product_stock_dict['firm_id'])

                if address:
                    no_address = False
                    partner = address.id
                else:
                    no_address = True
                    partner = product_stock_dict['external_customer_address_id']
                    
                
                part_stck_obj.replace_quantity(
                    partner, product.id, product_stock_dict['product_qty'],
                    price=product_stock_dict['product_standart_price'], no_address=no_address
                )
                    
                msg = _('Customer stock was successfully updated')
                if commit:
                    self.env.cr.commit()
            except UserError as e:
                err_note = _('Failed to create partner stock line: %s') % (tools.ustr(e),)
                msg += err_note
                trb += traceback.format_exc() + '\n\n'
                processed = False
                result['error'] = True
                self.env.cr.rollback()
            except Exception as e:
                err_note = _('Failed to create partner stock line: %s') % (tools.ustr(e),)
                msg += err_note
                trb += traceback.format_exc() + '\n\n'
                processed = False
                result['error'] = True
                self.env.cr.rollback()
            
            result['result'] = msg
            
            for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
                if ctx.get(created_object_ids_name, []):
                    result['created_objects'].append({
                        'name': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['name'],
                        'object': ROUTE_IMPORT_CREATE_OBJECTS[created_object_ids_name]['object'],
                        'created_ids': ctx[created_object_ids_name]
                    })
            for created_object_ids_name in ROUTE_IMPORT_CREATE_OBJECTS.keys():
                ctx[created_object_ids_name] = []
            
            results['quantities'].append(result)
        
            
        updated_vals = {
            'returned_information': str(json.dumps(results, indent=2)),
            'traceback_string': trb.strip(),
            'updated_customer_stocks': [(6,0,updated_stock_ids)]
        }
        log_vals = {
            'processed': processed,
            'return_results': str(json.dumps(results, indent=2)),
            'traceback_string': trb.strip(),
        }
        updated_vals = {}
        for updated_object_ids_name in ROUTE_IMPORT_UPDATE_OBJECTS.keys():
            if ctx.get(updated_object_ids_name, []):
                updated_ids = []
                for updated_tuple in ctx[updated_object_ids_name]:
                    if updated_tuple[1] not in updated_ids:
                        updated_ids.append(updated_tuple[1])
                updated_vals[updated_object_ids_name] = [(6,0,updated_ids)]
        log_vals.update(updated_vals)
        self.write(log_vals)
        return results

    @api.multi
    def process_intermediate_object_ivaz(self):
        if self.route_to_ivaz_id:
            self.route_to_ivaz_id.send_route_to_ivaz(False)
        elif self.transportation_order_to_ivaz_id and self.invoice_id:
            self.invoice_id.export_invoice_to_ivaz(self.transportation_order_to_ivaz_id)
        else:
            raise UserError(_('Route does not exist anymore'))
        return True
    
    @api.multi
    def get_tare_document_status(self, server, token, headers):
        response = requests.get(server, headers=headers)
        if response.content == 404:
            time.sleep(15)
            response = requests.get(server, headers=headers)
        return response.status_code, response.content
    
    @api.multi
    def process_intermediate_object_tare(self):
        if self.processed:
            return True
        context = self.env.context or {}
        if context.get('doing_intermediate_cron', False) and self.tare_document_id:
            return True
        mv_env = self.env['stock.move']
        trb = ''
        msg = self.return_results or ''
        processed = False
        try:
            company = self.env['res.users'].browse(self.env.uid).company_id
            if not company.export_tare_document:
                raise UserError(_('To export tare documents you need to check tare export field in company\'s %s settings') %company.name)
            server = company.tare_export_server
            token = company.tare_export_token
            source = company.tare_export_source
            
            if not server:
                raise UserError(_('To export tare documents you need to fill in tare export server in company\'s %s settings') %company.name)
            if not token:
                raise UserError(_('To export tare documents you need to fill in tare export server\'s token in company\'s %s settings') %company.name)
            if not source:
                raise UserError(_('To export tare documents you need to fill in tare export server\'s source in company\'s %s settings') %company.name)
            
            headers = {
                'Content-type': 'application/json',
                'access-token': token
            }
            moves = mv_env.search([('intermediate_for_tare_export_id','=',self.id)])
            moves_dict = moves.to_dict_for_export(id=str(self.repeat), source=source)[0]
            self.write({
                # 'tare_document_source': moves_dict['source'],
                # 'tare_document_id': moves_dict['documentid'],
                'received_values_show': _('MOVES: ') + ', '.join(str(move.id) for move in moves) \
                    + '\n\n' + str(json.dumps(moves_dict, indent=2)).encode('utf-8').decode('unicode-escape')
            })
            self.env.cr.commit()
            response = requests.post(server, data=json.dumps(moves_dict), headers=headers)
            msg += _('POST result: ') +'\n' + str(response.status_code)
            if  response.status_code != 200:
                msg += '\n' + str(response.content)
            if response.status_code == 200 or response.status_code == 409:
                if response.status_code == 200:
                    self.write({
                        'tare_document_source': moves_dict['source'],
                        'tare_document_id': moves_dict['documentid'],
                    })
                    self.env.cr.commit()
                status, content = self.get_tare_document_status(
                    server+'/'+moves_dict['source']+'/'+moves_dict['documentid'], token, headers
                )
                msg += '\n' + ('-------------- %s ----------------\n' % utc_str_to_local_str()) + _('STATUS for (%s/%s) result:') % (moves_dict['source'], moves_dict['documentid']) + '\n' + str(status)
                
                if status != 200:
                    msg += '\n' +  str(content)
                else:
                    processed = True
                    moves.write({'tare_document_exported': True})
        except UserError as e:
            err_note = _('Failed to export tare documents: %s') % (tools.ustr(e),)
            msg += err_note
            trb += traceback.format_exc() + '\n\n'
            processed = False
            self.env.cr.rollback()
#             raise
        except Exception as e:
            err_note = _('Failed to export tare documents: %s') % (tools.ustr(e),)
            msg += err_note
            trb += traceback.format_exc() + '\n\n'
            processed = False
            self.env.cr.rollback()
#             raise
        vals = {
            'return_results': msg,
            'processed': processed,
            'traceback_string': trb,
        }
        self.write(vals)
        return True

    @api.multi
    def process_intermediate_iceberg_object(self):
        iceberg_integration_env = self.env['iceberg.integration']
        list_of_quantities_vals = self.get_received_values_as_dict()
        iceberg_integration_env.set_data(list_of_quantities_vals, self)

    @api.multi
    def process_additional_intermediate_object(self):
        return {}

    @api.multi
    def process_intermediate_object(self):
        # if type(id) == type([]):
        #     id = id[0]

        iceberg_integration_env = self.env['iceberg.integration']

        context = self.env.context or {}
        ctx = context.copy()
        ctx['active_test'] = False
        ctx['mail_create_nosubscribe'] = True
        ctx['mail_track_log_only'] = True
        ctx['mail_create_nolog'] = True
        ctx['find_ignored'] = True
        ctx['recompute'] = False
        ctx['import_bls'] = False

        next_process_in = 0
        next_process_at = None
        obj = self.read(['function', 'repeat', 'count', 'datetime', 'next_process_at', 'next_process_in'])[0]

        start_time = datetime.now()
        repeat = 0#obj['repeat'] or 0
        # self.write({'repeat': repeat + 1})
        self = self.with_context(ctx)
        iceberg_types = [type_tuple[0] for type_tuple in iceberg_integration_env.get_iceberg_integration_function_selection()]
        

        res = {}
        if obj['function'] == 'CreateRoute':
            res = self.process_intermediate_object_route()
        elif obj['function'] == 'CreateOrder':
            res = self.process_intermediate_object_order()
        elif obj['function'] == 'CreateInvoice':
            res = self.process_intermediate_object_invoice()
        elif obj['function'] == 'OrderExternalPackets':
            res = self.process_intermediate_object_route_packets()
        elif obj['function'] == 'CreatePackage':
            res = self.process_intermediate_object_package()
        elif obj['function'] == 'create_packing':
            res = self.process_intermediate_object_packing_new()
        elif obj['function'] == 'quantity_by_customer':
            res = self.process_intermediate_object_quantity()
        elif obj['function'] == 'CreateClient':
            res = self.process_intermediate_object_client()
        elif obj['function'] == 'CreatePOSID':
            res = self.process_intermediate_object_posid()
        elif obj['function'] == 'IVAZexport':
            res = self.process_intermediate_object_ivaz()
        elif obj['function'] == 'CreateOwner':
            res = self.process_intermediate_object_owner()
        elif obj['function'] == 'CreateDOSLocation':
            res = self.process_intermediate_object_dos_location()
        elif obj['function'] == 'TareDocumentExport':
            self.check_status()
            res = self.process_intermediate_object_tare()
        elif obj['function'] in iceberg_types:
            res = self.process_intermediate_iceberg_object()
        else:
            self.process_additional_intermediate_object()
            
        end_time = datetime.now()
        skip = False
        if obj['count'] >= 4:
            skip = True
            if obj['next_process_in'] and obj['next_process_in'] > 0:
                next_process_in = obj['next_process_in'] * 2
            else:
                next_process_in = 1
            next_process_at = end_time + timedelta(minutes=next_process_in)
        # self.write({
        #     'start_time': start_time,
        #     'end_time': end_time,
        #     'duration': (end_time-start_time).seconds,
        #     'duration2': (end_time-datetime.strptime(obj['datetime'], '%Y-%m-%d %H:%M:%S')).days * 24 * 60 + (end_time-datetime.strptime(obj['datetime'], '%Y-%m-%d %H:%M:%S')).seconds/60,
        #     'count': obj['count'] + 1,
        #     'skip': skip,
        # })
        sql = '''
            UPDATE
                stock_route_integration_intermediate
            SET
                start_time = %s,
                end_time = %s,
                duration = %s, 
                duration2 = %s, 
                count = %s, 
                skip = %s,
                repeat = %s,
                next_process_in = %s,
                next_process_at = %s
            WHERE
                id = %s
        '''
        self.env.cr.execute(sql, (
            start_time,
            end_time,
            (end_time-start_time).seconds,
            (end_time-datetime.strptime(obj['datetime'], '%Y-%m-%d %H:%M:%S')).days * 24 * 60 + (end_time-datetime.strptime(obj['datetime'], '%Y-%m-%d %H:%M:%S')).seconds/60,
            obj['count'] + 1,
            skip,
            repeat,
            next_process_in,
            next_process_at,
            self.id
        ))
        self.env.clear()
        return res

    @api.multi
    def process_intermediate_objects(self):
        context = self.env.context or {}
        company = self.env['res.users'].browse(self.env.uid).company_id
        lang = company.import_language
        if lang and lang != context.get('lang', ''):
            intermediates = self.with_context(lang=lang)
        else:
            intermediates = self
        result = []
        for intermediate in intermediates:
            result.append(intermediate.process_intermediate_object())
        return result

    @api.multi
    def lock_and_process_intermediate_object(self, lock_cursor, job_cursor):
        sql = '''
            SELECT
                processed,
                function,
                lock_id
            FROM
                stock_route_integration_intermediate
            WHERE
                id = %s
        '''
        self.env.cr.execute(sql, (self.id,))
        result = self.env.cr.fetchall()
        if not result[0][0]:
            if not result[0][2]:
                lock = self.env['stock.route.integration.intermediate.lock'].create({'intermediate_id': self.id})
                self.env.cr.execute('''
                    UPDATE 
                         stock_route_integration_intermediate
                    SET
                        lock_id = %s
                    WHERE
                        id = %s
                    ''', (lock.id, self.id))
                self.env.cr.commit()
                lock_id = lock.id
            else:
                lock_id = result[0][2]
#             lock_cursor = self.env.registry.cursor()
#             job_cursor = self.env.registry.cursor()
            try:
                lock_cursor.execute("""SELECT *
                                   FROM stock_route_integration_intermediate_lock
                                   WHERE id=%s
                                   FOR UPDATE NOWAIT""",
                               (str(lock_id),), log_exceptions=False)
                locked_action = lock_cursor.fetchone()
                if not locked_action:
                    _logger.info("Integration `%s` already executed by another process/thread (%s). Skipping IT" % (
                        str(self.id), result[0][1]
                    ))
                    lock_cursor.commit()
#                     lock_cursor.close()
                    job_cursor.commit()
#                     job_cursor.close()
                    time.sleep(1)
                    return
                try:
                    integration = self.with_env(self.env(cr=job_cursor))
                    integration.with_context(recompute=False).process_intermediate_object()
                except Exception as e:
                    raise
            except psycopg2.OperationalError as e:
                if e.pgcode == '55P03':
                    # Class 55: Object not in prerequisite state; 55P03: lock_not_available
                    _logger.info("Integration `%s` already executed by another process/thread (%s). Skipping it" % (
                        str(self.id), result[0][1]
                    ))
                else:
                    # Unexpected OperationalError
                    raise
            finally:
                lock_cursor.commit()
#                 lock_cursor.close()
                job_cursor.commit()
#                 job_cursor.close()


    @api.multi
    def process_intermediate_objects_cron(self, cron=False):
        context = self.env.context or {}
        result = []
        company = self.env['res.users'].browse(self.env.uid).company_id
        lang = company.import_language
        if lang and lang != context.get('lang', ''):
            intermediates = self.with_context(lang=lang)
        else:
            intermediates = self
        show_log = False
        if company.log_cron:
            show_log = True
        count = len(intermediates)
        i = 0
        
        lock_cursor = self.env.registry.cursor()
        job_cursor = self.env.registry.cursor()
        
        for intermediate in intermediates:
            if show_log:
                i += 1
                _logger.info('Process intermediate object %s (ID: %s) -- %s / %s' % (
                    context.get('types', str([])), str(intermediate.id), str(i), str(count))
                )
            try:
                if not cron:
                    result.append(intermediate.process_intermediate_object())
                else:
                    result.append(intermediate.lock_and_process_intermediate_object(lock_cursor, job_cursor))
                self.env.cr.commit()
            except:
                if show_log:
                    trb = traceback.format_exc()
                    _logger.info(trb.encode('utf-8').decode('unicode-escape'))
                    self.env.cr.rollback()
                pass
            
        lock_cursor.close()
        job_cursor.close()
            
        return result

    @api.multi
    def process_intermediate_objects_threaded(self):
#         check_result = self.check_intermediate_vals(cr, uid, ids, context=context)
#         if check_result:
#             return check_result
        context = self.env.context or {}
        usr_obj = self.env['res.users']
        company = usr_obj.browse(self.env.uid).company_id
        if company and company.do_not_process_intermediate_objects and not context.get('force_process_intermediate', False):
            return False
        t = threading.Thread(target=self.thread_process_intermediate_objects)
        t.start()
        return False

    @api.multi
    def thread_process_intermediate_objects(self):
        context = self.env.context or {}
        with Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            try:
                if context.get('force_process_intermediate', False):                    
                    self.process_intermediate_objects_cron()
                else:
                    self.process_intermediate_objects()
                new_cr.commit()
            finally:
                new_cr.close()
        return True

    @api.model
    def cron_process_objects(self, types=None, default_domain=None):
        if types is None:
            types = []
        if default_domain is None:
            default_domain = []

        context = self.env.context or {}
        ctx = context.copy()
        ctx['doing_intermediate_cron'] = True
        usr_obj = self.env['res.users']
        company = usr_obj.browse(self.env.uid).company_id
        domain = default_domain + [
            ('processed','=',False),
            ('skip','=',False)
        ]
        if types:
            ctx['types'] = str(types)
            domain.append(('function','in',types))
        if company.cron_domain:
            domain += safe_eval(company.cron_domain)
        intermediates = self.search(domain, order='datetime, id',
            limit = 250
        )
        intermediates.with_context(ctx).process_intermediate_objects_cron(cron=True)
        self.env['product.product'].clear_default_cashe()
        return True

    @api.multi
    def unlink(self):
        context = self.env.context or {}
        if not context.get('allow_to_delete_integration_obj', False) and self.env.uid != SUPERUSER_ID:
            raise UserError(_('You can\'t delete integration objects %s') % ', '.join([str(id) for id in self.mapped('id')]))
        return super(StockRouteIntegrationIntermediate, self).unlink()

    @api.multi
    def write(self, vals):
        # if 'return_results' in vals.keys():
        #     try:
        #         vals['return_results'] = vals['return_results'].encode('utf-8').decode('unicode-escape')
        #     except:
        #         pass

        if 'received_values_show' not in vals.keys() and 'received_values' in vals.keys():
            try:
                vals['received_values_show'] = vals['received_values'].encode('utf-8').decode('unicode-escape')
            except:
                pass

        if 'traceback_string' in vals.keys():
            try:
                vals['traceback_string'] = vals['traceback_string'].encode('utf-8')
            except:
                pass
        return super(StockRouteIntegrationIntermediate, self).write(vals)

    @api.model
    def create(self, vals):
        lock_env = self.env['stock.route.integration.intermediate.lock']
        lock = lock_env.create({})
        vals['lock_id'] = lock.id
        if 'received_values_show' not in vals.keys() and 'received_values' in vals.keys():
            try:
                vals['received_values_show'] = vals['received_values'].encode('utf-8').decode('unicode-escape')
            except:
                pass

        if 'traceback_string' in vals.keys():
            vals['traceback_string'] = vals['traceback_string'].encode('utf-8')
        intermediate = super(StockRouteIntegrationIntermediate, self).create(vals)
        lock.write({'intermediate_id': intermediate.id})
        return intermediate

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        res = super(StockRouteIntegrationIntermediate, self).read(fields=fields, load=load)
        if 'received_values_show' in fields:
            for r in res:
                if not r['received_values_show']:
                    r['received_values_show'] = self.read(['received_values'])[0]['received_values']

        return res
    
    @api.multi
    def check_status(self):
        company = self.env['res.users'].browse(self.env.uid).company_id
        server = company.tare_export_server
        token = company.tare_export_token
        if not server:
            raise UserError(_('To export tare documents you need to fill in tare export server in company\'s %s settings') %company.name)
        if not token:
            raise UserError(_('To export tare documents you need to fill in tare export server\'s token in company\'s %s settings') %company.name)
        for intermediate in self:
            if not intermediate.tare_document_source or not intermediate.tare_document_id:
                continue
            headers = {
                'Content-type': 'application/json',
                'access-token': token
            }
            
            status, content = self.get_tare_document_status(
                server+'/'+intermediate.tare_document_source+'/'+intermediate.tare_document_id, token, headers
            )
            
            msg = '\n' + ('-------------- %s ----------------\n' % utc_str_to_local_str()) + _('STATUS for (%s/%s) result:') % (intermediate.tare_document_source, intermediate.tare_document_id) + '\n' + str(status) + '\n'
            
            if status != 200:
                msg += '\n' +  str(content)
                processed = False
            else:
                processed = True
                moves = self.env['stock.move'].search([('intermediate_for_tare_export_id','=',self.id)])
                moves.write({'tare_document_exported': True})
            self.write({
                'return_results': self.return_results + msg,
                'processed': processed
            })
        
        
#------------------- TESTAVIMUI ---------------------
#     @api.multi
#     def report_stuck_integration_objs_test(self):
# #         [('id','=',124194)]
#         self.env['stock.route.integration.intermediate'].report_stuck_integration_objs()
#         return True
             
    @api.model
    def post_monitoring_data(self, data_dict):
        company = self.env['res.users'].browse(self.env.uid).company_id
        server = company.monitoring_server
        token = company.monitoring_token
        if not server:
            _logger.info(
                "Monitoring server is undefined in company settings."
            )
        if not server:
            _logger.info(
                "Monitoring token is undefined in company settings."
            )
        
        headers = {
            'Content-type': 'application/json',
            'access-token': token
        }

        try:
            response = requests.post(server, data=json.dumps(data_dict), headers=headers)
            if response.status_code != 200:
                _logger.info(
                    "Monitoring data posting has failed. Status code: %s. Data dictionary: %s" % (
                        response.status_code, data_dict
                    )
                )
        except:
            _logger.info(
                "Unexpected error while posting monitoring data. Data dictionary: %s" % (
                    data_dict
                )
            )
            
        return True
             
    @api.model
    def report_stuck_integration_objs(self):
        obj_by_function_dict = {
            'CreateOwner': 'owner',
            'CreateClient': 'client',
            'CreatePOSID': 'posid',
            'CreatePackage': 'package',
            'CreateOrder': 'sale',
            'CreateInvoice': 'invoice',
            'CreateRoute': 'route',
            'create_packing': 'product',
            'quantity_by_customer': 'external_product_id,external_customer_id',
        }
        
        def form_json_dict_list_of_stuck_objects(integration_intermediate, running):
            integration_intermediate_read = integration_intermediate.read([
                'function', 'duration2',
            ])[0]
            
            if running:
                error_msg = "Function %s was processed to long. Operation duration: %s" % (
                    integration_intermediate_read['function'], integration_intermediate_read['duration2']
                )
            else:
                error_msg = "Function %s is still running. It is processing longer than expected." % (
                    integration_intermediate_read['function']
                )
            
            return [{
                "messageId": str(uuid.uuid1()),
                "headers": {
                    "inboundProperties": {},
                    "outboundProperties": {},
                    "invocationProperties": {
                        "documentID": str(integration_intermediate_read['id']),
                        "flowInput": ""
                    }
                },
                "payload": "",
                "flow": integration_intermediate_read['function'],
                "destination": None,
                "level": "info",
                "timeStamp": utc_str_to_local_str(),
                "exceptionType": "",
                "exceptionClass": "",
                "exceptionMessage": error_msg,
                "exceptionStackTrace": ""
            }]
            
        def form_json_dict_list_of_failed_objects(integration_intermediate):
            integration_intermediate_read = integration_intermediate.read([
                'function', 'return_results', 'traceback_string'
            ])[0]
            
            res = []
            
            try:
                integration_return_dict = json.loads(integration_intermediate_read["return_results"])
            except:
                json_acceptable_string = integration_intermediate_read["return_results"].replace("'", "\"")
                integration_return_dict = json.loads(json_acceptable_string)
                
            if not integration_return_dict:
                 return []
             
            for integration_return_obj_dict in list(integration_return_dict.values())[0]:
                if not integration_return_obj_dict.get('error', False):
                    continue
                
                obj_name = obj_by_function_dict.get(
                    integration_intermediate_read['function'], ""
                )
                if ',' in obj_name:
                    obj_name_list = obj_name.split(',')
                    id_doc = "%s, %s" % (
                        integration_return_obj_dict.get(obj_name_list[0], ""),
                        integration_return_obj_dict.get(obj_name_list[1], ""),
                    )
                else:
                    id_doc =   integration_return_obj_dict.get(obj_name, "")
                    
                flow_input = ""
                received_vals_list = integration_intermediate.get_received_values_as_dict()
                
                if ',' in id_doc:
                    splited_id_doc = id_doc.split(' ,')
                    value_to_find = splited_id_doc[0]
                    value_to_find2 = splited_id_doc[1]
                else:
                    value_to_find = id_doc
                    value_to_find2 = None
                for one_received_vals_obj_dict in received_vals_list:
                    obj_dict_vals_list = list(one_received_vals_obj_dict.values())
                    if value_to_find in obj_dict_vals_list\
                     and (not value_to_find2 or value_to_find2 in obj_dict_vals_list):
                        flow_input = str(json.dumps(one_received_vals_obj_dict, indent=2))
                        break
                
                vals = {
                    "messageId": str(uuid.uuid1()),
                    "headers": {
                        "inboundProperties": {},
                        "outboundProperties": {},
                        "invocationProperties": {
                            "documentID": id_doc,
                            "flowInput": flow_input or ""
                        }
                    },
                    "payload": "",
                    "flow": integration_intermediate_read['function'],
                    "destination": None,
                    "level": "warning",
                    "timeStamp": utc_str_to_local_str(),
                    "exceptionType": "",
                    "exceptionClass": "",
                    "exceptionMessage": integration_return_obj_dict.get('result', ""),
                    "exceptionStackTrace": integration_intermediate_read['traceback_string'] or "",
                }
                res.append(vals)
            
            return res
                 
         
        users_env = self.env['res.users']
        company = users_env.browse(self._uid).company_id
        stuck_integration_obj_time = company.stuck_integration_obj_time
#         functions = [
#             'CreateOrder','CreateRoute','CreateInvoice','CreatePackage',
#             'create_packing','quantity_by_customer','CreateClient','CreatePartner',
#             'CreatePOSID','CreateOwner','CreateSupplierInvoice'
#         ]
         
         
        time_bound = (
            datetime.now() - timedelta(seconds=stuck_integration_obj_time*60)
        ).strftime('%Y-%m-%d %H:%M:%S')
        integration_intermediate_recs = self.search([
            ('create_date','<=',time_bound),
            ('process_time_checked','=',False),
            ('function','in',tuple(obj_by_function_dict.keys()))
        ])
        for integration_intermediate in integration_intermediate_recs:
            integration_intermediate.write({
                'process_time_checked': True
            })
             
            integration_intermediate_read = integration_intermediate.read([
                'processed', 'duration2', 'count', 'traceback_string'
            ])[0]
             
            json_dict = {}
            if integration_intermediate_read['processed']:
                if integration_intermediate_read['duration2'] < stuck_integration_obj_time:
                    continue
                else:
                    json_dict_list = form_json_dict_list_of_stuck_objects(integration_intermediate, False)
            else:
                if integration_intermediate_read['count'] >= 2\
                 and integration_intermediate_read['traceback_string']:
                    json_dict_list = form_json_dict_list_of_failed_objects(integration_intermediate)
                else:
                    json_dict_list = form_json_dict_list_of_stuck_objects(integration_intermediate, True)

            for json_dict in json_dict_list:
                self.post_monitoring_data(json_dict)
             
        return True    
        
    
class StockLocation(models.Model):
    _name = 'stock.location'
    _inherit = ["stock.location", 'mail.thread']

    @api.one
    @api.depends('name', 'location_id.name')
    def _complete_name_sani(self):
        """ Forms complete name of location from parent location to child location.
        @return: Dictionary of values
        """
        self.complete_name = self.name_get()[0][1]

    # def _get_sublocations_sani(self):
    #     """ return all sublocations of the given stock locations (included) """
    #     if context is None:
    #         context = {}
    #     context_with_inactive = context.copy()
    #     context_with_inactive['active_test'] = False
    #     return self.search(cr, uid, [('id', 'child_of', ids)], context=context_with_inactive)
    
    driver_code = fields.Char('Driver Code', size=64, track_visibility='onchange')
    contract_no = fields.Char('Contract No', size=64)
    car_capacity = fields.Float('Car Capacity', digits=(16,2), track_visibility='onchange')
    license_plate = fields.Char('Car License Plate', size=64, track_visibility='onchange')
    external_driver_id = fields.Char('External ID', size=64,
        track_visibility='onchange'
    )
    driver = fields.Boolean('Driver', track_visibility='onchange', default=False)
    owner_id = fields.Many2one(
        'res.partner', 'Company', readonly=True,
        track_visibility='onchange'
    )
    owner_name = fields.Char('Company Name', size=256, readonly=True)
    owner_code = fields.Char('Company Code', size=32, readonly=True)
    owner_selected = fields.Boolean('Owner Selected', readonly=True,
        track_visibility='onchange', default=False
    )
    name = fields.Char('Location Name', required=True,
        track_visibility='onchange', translate=False
    )
    location_id = fields.Many2one(
        'stock.location', 'Parent Location',
        track_visibility='onchange',
        ondelete='cascade'
    )
    allowed_driver_location_ids = fields.Many2many(
        'stock.location', 'driver_stock_location_rel',
        'driver_id', 'location_id', 'Allowed Locations',
        track_visibility='onchange'
    )
    code = fields.Char('Code', size=128)
    complete_name = fields.Char(string="Full Location Name", compute='_complete_name_sani', store=True)
    gate_id = fields.Many2one('stock.gate', "Gate")
    mismatch_location = fields.Boolean('Mismatch Location', default=False)
    product_exchange_location = fields.Boolean(
        'Product Exchange Location', default=False,
        help="Location which is used to change product stock to related one"
    )
    trailer = fields.Char('Trailer')
    total_debt = fields.Integer('Total Debt', readonly=True, help='Total debt of driver.', default=0)
    region_ids = fields.Many2many('stock.region', 'region_driver_rel', 'driver_id', 'region_id', 'Regions')
    load_address = fields.Char('Address', size=128)
    id_version = fields.Char('POD Version', size=128, readonly=True)
    username = fields.Char('Username', size=128, readonly=True)
    password = fields.Char('Password', size=128, readonly=True)
    phone = fields.Char('Phone', size=16, readonly=True)
    email = fields.Char('Email', size=128, readonly=True)
    enabled = fields.Boolean("Enabled", default=True)
    dos_location = fields.Boolean('DOS Location', readonly=True, help='Shows if this is DOS warehouse location.')
    country_code = fields.Char('Country Code', size=8, readonly=True)
    vat_code = fields.Char('VAT Code', size=32, readonly=True)
    reg_code = fields.Char('Registration Code', size=32, readonly=True)
    name_en = fields.Char('Name(EN)', size=64)
    name_lt = fields.Char('Name(LT)', size=64)
    name_ru = fields.Char('Name(RU)', size=64)
    name_ee = fields.Char('Name(EE)', size=64)
    name_lv = fields.Char('Name(LV)', size=64)


    @api.model
    def get_empty_carrier_dict_from_driver(self):
        carrier_dict = self.env['res.partner'].get_empty_carrier_dict_from_carrier()
        carrier_dict.update({
            'Driver': '',
            'CarNumber': '',
            'TrailNumber': '',
        })
        return carrier_dict
    

    @api.multi
    def _export_rows(self, fields):
        if self.env.user.company_id.user_faster_export:
            res = self.env['ir.model'].export_rows_with_psql(fields, self)
        else:
            res = super(StockLocation, self)._export_rows(fields)
        return res
    

    @api.multi
    def get_carrier_dict_from_driver(self):
        carrier_dict = self.owner_id.get_carrier_dict_from_carrier()
        carrier_dict.update({
            'Driver': self and self.name or '',
            'CarNumber': self and self.license_plate or '',
            'TrailNumber': self and self.trailer or '',
        })
        return carrier_dict

    @api.multi
    def to_dict_for_rest_integration(self):
        driver_dict = {
            'id': self.external_driver_id or str(self.id*10000),
            'driverid': str(self.id),
            'fullName': self.name or '',
            'fullname': self.name or '',
            'carrierorgid': self.owner_id and self.owner_id.external_customer_id or '',
            'maincarrierorgid': self.owner_id and self.owner_id.external_customer_id or '',
            'agreemen': self.contract_no or '',
            'active': self.active,
            'deleted': False, #Negali būti ištrintas
            'username': str(self.id*10000), #Laikinai
            'email': str(self.id*10000)+'@bls.lt', #Laikinai
            'carrierId': self.owner_id and self.owner_id.external_customer_id or '',
            'id_version': self.id_version,
        }
        return driver_dict

    @api.multi
    @api.constrains('code')
    def _check_location_code(self):
        for location in self:
            if location.code:
                locations = self.search([('code','=',location.code),('id','!=',location.id)])
                if locations:
                    raise ValidationError(_('There already exists location with code %s. Locations: %s') % (
                        location.code, ', '.join([location.name for location in locations])
                    ))

    @api.multi
    def get_picking_type(self, pick_type):
        type_obj = self.env['stock.picking.type']
        domain = [('code','=',pick_type)]
        wh = False
        if self:
            wh = self.get_location_warehouse_id()
            if wh:
                domain.append(('warehouse_id','=',wh.id))
        type_of_picking = type_obj.search(domain, limit=1)
        if not type_of_picking and wh:
            type_of_picking = type_obj.search([('code','=',pick_type)], limit=1)
        return type_of_picking and type_of_picking.id or False
    
    @api.multi
    def get_driver_wh_dict(self):
        return {'warehouseid': DRIVER_WAREHOUSE}
    
    @api.multi
    def get_warehouse_dict(self):
#         warehouse = self.get_location_warehouse_id()
#         warehouse
        d = {'warehouseid': self.code}
        return d
    
    @api.multi
    def get_driver_dict(self):
        d = {
            'driverid': self.driver_code or str(self.id) or '',
            'name': self.name or '',
            'organisationid': self.owner_code or '',
            'mainCarrierOrgId': self.owner_id and self.owner_id.external_customer_id or ''
        }
        return d

    @api.model
    def create_location_if_not_exist(self, location_code, create_wh_if_not_exists=False):
        if not self.search([('code','=',location_code)]):
            wh_code = location_code[:-1]
            warehouse = self.env['stock.warehouse'].search([('code','=',wh_code)])
            if not warehouse:
                if create_wh_if_not_exists and False:
                    warehouse = self.env['stock.warehouse'].create_wh_if_not_exists(wh_code)
                else:
                    raise UserError(_('There are no warehouse with code %s in odoo system') % wh_code)
            if not self.search([('code','=',location_code)]):
                location_vals = self.default_get(self._fields)
                location_vals['name'] = location_code
                location_vals['code'] = location_code
                location_vals['location_id'] = warehouse.lot_stock_id.id
                return self.create(location_vals)
            else:
                return self.search([('code','=',location_code)], limit=1)
        else:
            return self.search([('code','=',location_code)], limit=1)

    @api.multi
    def get_location_warehouse_id(self):
        wh_obj = self.env['stock.warehouse']
        loc = self
        warehouse = False
        while loc and not warehouse:
            warehouse = wh_obj.search([('lot_stock_id','=',loc.id)], limit=1)
            if not warehouse:
                loc = loc.location_id or False
            else:
                loc = False
        return warehouse or False

    @api.multi
    def get_driver_info(self):
        # Naudojama atnaujinti stock move reikšmes

        info = {
            'driver_code': '',
            'driver_company_name': '',
            'driver_company_code': ''
        }
        if self:
            info['driver_code'] = self.driver_code or ''
            if self.owner_id:
                info['driver_company_name'] = self.owner_id.name or ''
                info['driver_company_code'] = self.owner_id.ref or ''
        return info

    @api.model
    def get_location_warehouse_id_from_code(self, code, return_location_id=False, create_if_not_exists=False):
        location = self.search([('code','=',code)], limit=1)
        if not location:
            if create_if_not_exists:
                location = self.create_location_if_not_exist(code, create_wh_if_not_exists=True)
            else:
                raise UserError(_('There are no location with code %s in odoo system') %code)
        if return_location_id:
            return location, location.get_location_warehouse_id()
        else:
            return location.get_location_warehouse_id()

    @api.model
    def create_or_update_location(self, values):
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        inter_obj = self.env['stock.route.integration.intermediate']

        datetimes = time.strftime('%Y-%m-%d %H:%M:%S')

        ctx_en = context.copy()
        ctx_en['lang'] = 'en_US'

        itermediate = inter_obj.create({
            'datetime': datetimes,
            'function': 'CreateDOSLocation',
            'received_values': str(json.dumps(values, indent=2)),
            'processed': False
        })
        if commit:
            self.env.cr.commit()
        itermediate.with_context(from_rest_api=True).process_intermediate_objects()
        return itermediate.id
    
    # def create_driver(self, cr, uid, vals, context=None):
    #     if context is None:
    #         context = {}
    #     ids = self.search(cr, uid, [
    #         ('external_driver_id','=',vals['external_driver_id'])
    #     ], context=context)
    #     location_vals = vals.copy()
    #     location_vals['usage'] = 'internal'
    #     location_vals['driver'] = 'True'
    #     if location_vals.get('external_carrier_id', ''):
    #         partner_vals = {
    #             'name': location_vals['carrier_name'],
    #             'driving_contract_number': location_vals.get('driving_contract_number', ''),
    #             'external_customer_id': location_vals['external_carrier_id']
    #         }
    #         del location_vals['carrier_name']
    #         del location_vals['external_carrier_id']
    #         if location_vals.get('driving_contract_number', ''):
    #             del location_vals['driving_contract_number']
    #         partner_id = self.env('res.partner').create_partner(
    #             cr, uid, partner_vals, context=context
    #         )
    #         location_vals['owner_id'] = partner_id
    #     if ids:
    #         id = ids[0]
    #         self.write(cr, uid, [id], location_vals, context=context)
    #         if 'updated_driver_ids' in context:
    #             context['updated_driver_ids'].append((location_vals['external_driver_id'], id))
    #
    #     else:
    #         location_vals['intermediate_id'] = context.get('intermediate_id', False)
    #         location_vals['log_id'] = context.get('log_id', False)
    #         id = self.create(cr, uid, location_vals, context=context)
    #         if 'created_driver_ids' in context:
    #             context['created_driver_ids'].append((location_vals['external_driver_id'], id))
    #     self.env.cr.commit()
    #     context['license_plate'] = self.browse(cr, uid, id, context=context).license_plate
    #     return id

    @api.model
    def default_get(self, fields):
        context = self.env.context or {}
        res = super(StockLocation, self).default_get(fields)
        if context.get('driver_menu', False):
            res['driver'] = True
        return res
    
    @api.model
    def update_vals(self, vals):
        if vals.get('owner_id', False):
            owner = self.env['res.partner'].browse(vals['owner_id'])
            vals['owner_code'] = owner.ref
            vals['owner_name'] = owner.name
        if vals.get('owner_id', False):
            vals['owner_selected'] = True
        if vals.get('driver', False):
            vals['location_id'] = self.get_driver_parent_id()

    @api.multi
    def fill_in_missing_vals(self):
        for location in self:
            vals = {'owner_id': location.owner_id and location.owner_id.id or False}
            self.update_vals(vals)
            location.write(vals)

    @api.multi
    def write(self, vals):
        context = self.env.context or {}
        if not context.get('allow_to_edit_location', False) and self.env.uid != 1:
            for location in self:
                if not location.driver:
                    raise UserError(_('You are not allowed to edit locations(%s, ID: %s)') %(location.name, str(location.id)))
        self.update_vals(vals)
        
        
        if set(vals.keys()) & {'name','owner_id','contract_no','active'}:
            vals['id_version'] = get_local_time_timestamp()
        
#         for location in self:
#             if location.driver or vals.get('driver', False)\
#              and set(vals.keys()) & {'name','owner_id','contract_no','active'}:
#                 vals['id_version'] = get_local_time_timestamp()
#             elif 'id_version' in vals.keys():
#                 del vals['id_version']
        
        if len(self) == 1 and 'id_version' in vals.keys():
            res = super(StockLocation, self).write(vals)
        elif set(vals.keys()) & {'name','owner_id','contract_no','active'}:
            for location in self:
                if location.driver or vals.get('driver', False):
                    vals['id_version'] = get_local_time_timestamp()
                else:
                    del vals['id_version']
                res = super(StockLocation, location).write(vals)
        else:
            res = super(StockLocation, self).write(vals)
        
        for location in self:
            if location.owner_id and location.driver:
                location.owner_id.write({'carrier': True})
            
        if set(vals.keys()).intersection({'name', 'owner_id'}):
            self.check_driver()
        if 'active' in vals.keys() and not vals['active']:
            self.raise_if_has_any_debt()
        return res
    
    @api.multi
    def check_driver(self):
        # Vairuotojo patikrinimas
        # patikrinama ar jau nėra sukurtas vairuotojas
        # su tuo pačiu vardu ir ta pačia įmone
        
        for driver in self:
            if driver.owner_id:
                if self.search([
                    ('name','=',driver.name),
                    ('owner_id','=',driver.owner_id.id),
                    ('id','!=',driver.id)
                ]):
                    raise UserError(_('Driver %s with company \'%s\' already exist.') %(driver.name, driver.owner_id.name))

    @api.multi
    def unlink(self):
        context = self.env.context or {}
        if not context.get('allow_to_delete_location', False):
            raise UserError(_('You are not allowed to unlink drivers/locations (IDs: %s)') % str(self.mapped('id')))
        return super(StockLocation, self).unlink()

    @api.multi
    def raise_if_has_any_debt(self):
        for driver in self:
            if driver.driver and driver.get_drivers_debt_all():
                raise UserError(_('Action is forbidden. Driver %s still has tare debt.') % driver.name)

    @api.model
    def create(self, vals):
        self.update_vals(vals)
        if not vals.get('total_debt', False):
            vals['total_debt'] = 0.0
        if vals.get('driver', False):
            vals['id_version'] = get_local_time_timestamp()
        if 'total_debt' not in vals:
            vals['total_debt'] = 0
        location = super(StockLocation, self).create(vals)
        if set(vals.keys()).intersection({'name', 'owner_id'}):
            location.check_driver()
        if location.owner_id and location.driver:
            location.owner_id.write({'carrier': True})
            
        return location

    @api.multi
    def get_products(self):
        stock_obj = self.env['sanitex.product.location.stock']
        res = []
        quants = stock_obj.search([
            ('location_id','=',self.id),
            ('qty_available','>',0)
        ], order='product_code')
        for stock in quants.read(['product_id', 'qty_available']):
            res.append((stock['product_id'][0], stock['qty_available']))
        return res

    @api.model
    def update_args(self, args):
        context = self.env.context or {}
        wh_obj = self.env['stock.warehouse']

        if context.get('args_updated', False):
            return True

        if context.get('related_warehouse_id', False):
            # Grąžina tik tas vietas,kurios yra susijusios su per contextą paduodamu sandėliu
            ctx = context.copy()
            del ctx['related_warehouse_id']
            args.append(('id','in',wh_obj.browse(
                context['related_warehouse_id']
            ).with_context(ctx).get_warehouse_locations()))

        if context.get('only_user_allowed_return_locations', False):
            # Grąžina tik tas vietas kurios yra skirtos atsargų grąžinimams
            wh_obj = self.env['stock.warehouse']
            whs = wh_obj.search([])
            ids = []
            for wh in whs:
                if wh.wh_return_stock_loc_id:
                    ids.append(wh.wh_return_stock_loc_id.id)
                args.append(('id','in',ids))
        if context.get('drivers_allowed_in_region', False):
            # Grąžina tik tas vietas kurios yra priskirtos einamam regionui arba nėra priskirtos jokiam regionui
            usr_obj = self.env['res.users']
            user = usr_obj.browse(self.env.uid)
            if user.default_region_id:
                args.append('|')
                args.append(('id','in',user.default_region_id.driver_ids.mapped('id')))
                args.append(('region_ids','=',False))

        return True

    @api.model
    def get_drivers_debt_by_name(self, driver_name):
        driver = self.search([('name','=',driver_name),('driver','=',True)])
        if not driver:
            driver = self.with_context(active_test=False).search([('name','=',driver_name),('driver','=',True)])
        if driver:
            if len(driver) > 1:
                return 'too_many'
            else:
                return driver.total_debt
        else:
            return 'not_found'


    @api.model
    def get_driver_debt_for_rest_api(self, driver_name):

        interm_env = self.env['stock.route.integration.intermediate']
        receive_vals = _('Received driver parameter') + ': '
        result_vals = ''
        processed = True
        trb = ''
        
        if isinstance(driver_name, str):
            receive_vals += driver_name
        else:
            receive_vals += str(driver_name)
        
        intermediate = interm_env.create({
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
            'function': 'IcebergGetDriverTotalDebt',
            'received_values': receive_vals,
            'processed': False
        })
        self.env.cr.commit()
        try:
            res = self.get_drivers_debt_by_name(driver_name)
            if isinstance(res, int) or isinstance(res, float):
                result = {'debt': res}
            else:
                result = {
                    'code': res,
                    'message': {
                        'too_many': _('There are more than one driver with name %s') % driver_name,
                        'not_found': _('Driver %s not found') % driver_name
                    }[res]
                }
            result_vals += _('Result: ') + '\n\n' + str(json.dumps(result, indent=2))
        except Exception as e:
            err_note = _('Failed to return drivers debt: %s') % (tools.ustr(e),)
            result_vals += err_note
            processed = False
            trb += traceback.format_exc() + '\n\n'
            self.env.cr.rollback()

        intermediate.write({
            'processed': processed,
            'return_results': result_vals,
            'traceback_string': trb
        })
        self.env.cr.commit()
        return result

    @api.model
    def _search(
        self, args, offset=0, limit=None,
        order=None, count=False,
        access_rights_uid=None
    ):
    
        context = self.env.context or {}
        ctx = context.copy()
        self.with_context(ctx).update_args(args)
        return super(StockLocation, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self.env.context or {}
        ctx = context.copy()
        self.with_context(ctx).update_args(args)
        res = super(StockLocation, self).search(
            args, offset=offset, limit=limit,
            order=order, count=count
        )

        return res

    @api.multi
    def name_get(self):
        context = self.env.context or {}
        lang = context.get('lang', False)
        res = []
        for location in self:
            name = location.name or ''
            if location.driver and context.get('show_driver_company_info_in_name', False):
                name_list = [name]
                if location.owner_code:
                    name_list.append(location.owner_code or '')
                if location.owner_id:
                    name_list.append(location.owner_id.name or '')
                name = ', '.join(name_list)
            elif lang and location.dos_location:
                if lang in ('ee', 'et_EE') and location.name_ee:
                    name = location.name_ee
                elif lang in ('lt', 'lt_LT') and location.name_lt:
                    name = location.name_lt
                elif lang in ('lv', 'lv_LV') and location.name_lv:
                    name = location.name_lv
                elif lang in ('ru', 'ru_RU') and location.name_ru:
                    name = location.name_ru
                elif lang in ('en', 'en_EN', 'en_US') and location.name_en:
                    name = location.name_en
                else:
                    name = location.name
                if location.code:
                    name = '[' + location.code + '] ' + name
            else:
                if location.code and location.code != name:
                    name = '[' + location.code + '] ' + name

            res.append((location['id'], name))
        return res
    
    @api.model
    def get_dos_location(self):
        # Gražina standartine vietą, kuri bus naudojama stock.move ir stock.picking
        # kai operacija vyks tap\rp atlas sandėlio ir dos sandėlio

        return self.env.ref('config_sanitex_delivery.dos_location')
    
    @api.model
    def get_driver_parent_id(self):
        model_obj = self.env['ir.model.data']
        model = model_obj.search([
            ('module','=','config_sanitex_delivery'),
            ('model','=','stock.location'),
            ('name','=','driver_parent_location')
        ], limit=1)
        location_id = False
        if model:
            location_id = model.res_id
        return location_id
    
    @api.multi
    def get_drivers_debt(self, product_id):
        debt = 0
        driver_debt = self.env['sanitex.product.location.stock'].search([
            ('product_id','=',product_id),('location_id','=',self.id)
        ], limit=1)
        if driver_debt:
            debt = driver_debt.qty_available
        return debt

    # @api.multi
    # def get_drivers_debt_all_by_owner(self, owner_id):
    #     # tare_credit = {
    #     #     'Inf_Prek': debt_line[1],
    #     #     'ProductDescription': debt_line[2],
    #     #     'Price': debt_line[3],
    #     #     'TareCredit': debt_line[4],
    #     # }
    #     sql = '''
    #         SELECT
    #             spls.id,
    #             spls.product_code,
    #             spls.product_name,
    #             pt.standard_price,
    #             spls.qty_available
    #         FROM
    #             sanitex_product_location_stock spls
    #             JOIN product_product pp on (pp.id = spls.product_id)
    #             JOIN product_template pt on (pt.id = pp.product_tmpl_id)
    #         WHERE
    #             spls.location_id = %s
    #             AND pp.owner_id = %s
    #             AND spls.qty_available > 0.0
    #         ORDER BY
    #             spsl.product_code
    #     '''
    #     self.env.cr.execute(sql, (self.id, owner_id))
    #     result = self.env.cr.fetchall()
    #     return result
    
    @api.multi
    def get_drivers_debt_all(self, owner=False):
        domain = [
            ('location_id','=',self.id),('qty_available','>',0.0)
        ]
        if owner:
            domain.append(('owner_id','=',owner.id))
        return self.env['sanitex.product.location.stock'].search(domain)

    @api.multi
    def get_drivers_debt_all_with_sql(self):
        results = []
        if self:
            search_sql = '''
                SELECT
                    product_id,
                    sum
                FROM
                    (SELECT
                        product_id,
                        SUM(
                            CASE
                                WHEN location_id = %s THEN -product_uom_qty
                                WHEN location_dest_id = %s THEN product_uom_qty
                            END
                        ) as sum
                    FROM
                        stock_move
                    WHERE
                        (location_id=%s 
                            OR location_dest_id = %s)
                        AND state='done'
                    GROUP BY
                        product_id) as tb1
                WHERE
                    tb1.sum > 0.0
            '''
            search_where = (self.id, self.id, self.id, self.id)
            self.env.cr.execute(search_sql, search_where)
            results = self.env.cr.fetchall()
        return dict(results)
    
    @api.multi
    def update_drivers_total_debt(self):
        # vairuotojui atnaujinama bendra skola 
        # t.y. - visų taros skolų bendra suma
        
        for driver in self.sudo().filtered('driver'):
            all_debt = driver.get_drivers_debt_all()
            debt = sum(all_debt.mapped('qty_available'))
            if driver.total_debt != debt:
                driver.write({'total_debt': debt})
    
    @api.multi
    def open_drivers_open_moves(self):
        form_view = self.env.ref('config_sanitex_delivery.view_stock_move_report_form', False)[0]
        tree_view = self.env.ref('config_sanitex_delivery.view_stock_move_report_tree', False)[0]
        return {
                'name': _('%s Debt') % ', '.join(self.mapped('name')),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'stock.move',
                'views': [(tree_view.id,'tree'),(form_view.id,'form')],
                'type': 'ir.actions.act_window',
                'domain': [
                    ('state','=','done'),
                    ('location_dest_id','in',self.mapped('id')),
                    ('open','=',True)
                ]
            }


    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """ search full name and barcode """
        if args is None:
            args = []
        recs = self.search(['|', ('code', operator, name), '|', ('owner_code', operator, name), '|', ('name', operator, name), ('owner_name', operator, name)] + args, limit=limit)
        
        return recs.name_get() 
    
    @api.model
    def get_pod_domain(self, obj):
        return [('driver','=',True)]
    
    @api.multi
    def set_version(self):
        for location in self:
            self._cr.execute('''
                UPDATE
                    stock_location
                SET
                    id_version = %s
                WHERE id = %s
            ''', (get_local_time_timestamp(), location.id))
        return True
    
    @api.multi
    def to_dict_for_pod_integration(self, obj):
        return {
            'id': self.external_driver_id or str(self.id*10000),
            'fullName': self.name or '',
            'active': self.active,
            'deleted': False, #Negali būti ištrintas
            'username': self.username or str(self.id*10000),
            'email': self.email,
            'phone': self.phone,
            'password': self.password,
            'carrierId': self.owner_id and self.owner_id.ref or self.owner_id.external_customer_id or '',
            'enabled': self.enabled,
            'id_version': self.id_version,
        }
        
    @api.model
    def set_iceberg_data(self, data):
        external_id_driver = data['driverId']
        
        vals = {
            'active' : not data.get('deleted', False),
        }
        if data.get('name', False):
            vals['name'] = data['name']
        
        if data.get('phone', False):
            vals['phone'] = data['phone']
            
        if data.get('email', False):
            vals['email'] = data['email']
        
        if data.get('userName', False):
            vals['username'] = data['userName']
            
        if data.get('password', False):
            vals['password'] = data['password']
            
        if data.get('carrierId', False):
            partner_env = self.env['res.partner']
            carrier = partner_env.get_partner_by_carrier_id(data['carrierId'])
            # carrier = partner_env.search([
            #     ('carrier','=',True),
            #     ('external_customer_id','=',data['carrierId'])
            # ], limit=1)
            vals['owner_id'] = carrier and carrier.id or False
            
        if data.get('enabled', False):
            vals['enabled'] = data['enabled']
            
        driver = self.search([
            ('external_driver_id','=',external_id_driver),
            ('driver','=',True)
        ])
        if driver:
            driver.write(vals)
            res = _("Driver was updated successfully")
        else:
            vals['driver'] = True
            vals['external_driver_id'] = external_id_driver
            self.create(vals)
            res = _("Driver was created successfully")
            
        return res

class StockRegion(models.Model):
    _name = 'stock.region'
    _description = 'Regions for Warehouses'

    _rec_name = 'name'

    name = fields.Char('Name', size=128, required=True)
    warehouse_of_region_ids = fields.One2many('stock.warehouse', 'region_id', 'Warehouses')
    product_ids = fields.Many2many(
        'product.product', 'product_product_region_rel',
        'region_id', 'product_id', 'Products'
    )
    responsible_user_ids = fields.Many2many(
        'res.users', 'region_user_rel_ids', 'region_id',
        'user_id', 'Responsible Users'
    )
    location_id = fields.Many2one('stock.location', 'Main Location', domain=[('driver','=',False)])
    location_required = fields.Boolean('Location Required', default=False)
    driver_ids = fields.Many2many('stock.location', 'region_driver_rel',
        'region_id', 'driver_id', 'Drivers', domain=[('driver','=',True)]
    )
    active = fields.Boolean('Active', default=True)
    main_warehouse_name = fields.Char('Main Warehouse Name', size=64, readonly=True)
    return_location_id = fields.Many2one('stock.location', 'Return Location', domain=[('driver','=',False)])
    return_location_required = fields.Boolean('Return Location Required', default=False)



    @api.onchange('warehouse_of_region_ids')
    def onchange_warehouses(self):
        context = self.env.context or {}
        if context.get('skip_onchange', False):
            return
        self = self.sudo()
        self.product_ids = self.warehouse_of_region_ids.mapped('product_ids')
        self.responsible_user_ids = self.warehouse_of_region_ids.mapped('responsible_user_ids')
        if not self.warehouse_of_region_ids:
            if self.location_id:
                self.location_id = False
            if self.return_location_id:
                self.return_location_id = False
            self.location_required = False
            self.return_location_required = False
            return {'domain': {
                'location_id': [('id','>',1),('id','<',1)],
                'return_location_id': [('id','>',1),('id','<',1)]
            }}
        else:
            self.location_required = True
            self.return_location_required = True
            locations = self.warehouse_of_region_ids.mapped('lot_stock_id')
            allowed_locations = self.env['stock.location'].search([('location_id','child_of',locations.mapped('id'))])
            if self.location_id and self.location_id not in allowed_locations:
                self.location_id = False
            if self.return_location_id and self.return_location_id not in allowed_locations:
                self.return_location_id = False
            return {'domain': {
                'location_id': [
                    ('id','in',allowed_locations.mapped('id')),
                    '|',('active','=',True),('active','=',False)
                ], 
                'return_location_id': [
                    ('id','in',allowed_locations.mapped('id')),
                    '|',('active','=',True),('active','=',False)
                ]
            }}

    @api.model
    def update_vals(self, vals):
        if 'location_id' in vals:
            if vals['location_id']:
                vals['main_warehouse_name'] = \
                    self.env['stock.location'].browse(vals['location_id']).get_location_warehouse_id().name
            else:
                vals['main_warehouse_name'] = ''

    @api.model
    def create(self, vals):
        self.update_vals(vals)
        region = super(StockRegion, self).create(vals)
        region.onchange_warehouses()
        return region

    @api.multi
    def write(self, vals):
        self.update_vals(vals)
        res = super(StockRegion, self).write(vals)
        for region in self:
            region.with_context(skip_onchange=True).onchange_warehouses()
        return res
    
    @api.multi
    def get_main_location(self):
        if self.location_id:
            return self.location_id
        raise UserError(_('Region %s does not have main location filled in.') %self.name)

    @api.multi
    def get_return_location(self):
        if self.return_location_id:
            return self.return_location_id
        return self.get_main_location()

    @api.multi
    def get_all_warehouses_by_name(self):
        return self.main_warehouse_name, self.warehouse_of_region_ids.mapped('name')


class StockWarehouse(models.Model):
    _name = 'stock.warehouse'
    _inherit = ["stock.warehouse", 'mail.thread']

    product_ids = fields.Many2many(
        'product.product', 'product_product_warehouse_rel',
        'warehouse_id', 'product_id', 'Products',
        track_visibility='onchange'
    )
    prefix_for_route = fields.Char('Prefix for Route', size=32,
        track_visibility='onchange'
    )
    responsible_user_ids = fields.Many2many(
        'res.users', 'warehouse_user_rel_ids', 'user_id',
        'warehouse_id', 'Responsible Users',
        track_visibility='onchange'
    )
    code = fields.Char('Code', size=32, required=True,
        track_visibility='onchange'
    )
    name = fields.Char('Warehouse Name', required=True,
        track_visibility='onchange'
    )
    wh_output_stock_loc_id = fields.Many2one('stock.location',
        'Return location', track_visibility='onchange'
    )
    wh_return_stock_loc_id = fields.Many2one('stock.location',
        'Return location', track_visibility='onchange'
    )
    wh_defect_stock_loc_id = fields.Many2one('stock.location',
        'Defect location', track_visibility='onchange'
    )
    wh_mismatch_loc_id = fields.Many2one('stock.location',
        'Mismatch Location', track_visibility='onchange'
    )

    lot_stock_id = fields.Many2one('stock.location', 'Location Stock', domain=[])
    product_exchange_location_id = fields.Many2one(
        'stock.location', 'Product Exchange Location',
        help="Location which is used to change product stock to related one"
    )
    region_id = fields.Many2one('stock.region', 'Region')
    printer_ids = fields.Many2many('printer', 'warehouse_printer_rel', 'warehouse_id', 'printer_id', 'Printers')
    sequence_for_route_id = fields.Many2one('ir.sequence', 'Route Sequence')
    sequence_for_driver_picking_id = fields.Many2one('ir.sequence', 'Driver Picking Sequence')
    sequence_for_client_packing_id = fields.Many2one('ir.sequence', 'Client Packing Sequence')
    sequence_for_corection_id = fields.Many2one('ir.sequence', 'Internal Operation Sequence')
    document_setting_line_ids = fields.One2many('document.type.settings.line', 'warehouse_id', 'Document Setting Line')
    dos_warehouse = fields.Boolean('DoS Warehouse', readonly=True, default=False)


    # region = fields.Boolean('Region', default=_get_region)
    # warehouse_of_region_ids = fields.Many2many('stock.warehouse', 'warehouse_region_rel', 'region_id', 'warehouse_id', 'Warehouses')
    # regions_of_warehouse_ids = fields.Many2many('stock.warehouse', 'warehouse_region_rel', 'warehouse_id', 'region_id', 'Regions')

    @api.multi
    def update_sequences(self):
        seq_env = self.env['ir.sequence']
        for warehouse in self:
            warehouse_vals = {}
            seq_default_vals = seq_env.default_get(seq_env._fields)

            #Route
            sequence_for_route_vals = {
                'name': warehouse.name + ' Route',
                'prefix': 'Q'+warehouse.code
            }
            if not warehouse.sequence_for_route_id:
                route_seq_vals = seq_default_vals.copy()
                route_seq_vals.update(sequence_for_route_vals)
                route_seq_vals['padding'] = 6
                warehouse_vals['sequence_for_route_id'] = seq_env.create(route_seq_vals).id
            else:
                warehouse.sequence_for_route_id.write(sequence_for_route_vals)

            #Driver Picking
            sequence_for_driver_picking_vals = {
                'name': warehouse.name + ' Driver Picking',
                'prefix': 'T'+warehouse.code
            }
            if not warehouse.sequence_for_driver_picking_id:
                driver_picking_seq_vals = seq_default_vals.copy()
                driver_picking_seq_vals.update(sequence_for_driver_picking_vals)
                driver_picking_seq_vals['padding'] = 6
                warehouse_vals['sequence_for_driver_picking_id'] = seq_env.create(driver_picking_seq_vals).id
            else:
                warehouse.sequence_for_driver_picking_id.write(sequence_for_driver_picking_vals)

            #Client Packing
            sequence_for_client_packing_vals = {
                'name': warehouse.name + ' Client Packing',
                'prefix': 'TK'+warehouse.code[-1:]
            }
            if not warehouse.sequence_for_client_packing_id:
                client_packing_seq_vals = seq_default_vals.copy()
                client_packing_seq_vals.update(sequence_for_client_packing_vals)
                client_packing_seq_vals['padding'] = 6
                warehouse_vals['sequence_for_client_packing_id'] = seq_env.create(client_packing_seq_vals).id
            else:
                warehouse.sequence_for_client_packing_id.write(sequence_for_client_packing_vals)

            #Correction
            sequence_for_correction_vals = {
                'name': warehouse.name + ' Internal Operations',
                'prefix': ''+warehouse.code
            }
            if not warehouse.sequence_for_corection_id:
                correction_seq_vals = seq_default_vals.copy()
                correction_seq_vals.update(sequence_for_correction_vals)
                correction_seq_vals['padding'] = 6
                warehouse_vals['sequence_for_corection_id'] = seq_env.create(correction_seq_vals).id
            else:
                warehouse.sequence_for_corection_id.write(sequence_for_correction_vals)


            if warehouse_vals:
                warehouse.write(warehouse_vals)

    @api.multi
    def get_intermediate_location(self):
        # perkeliant prekes iš vieno sandėlio į kitą reikia jas nurašyti nuo pirmojo sandėlio,
        # bet prie antrojo neprirašyti tol kol nepatvirtintas gavimas, todėl perkeliama į tarpinę
        # vietą. Ši funkcija grąžina tą tarpinę vietą.
        
        return self.env.ref('config_sanitex_delivery.in_movement_stock_location')

    @api.multi
    def get_asn_location(self):
        # grąžina ASN vietą. Kadnagi jos šiame modulyje nėra, tai ši funkcija
        # suveiks tinkamai tik tada kai bus sudiegtas config_bls_stock modulis
        try:
            getattr(self, 'asn_location_id')
            return self.asn_location_id
        except:
            return self.env.ref('stock.location_production')

    @api.model
    def create(self, vals):
        if 'dos_warehouse' not in vals:
            vals['dos_warehouse'] = False
        warehouse = super(StockWarehouse, self).create(vals)
        if warehouse.lot_stock_id:
            lot = warehouse.lot_stock_id.location_id
            lot.sudo().write({
                'code': vals.get('code', '') + '_system'
            })
            warehouse.write({'lot_stock_id': lot.id})
        if warehouse.wh_output_stock_loc_id:
            warehouse.wh_output_stock_loc_id.sudo().write({
                'name': vals.get('code', '')+'1',
                'code': vals.get('code', '')+'1',
                'active': True
            })
        warehouse.write({
            'wh_return_stock_loc_id': self.env['stock.location'].sudo().create({
                'name': vals.get('code', '')+'6',
                'usage': 'internal',
                'location_id': warehouse.lot_stock_id.id,
                'code': vals.get('code', '')+'6',
                'active': True
            }).id
        })
        if warehouse.region_id:
            warehouse.region_id.onchange_warehouses()
        warehouse.update_sequences()
        return warehouse


    @api.model
    def _handle_renaming(self, warehouse, name, code, context=None):
        # pašalintas nereikalingas funkcionalumas, kuris dar ir klaidą mesdavo
        return True

    @api.multi
    def create_wh_if_not_exists(self, code):
        if not self.search([('code','=',code)]):
            context = self.env.context or {}
            wh_vals = self.default_get(self._fields)
            wh_vals['name'] = code
            wh_vals['code'] = code
            wh_vals['prefix_for_route'] = code
            wh_vals['dos_warehouse'] = context.get('dos_warehouse', False)
            wh = self.create(wh_vals)
            return wh
        else:
            return self.search([('code','=',code)], limit=1)

    @api.multi
    def get_warehouse_locations(self):
        loc_obj = self.env['stock.location']
        location_ids = []
        wh_location_ids = []
        if self.lot_stock_id:
            wh_location_ids.append(self.lot_stock_id.id)
        if wh_location_ids:
            location_ids = loc_obj.search([
                ('location_id','child_of',wh_location_ids)
            ]).mapped('id')
        if wh_location_ids and self.lot_stock_id:
            while self.lot_stock_id.id in location_ids:
                location_ids.remove(self.lot_stock_id.id)
        return location_ids

    @api.model
    def update_args(self, args):
        context = self.env.context or {}
        if context.get('args_updated', False):
            return True
        if not context.get('get_all_warehouses', False) and self.env.uid != 1:
            # Grąžina tik tuos sandėlius prie kurių priskirtas ieškantysis naudotojas
            if not context.get('warehouse_menu', False):
                args.append(('responsible_user_ids', 'in', [self.env.uid]))
            elif not self.env['res.users'].browse(self.env.uid).does_user_belong_to_group(GROUP_TO_SEE_ALL_WAREHOUSES):
                args.append(('responsible_user_ids','in',[self.env.uid]))
        return True

    @api.multi
    def fix_sequences(self):
        self.env['document.type'].generate_document_types()
        setting_env = self.env['document.type.settings']
        line_env = self.env['document.type.settings.line']
        draivas_settings = setting_env.search([
            ('document_type_id.code','=','config_sanitex_delivery.product_packing')
        ])
        if not draivas_settings:
            draivas_settings = setting_env.create({
                'document_type_id': self.env['document.type'].search([('code','=','config_sanitex_delivery.product_packing')]).id,
                'sequence_by': 'wh'
            })
        driver_transfer_settings = setting_env.search([
            ('document_type_id.code','=','config_sanitex_delivery.drivers_packing_transfer_act')
        ])
        if not driver_transfer_settings:
            driver_transfer_settings = setting_env.create({
                'document_type_id': self.env['document.type'].search([('code','=','config_sanitex_delivery.drivers_packing_transfer_act')]).id,
                'sequence_by': 'wh'
            })
        client_transfer_settings = setting_env.search([
            ('document_type_id.code','=','config_sanitex_delivery.stock_packing_report')
        ])
        if not client_transfer_settings:
            client_transfer_settings = setting_env.create({
                'document_type_id': self.env['document.type'].search([('code','=','config_sanitex_delivery.stock_packing_report')]).id,
                'sequence_by': 'wh'
            })
        correction_setting_settings = setting_env.search([
            ('document_type_id.code','=','config_sanitex_delivery.tare_to_driver_act')
        ])
        if not correction_setting_settings:
            correction_setting_settings = setting_env.create({
                'document_type_id': self.env['document.type'].search([('code','=','config_sanitex_delivery.tare_to_driver_act')]).id,
                'sequence_by': 'wh'
            })

        for warehouse in self:
            driver_transfer_line = warehouse.document_setting_line_ids.filtered(
                lambda rec_line: driver_transfer_settings in rec_line.document_type_settings_ids and correction_setting_settings in rec_line.document_type_settings_ids
            )
            if not driver_transfer_line:
                driver_transfer_line = line_env.create({
                    'document_type_settings_ids': [(6,0,[driver_transfer_settings.id, correction_setting_settings.id])],
                    'warehouse_id': warehouse.id
                })
            warehouse.sequence_for_driver_picking_id.write({
                'document_setting_line_id': driver_transfer_line.id,
                'last_number': 999999,
                'priority': 1
            })
            draivas_line = warehouse.document_setting_line_ids.filtered(lambda rec_line: rec_line.document_type_settings_ids == draivas_settings)
            if not draivas_line:
                draivas_line = line_env.create({
                    'document_type_settings_ids': [(6,0,[draivas_settings.id])],
                    'warehouse_id': warehouse.id
                })
            warehouse.sequence_for_route_id.write({
                'document_setting_line_id': draivas_line.id,
                'last_number': 999999,
                'priority': 1
            })
            client_line = warehouse.document_setting_line_ids.filtered(lambda rec_line: rec_line.document_type_settings_ids == client_transfer_settings)
            if not client_line:
                client_line = line_env.create({
                    'document_type_settings_ids': [(6,0,[client_transfer_settings.id])],
                    'warehouse_id': warehouse.id
                })
            warehouse.sequence_for_client_packing_id.write({
                'document_setting_line_id': client_line.id,
                'last_number': 999999,
                'priority': 1
            })
            # sequence_for_route_id = fields.Many2one('ir.sequence', 'Route Sequence')
            # sequence_for_driver_picking_id = fields.Many2one('ir.sequence', 'Driver Picking Sequence')
            # sequence_for_client_packing_id = fields.Many2one('ir.sequence', 'Client Packing Sequence')
            # sequence_for_corection_id

    @api.model
    def _search(
        self, args, offset=0, limit=None,
        order=None, count=False,
        access_rights_uid=None
    ):
        self.update_args(args)
        return super(StockWarehouse, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self.env.context or {}
        ctx = context.copy()
        self.update_args(args)
        ctx['args_updated'] = True
        return super(StockWarehouse, self.with_context(ctx)).search(
            args, offset=offset, limit=limit,
            order=order, count=count
        )

    @api.multi
    def write(self, vals):
        regions = self.env['stock.region'].browse([])
        if 'region_id' in vals.keys():
            for warehouse in self:
                regions += warehouse.region_id
        res = super(StockWarehouse, self).write(vals)
        if {'region_id', 'responsible_user_ids', 'product_ids'} & set(vals.keys()):
            for region in self.mapped('region_id') + regions:
                region.onchange_warehouses()
        # if {'name', 'code'} & set(vals.keys()):
            # self.update_sequences()
        return res

    @api.multi
    def get_not_received_containers(self):
        cont_env = self.env['account.invoice.container']
        return cont_env.with_context(not_received_containers=True).search([
            ('picking_warehouse_id','=',self.id)
        ])


class StockRoute(models.Model):

    _name = 'stock.route'
    _description = 'Stock Route'
    _inherit = ['mail.thread']
    
#     _track = {
#         'state': {
#             'config_sanitex_delivery.mt_route_stage': lambda self, cr, uid, obj, ctx=None: obj['state'] in ['draft', 'released', 'closed'],
#         },
#     } 

    @api.model
    def _get_wh(self):
        usr_obj = self.env['res.users']
        user = usr_obj.browse(self.env.uid)
        return user.get_main_warehouse_id()
    
#     def _get_name(self, cr, uid, context=None):
#         seq_obj = self.env('ir.sequence')
#         wh_obj = self.env('stock.warehouse')
#          
#         seq_ids = seq_obj.search(cr, uid, [
#             ('code','=','released_route'),
#         ], context=context)
#         name = ''
#         prefix = ''
#         wh_id = self._get_wh(cr, uid, context=context)
#         wh = wh_obj.browse(cr, uid, wh_id, context=context)
#         if len(seq_ids)>0:
#             name = prefix + seq_obj.get_id(cr, uid, seq_ids[0])
#         return name
    
    @api.model
    def _get_state2(self):
        return [
            ('planned', _('Planned')), 
            ('released', _('Comming')),
            ('closed', _('Received'))
        ]
            
    @api.depends('fully_received_warehouses_ids_char')
    def _calc_receiver_state(self):
        usr_obj = self.env['res.users']
        user = usr_obj.browse(self.env.uid)
        default_warehouse_id = user.default_warehouse_id and user.default_warehouse_id.id or False
        for route in self:
            if route.state == 'draft':
                state = 'planned'
            elif route.state == 'closed':
                state = 'closed'
            else:
                if not default_warehouse_id:
                    state = 'released'
                else:
                    warehouse_char = route.fully_received_warehouses_ids_char or ''
                    if 'id'+str(default_warehouse_id)+'id' in warehouse_char:
                        state = 'closed'
                    else:
                        state = 'released'
            route.state_receive = state
    
    @api.model
    def get_route_states_selection(self):
        return [
            ('draft', _('Being Released')),
            ('released', _('Route started')),
            ('closed', _('Closed'))
        ]

    @api.depends('document_count', 'document_count_left_to_check')
    def _calc_document_count_scan(self):
        for route in self:
            route.document_count_left_to_check_info_line = str(route.document_count - route.document_count_left_to_check) \
                + ' ' + _('out of') + ' ' + str(route.document_count)
      
    id = fields.Integer('ID', readonly=True)
    routeid = fields.Char('Route Id', size=32, track_visibility='onchange')
    description = fields.Text('Description', track_visibility='onchange',
        states={'released':[('readonly',True)],'closed':[('readonly',True)]}
    )
    picking_id = fields.Many2one(
        'stock.picking', 'Picking for Driver',
        track_visibility='onchange', readonly=True
    )
    picking_ids = fields.One2many(
        'stock.picking', 'transfer_to_driver_picking_for_route_id', 'Picking for Driver',
        track_visibility='onchange', readonly=True
    )
    move_ids = fields.One2many(
        'stock.move', 'route_id', 'Moves',
        track_visibility='onchange', readonly=True
    )
    packing_for_client_ids = fields.One2many(
        'stock.packing', 'route_id', 'Packing for client',
        states={'released':[('readonly',False)],'closed':[('readonly',True)]},
        track_visibility='onchange'
    )
    date = fields.Date(
        'Date', required=True,
        states={'released':[('readonly',True)],'closed':[('readonly',True)]},
        track_visibility='onchange'
    )
    receiver = fields.Char('Route', size=128,
        states={'released':[('readonly',True)],'closed':[('readonly',True)]},
        track_visibility='onchange'
    )
    sender1_id = fields.Many2one(
        'res.partner', 'Sender',
        readonly=True, track_visibility='onchange'
    )
    sender2_id = fields.Many2one(
        'res.partner', 'Sender2',
        readonly=True, track_visibility='onchange'
    )
    weight = fields.Float(
        'Weight', digits=(16,2),
        states={'released':[('readonly',True)],'closed':[('readonly',True)]},
        track_visibility='onchange'
    )
    location_id = fields.Many2one(
        'stock.location', 'Driver',
        readonly=True, track_visibility='onchange'
    )
    license_plate = fields.Char(
        'License Plate',
        states={'released':[('readonly',True)],'closed':[('readonly',True)]},
        track_visibility='onchange'
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse', 'Release Warehouse',
        states={'released':[('readonly',True)],'closed':[('readonly',True)]},
        readonly=True, track_visibility='onchange', default=_get_wh
    )
    destination_warehouse_id = fields.Many2one(
        'stock.warehouse', 'Destination Warehouse',
        states={'released':[('readonly',True)],'closed':[('readonly',True)]},
        track_visibility='onchange'
    )
    return_warehouse_id = fields.Many2one(
        'stock.warehouse', 'Return Warehouse',
        states={'released':[('readonly',True)],'closed':[('readonly',True)]},
        track_visibility='onchange', default=_get_wh
    )
    state = fields.Selection(
        get_route_states_selection, 'State', readonly=True, track_visibility='onchange',
        default='draft'
    )
    release_user_id = fields.Many2one(
        'res.users', 'Release User', readonly=True, track_visibility='onchange'
    )
    returned_picking_id = fields.Many2one(
        'stock.picking', 'Returned from Driver', track_visibility='onchange',
        states={'released':[('readonly',True)],'closed':[('readonly',True)]}
    )
    returned_picking_ids = fields.One2many(
        'stock.picking', 'return_from_driver_picking_for_route_id', 'Returned from Driver',
        track_visibility='onchange', states={'released':[('readonly',True)],'closed':[('readonly',True)]}
    )
    intermediate_id = fields.Many2one(
        'stock.route.integration.intermediate', 'Created by', readonly=True,
        states={'released':[('readonly',True)],'closed':[('readonly',True)]}
    )
    type = fields.Selection([
            ('internal', 'Interbranch (IBL)'),
            ('out', 'Distributive (DST)'),
            ('mixed', 'Mixed')
        ], 'Type', required=True,
        states={'released':[('readonly',True)],'closed':[('readonly',True)]},
        track_visibility='onchange'
    )
    name = fields.Char(
        'Packing Delivery Picking No.', size=64,
        readonly=True, track_visibility='onchange', default=''
    )
    route_length = fields.Float(
        'Route Length', digits=(16,2),
        states={'released':[('readonly',True)],'closed':[('readonly',True)]},
        track_visibility='onchange'
    )
    departure_time = fields.Datetime(
        'Departure Date, Time', readonly=True,
        track_visibility='onchange'
    )
    return_time = fields.Datetime('Return Time', readonly=True, track_visibility='onchange')
    route_no = fields.Char(
        'Route No.', size=64,
        states={'released':[('readonly',True)],'closed':[('readonly',True)]},
        help='Route number from routing system', track_visibility='onchange'
    )
    automatic = fields.Boolean(
        'Automatic', readonly=True,
        help='Checked if routing was created using integration',
        track_visibility='onchange'
    )
    automatic_full_used = fields.Boolean(
        'Full Used', readonly=True,
        track_visibility='onchange'
    )
    unused_documents = fields.Integer('Unused documents', readonly=True)
    route_name = fields.Char(
        'Route Name', size=128,
        states={'released':[('readonly',True)],'closed':[('readonly',True)]},
        track_visibility='onchange'
    )
    out_picking_id = fields.Many2one('stock.picking', 'Out Picking', readonly=True, track_visibility='onchange')
    in_picking_id = fields.Many2one('stock.picking', 'In Picking', readonly=True, track_visibility='onchange')
    to_wh_or_route_picking_ids = fields.One2many('stock.picking', 'transfer_route_id', 'Transfer to', track_visibility='onchange')
    external_route_id = fields.Char('External ID', size=64, readonly=True)
    transfer_to_route_id = fields.One2many(
        'stock.picking', 'transfer_to_route_id',
        'Transfered from another routes', readonly=True
    )
    destination_filled = fields.Boolean('Destination Filled', readonly=True, default=False)
    return_location_id = fields.Many2one('stock.location', 'Return Location',
        states={'draft':[('required',True)],'released':[('required',True)],'closed':[('readonly',True)]},
    )
    collection_package_ids = fields.One2many(
        'stock.package', 'collection_route_id', 'Collection Packages',
        track_visibility='onchange',
        readonly=True,
    )
    delivery_package_ids = fields.Many2many(
        'stock.package', 'delivery_package_route_rel', 'delivery_route_id',
        'package_id', 'Delivery Packages', track_visibility='onchange',
        readonly=True,
    )
    company_id = fields.Many2one('res.company', 'Company',
        states={'released':[('readonly',True)],'closed':[('readonly',True)]}
    )
    driver_name = fields.Char('Driver Name', size=256,
        help='Filled in if there are no driver in the system with such name',
        states={'released':[('readonly',True)],'closed':[('readonly',True)]},
        track_visibility='onchange'
    )
    driver_company_id = fields.Many2one(related='location_id.owner_id',
         relation='res.partner', string='Driver Company', readonly=True
    )
    source_location_id = fields.Many2one('stock.location', 'Status', required=True,
        states={'released':[('readonly',True)],'closed':[('readonly',True)]},
        track_visibility='onchange'
    )
    trailer = fields.Char('Trailer', size=128, track_visibility='onchange',
        states={'released':[('readonly',True)],'closed':[('readonly',True)]}
    )
    internal_route_for_route_id = fields.Many2one('stock.route', 'Made by', readonly=True)
    driver_picked = fields.Boolean('Driver Picked', readonly=True, track_visibility='onchange', default=False)
    packings_generated = fields.Boolean('Packing Generated', readonly=True, track_visibility='onchange', default=False)
    products_picked = fields.Boolean('Products Picked', readonly=True, track_visibility='onchange', default=False)
    sale_count = fields.Integer('Sale Count', readonly=True)
    shipping_warehouse_id_filter = fields.Char('Field to filter by Sales Shipping Warehouse', readonly=True, size=256)
    picking_warehouse_id_filter = fields.Char('Field to filter by Sales Picking Warehouse', readonly=True, size=256)
    sale_ids = fields.One2many('sale.order', 'route_id', string='Transportation Tasks', track_visibility='onchange',
       states={'released':[('readonly',True)],'closed':[('readonly',True)]}
    )
    state_receive = fields.Selection(_get_state2, "State", store=False, compute='_calc_receiver_state')
    fully_received_warehouses_ids_char = fields.Char('Field do calculate Receive state', size=256, readonly=True)
    container_line_ids = fields.One2many('stock.route.container', 'route_id', 'Containers', readonly=True)
    invoice_ids = fields.Many2many(
        'account.invoice', 'stock_route_invoice_rel', 'route_id', 'invoice_id', 'Documents', readonly=True
    )
    tasks_extended = fields.Boolean('Task Extended', readonly=True, default=False, help='Used to show all tasks are extended')
    drections_for_drive_report = fields.Char('Receiver in Drive Report', size=256,
        states={'released':[('readonly',True)],'closed':[('readonly',True)]},
        help='This information will be filled in in drive report in receiver part'
    )
    region_id = fields.Many2one('stock.region', 'Region', readonly=True, track_visibility='onchange')
    version_id = fields.Integer('Version ID', readonly=True, help='Used for REST integration to export routes')
    route_template_id = fields.Many2one('stock.route.template', 'Route Template', readonly=True)
    route_id_str = fields.Char('Route ID', size=32, readonly=True)
    hide_close_button = fields.Boolean("Hide Close Button", readonly=True, default=True)
    picking_number = fields.Char('Tare Transfer to Driver Document Number', readonly=True)
    return_picking_created = fields.Boolean('Return From Driver Done', readonly=True, default=False)
    number_of_packing_for_client_lines = fields.Char("Number of Packing for client lines", readonly=True, default="0")
    id_version = fields.Char('POD Version', size=128, readonly=True)
    act_status = fields.Char('Acts (D, C)', readonly=True, size=32, help='Shows status of driver and client acts', 
        default='—   —'
    )
    return_move_ids = fields.One2many('stock.move', 'return_for_route_id', 'Tare from driver', readonly=True)
    return_picking_number = fields.Char('Tare Return from Driver Document Number', size=64, readonly=True)
    related_picking_ids = fields.One2many('stock.picking', 'related_route_id', 'Related Pickings', readonly=True)
    related_move_ids = fields.One2many('stock.move', 'related_route_id', 'Related Moves', readonly=True)
    temp_route_number = fields.Char('Temporary Route Number', size=64, readonly=True)
    document_scanning_line_ids = fields.One2many('stock.route.document.scanning', 'route_id', 'Documnet Scanning Lines', readonly=True)
    document_count_left_to_check = fields.Integer('Not Ckecked Documents', readonly=True)
    document_count = fields.Integer('All Documents', readonly=True)
    document_count_left_to_check_info_line = fields.Char('Not Ckecked Documents', compute='_calc_document_count_scan', readonly=True, store=False)
    fully_checked = fields.Boolean('Fully Checked', readonly=True, default=False)
    last_user_to_reset_scannig_id = fields.Many2one('res.users', 'Last Person to Reset Scanning', readonly=True)
    scanning_reset_datetime = fields.Datetime('Scanning Reset Date, Time', readonly=True)
    scanning_log = fields.Text('Scanning Log', readonly=True, default='')
    estimated_start = fields.Datetime('Estimated Start')
    estimated_finish = fields.Datetime('Estimated Finish')

    _sql_constraints = [
        ('external_route_id', 'unique (external_route_id)', 'External ID of route has to be unique'),
        ('version_id', 'unique (version_id)', 'Version ID of route has to be unique')
    ]
    
#     _rec_name = 'name'
    
    # _order = 'date desc, name desc'
    _order = 'id desc'
    
    @api.multi
    def update_scanning_log(self, new_line):
        # Atnaujinamas dokumentų skenavimo logas prie maršruto.
        # Kai viskas nuskenuota ar skenavimas nuresetintas

        if self and isinstance(new_line, str):
            update_sql = '''
                UPDATE
                    stock_route
                SET
                    scanning_log = (
                        CASE
                            WHEN scanning_log is NULL THEN %s
                            WHEN scanning_log is not NULL THEN scanning_log || %s
                        END
                    )
                WHERE
                    id in %s
            '''
            log_message = '\n' + new_line + '\n***************************************************'
            update_where = (log_message, log_message, tuple(self.ids))
            self.env.cr.execute(update_sql, update_where)
    
    @api.multi
    def get_left_to_check(self):
        document_info = self.get_related_document_data_for_check_up()
        qty = 0
        for document in document_info:
            if document[3] and document[3] == 'collection':
                continue
            elif document[2] and document[2] == 'electronical':
                continue
            else:
                qty += len(document[1].split(','))
        return qty


    @api.multi
    def update_cheched_document_info(self, doc_left=None):
        for route in self:
            route_vals = {
                'document_count_left_to_check': 0,
                'fully_checked': True
            }
            if doc_left is None:
                doc_left = route.get_left_to_check()
                route_vals['document_count'] = doc_left
            if doc_left > 0:
                route_vals.update({
                    'document_count_left_to_check': doc_left,
                    'fully_checked': False
                })
            else:
                route.document_scanning_line_ids.unlink()
            route.write(route_vals)
            if route_vals['fully_checked']:
                route.update_scanning_log(route.get_scanned_document_summary())

    @api.multi
    def get_scanned_document_summary(self):
        # Maršrutai turi skenavimo logą, kuriame prieš nuresetinant
        # skenavimą reikia įrašyti kiek dokumentų buvo nuskenuota.
        # Ši funkcija suformuoja grąžų tekstą su reikiama informacija.
        
        if self.fully_checked:
            return _('All document were scanned.')
        if not self.document_scanning_line_ids:
            return _('None of the documents were scanned.')
        info_sql = '''
            SELECT
                scanned,
                invoice_type,
                count(*),
                string_agg(name, ', ')
            FROM
                stock_route_document_scanning
            WHERE
                route_id = %s
            GROUP BY
                scanned, invoice_type
        '''
        info_where = (self.id,)
        self.env.cr.execute(info_sql, info_where)
        info_results = self.env.cr.fetchall()

        scanned_documents = ''
        scanned_document_count = 0
        need_to_be_scanned = ''
        need_to_be_scanned_count = 0
        dont_need_to_be_scanned_count = 0

        for info_result in info_results:
            if not scanned_documents and info_result[0]:
                scanned_documents = info_result[3]
                scanned_document_count = info_result[2]
            elif not info_result[0] and info_result[1] == 'need_scanning':
                need_to_be_scanned = info_result[3]
                need_to_be_scanned_count = info_result[2]
            elif info_result[1] in ['collection_package', 'digital_doc']:
                dont_need_to_be_scanned_count += info_result[2]

        info_line = _('Scanned documents: %s | Not scanned lines: %s | Documents whitch doesn\'t have to be scanned: %s') % (
            str(scanned_document_count), str(need_to_be_scanned_count), str(dont_need_to_be_scanned_count)
        )
        info_line += '\n' + _('Not scanned documents') + ': ' + need_to_be_scanned
        return info_line

    @api.multi
    def get_receiver_for_report_log(self, report_name):
        # Metodas naudojamas papildyti spausdintų ataskaitų logui
        receiver = ''
        if report_name == 'config_sanitex_delivery.product_packing':
            receiver = self.receiver or ''
        elif report_name == 'config_sanitex_delivery.drivers_packing_transfer_act':
            receiver = self.location_id and self.location_id.name or ''
        return receiver

    @api.multi
    def get_driver_act_status(self):
        status = '—'
        if self.picking_ids:
            status = '⟶'
            if self.state != 'closed' and self.returned_picking_ids:
                status = '⟵'
            if self.state == 'closed':
                status = '√'
        elif self.returned_picking_ids:
            if self.state != 'closed':
                status = '⟵'
            else:
                status = '√'
                
        return status

    @api.multi
    def get_client_act_status(self):
        status = '—'
        if self.packing_for_client_ids:
            status = '⟶'
            packing_states = set(self.packing_for_client_ids.mapped('state'))
            if self.state == 'closed' and packing_states == {'done'}:
                status = '√'
            elif packing_states == {'done'} and self.state != 'closed':
                status = '⟵'

        return status

    @api.multi
    def get_act_status(self):
        driver_act_status = self.get_driver_act_status()
        client_act_status = self.get_client_act_status()
        return driver_act_status + '   ' + client_act_status

    @api.multi
    def update_act_status(self):
        for route in self:
            act_status = route.get_act_status()
            if route.act_status != act_status:
                route.write({'act_status': act_status})

    @api.multi
    def fleetinfo_to_dict_for_rest_api(self, truck=False):
        if truck:
            return {
                # "createdAt": "",
                "carrierId": self.location_id and self.location_id.owner_id and self.location_id.owner_id.external_customer_id or '',
                "deleted": False,
                # "odometerReading": 0,
                "registrationPlate": self.trailer or '',
                # "runHours": 0,
                # "updateInc": 0,
                # "updatedAt": "",
                "fleetId": self.trailer or '',
                "fleetType": "trailer",
                # "trailerType": ""
            }
        return {
            # "createdAt": "",
            "carrierId": self.location_id and self.location_id.owner_id and self.location_id.owner_id.external_customer_id or '',
            "deleted": False,
            # "odometerReading": 0,
            "registrationPlate": self.license_plate or '',
            # "runHours": 0,
            # "updateInc": 0,
            # "updatedAt": "",
            "fleetId": self.license_plate or '',
            "fleetType": "truck",
            # "trailerType": ""
        }

    @api.multi
    def get_direction(self):
        direction = ''
        if self.receiver:
            direction = self.receiver
        if not direction:
            names = self.sudo().sale_ids.filtered(
                lambda task_rec: task_rec.state != 'cancel'
            ).mapped('shipping_warehouse_id').mapped('name')
            if names:
                direction = ', '.join(names)
        return direction

    @api.multi
    def to_dict_for_rest_integration(self):
        status_mapper = {
            'draft': 'draft',
            'released': 'started',
            'closed': 'finished'
        }
        context = self.env.context or {}
        company = self.get_company()
        version = context.get('rest_version', 1)
        route_dict = {
            'firmid': company.company_code or '',
            'prefstock': self.source_location_id.code or '',
            'loadlistnr': str(self.id), # Neaišku kokį numerį paduot
            'routetype': 'CLIENT', #type_mapper[self.type], # Neaišku kokie tipaigali būti ir pagal ką juos parinkti
            'drivecode': '', # vairuotojai neturi jokio kodo(asmens kodas kurio niekas nepildo)
            'carnumber': self.license_plate or '',
            'trailnumr': self.trailer or '',
            'date': self.date or '',
            'updated': str_date_to_timestamp(self.write_date, '%Y-%m-%d %H:%M:%S'),
            'direction': self.get_direction(),
            'shipinvoiceno': self.name or '',
            'version_id': self.version_id,
            'driverinfo': self.location_id.to_dict_for_rest_integration(),
            'invoices': []
        }
        if version == 2:
            route_dict.update({
                'routeId': str(self.id) or '',
                'estimatedDistance': self.route_length or 0,
                # 'estimatedStartTime': self.date or '',#self.departure_time and utc_str_to_local_str(self.departure_time)[:10] or '',
                'name': self.receiver or '',
                'carrierId': self.location_id and self.location_id.owner_id and self.location_id.owner_id.external_customer_id or '',
                # 'estimatedFinishTime': '',
                'deleted': False,
                'userInfo': self.location_id.to_dict_for_rest_integration(),
                'status': status_mapper.get(self.state, ''),
                # 'position': '',#Negauname
                'driverId': self.location_id and str(self.location_id.id*10000) or '',
                'truckFleetId': self.license_plate or '',
                'trailerFleetId': self.trailer or '',
                'truckInfo': self.fleetinfo_to_dict_for_rest_api(),
                'trailerInfo': self.fleetinfo_to_dict_for_rest_api(truck=True),
                'carrierInfo': self.driver_company_id and self.driver_company_id.carrier_to_dict_for_rest_integration() or {},
                'id_version': self.id_version,
            })
        for task in self.sale_ids:
            task_dict_list = task.to_dict_for_rest_integration()
            if task_dict_list:
                route_dict['invoices'] += task_dict_list
        
        line_no = 1
        for inv_dict in route_dict['invoices']:
            inv_dict['linenum'] = line_no
            line_no += 1
        return route_dict

    @api.multi
    def update_version(self):
        seq_env = self.env['ir.sequence']
        seq = seq_env.search([
            ('code','=','route_version'),
        ], limit=1)
        for route in self:
            route_vals = {}
            if seq:
                route_vals['version_id'] = int(seq.next_by_id())
            else:
                self.env.cr.execute('''
                    SELECT
                        MAX(version_id)
                    FROM
                        stock_route
                ''')
                route_vals['version_id'] =  self.env.cr.fetchall()[0][0] + 1
                
            route_vals['id_version'] = get_local_time_timestamp() 
            route.write(route_vals)
        return True


    @api.model
    def get_routes_by_version(self, version_id):
        domain = [('state','in',['released','closed'])]
        company = self.env['res.users'].browse(self.env.uid).company_id
        limit = company.limit_of_route_rest_export or 50
        if version_id:
            if not isinstance(version_id, int):
                try:
                    version_id = int(version_id)
                    domain.append(('version_id','>',version_id))
                except:
                    pass

        return self.with_context(rest_version=company.get_route_export_version()).search(domain, order='version_id', limit=limit)
    
    @api.multi
    def get_return_picking_name(self, owner=None):
        return_picking_number = False
        if self.picking_ids:# and self.picking_id.name:
            picking_numbers = self.picking_ids.mapped('name')
            picking_numbers.sort()
            return_picking_numbers = self.returned_picking_ids.mapped('name')
            for picking_number in picking_numbers:
                if picking_number + 'R' not in return_picking_numbers:
                    return_picking_number = picking_number
                    break
        if not return_picking_number:
            if self.env.user.company_id.do_use_new_numbering_method():
                return_picking_number = self.env['stock.picking'].get_picking_name('route_return_from_driver', self.warehouse_id, owner)
            else:
                return_picking_number = self.env['stock.picking'].get_pick_name(self.warehouse_id.id, picking_type='driver')
        return return_picking_number + 'R'
    
    @api.model
    def get_route_information_by_version(self, version_id):

        interm_env = self.env['stock.route.integration.intermediate']
        receive_vals = _('Received version parameter') + ': '
        result_vals = ''
        processed = True
        trb = ''
        
        if isinstance(version_id, str):
            receive_vals += version_id
        else:
            receive_vals += str(version_id)
        
        intermediate = interm_env.create({
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
            'function': 'RESTRoutesByVersion',
            'received_values': receive_vals,
            'processed': False
        })
        self.env.cr.commit()
        results = {'loadlist': []}
        try:
            routes = self.get_routes_by_version(version_id)
            result_vals += _('Routes to return: ') + str(routes.mapped('id')) + '\n\n'

            for route in routes:
                results['loadlist'].append(route.to_dict_for_rest_integration())
            results['loadlist'] = sorted(results['loadlist'], key=lambda k: k['version_id'])
            result_vals += _('Result: ') + '\n\n' + str(json.dumps(results, indent=2))
        except Exception as e:
            err_note = _('Failed to return routes: %s') % (tools.ustr(e),)
            result_vals += err_note
            processed = False
            trb += traceback.format_exc() + '\n\n'
            self.env.cr.rollback()

        intermediate.write({
            'processed': processed,
            'return_results': result_vals,
            'traceback_string': trb
        })
        self.env.cr.commit()
        return results


    @api.multi
    def update_last_route_info_in_documents(self):
        # Kai dokumentai būna įdėti į maršrutą(kartu su užduotimis) ir
        # tas maršrutas būna išleistas prie kiekvieno dokumento reikia
        # nurodyti maršruto numerį, vairuotojo vardą ir sandėlį į kur važiuoja,
        # kad pagal jį filtruotųsi. Ši funkcija tai padaro. Jei
        # dokumentas prieš tai buvo priskirtas kitam maršrutui
        # numeris bus perrašytas.

        if self:
            number_sql = '''
                UPDATE
                    account_invoice ai
                SET
                    route_number = sr.name,
                    driver_name = sl.name,
                    warehouse_at_id = (
                        CASE
                            WHEN sr.destination_warehouse_id is not null
                                THEN sr.destination_warehouse_id
                            WHEN sr.destination_warehouse_id is null
                                THEN sr.warehouse_id
                        END
                    )
                FROM
                    stock_route sr,
                    stock_route_invoice_rel srir,
                    stock_location sl
                WHERE
                    srir.route_id = sr.id
                    AND ai.id = srir.invoice_id
                    AND sr.id in %s
                    AND sr.state != 'draft'
                    AND sl.id = sr.location_id
            '''
            number_where = (self._ids,)
            self.env.cr.execute(number_sql, number_where)

    @api.multi
    def update_related_documents(self):
        # kai maršrute pasikeičia susijusios užduotys, turi pasikeisti ir susiję dokumentai
        # iškvietus šia funkciją į maršrutą susidės visi dokumentai, kurie yra susisję su 
        # susijusionmis užduotimis. Taip pat iš maršruto bus pašalinti tie dokumentai, 
        # kurių užduotys buvo išimtos iš maršruto.
        
        for route in self:
            invoices = self.env['account.invoice'].browse()
            for sale in route.sale_ids:
                invoices += sale.get_invoices()
            route_invoices = route.invoice_ids
            invoices_to_add = invoices - route_invoices
            invoices_to_remove = route_invoices - invoices
            inv_ids = [(4, inv.id) for inv in invoices_to_add]
            inv_ids += [(3, inv.id) for inv in invoices_to_remove]
            if inv_ids:
                route.write({'invoice_ids': inv_ids})
        self.update_cheched_document_info()
            
            
    @api.multi
    def update_containers(self):
        # kai maršrute pasikeičia susijusios užduotys, turi pasikeisti ir susiję konteineriai
        # iškvietus šia funkciją į maršrutą susidės visi konteineriai, kurie yra susisję su 
        # susijusionmis užduotimis. Taip pat iš maršruto bus pašalinti tie konteineriai, 
        # kurių užduotys buvo išimtos iš maršruto.
        
        for route in self:
            new_containers = route.sale_ids.mapped('container_ids')
            old_containers = route.container_line_ids.mapped('container_id')
            containers_to_be_in_route = new_containers - old_containers
            if containers_to_be_in_route:
                route.write({
                    'container_line_ids': [
                        (0, 0, {'container_id': cont.id, 'state': 'none'}) \
                            for cont in containers_to_be_in_route
                    ]
                })
            containers_to_be_removed_from_route = old_containers - new_containers
            if containers_to_be_removed_from_route:
                route.container_line_ids.filtered(
                    lambda line_record: \
                        line_record.container_id in containers_to_be_removed_from_route
                ).unlink()
                
            
    
    @api.multi
    def update_route_type(self, destination_changed_in_route=False):
        # Maršrute tipas priklauso nuo susijusių pardavimų tikslo sandėlių.
        # Jeigu į maršrutą pridedama arba iš jo išimama pardavimų, arba
        # kuriame nors pardavime pasikeičia sandėlis iškviečiama ši funkcija,
        # kad perskaičiuotų maršruto tipą

        context = self.env.context or {}
        if context.get('skip_type_recalculation_for_route', False):
            return
        for route in self:
            new_type = route.sale_ids.get_type_for_route()
            vals = {}
            if new_type == 'out':
                new_numbers = [no for no in route.sale_ids.mapped('route_number') if isinstance(no, str)]
                new_number = ', '.join(list(set(new_numbers)))
                vals['receiver'] = new_number
            if new_type != route.type:
                vals['type'] = new_type
                if new_type == 'internal':
                    vals['destination_warehouse_id'] = route.sale_ids[0].shipping_warehouse_id.id
                    vals['return_location_id'] = route.sale_ids[0].shipping_warehouse_id.wh_return_stock_loc_id.id
                    vals['receiver'] = route.sale_ids[0].shipping_warehouse_id.name
                elif new_type == 'mixed':
                    vals['destination_warehouse_id'] = route.sale_ids.filtered(lambda task_rec:
                        task_rec.warehouse_id != task_rec.shipping_warehouse_id
                    )[0].shipping_warehouse_id.id
                    vals['return_location_id'] = route.warehouse_id.wh_return_stock_loc_id.id
                    vals['receiver'] = _('Mixed Route')
                else:
                    vals['destination_warehouse_id'] = False
                    vals['return_location_id'] = route.warehouse_id.wh_return_stock_loc_id.id
                route.write(vals)
            else:
                if destination_changed_in_route:
                    vals['return_location_id'] = route.destination_warehouse_id.wh_return_stock_loc_id.id
                    if new_type == 'mixed':
                        vals['receiver'] = _('Mixed Route')
                    elif new_type == 'internal':
                        vals['receiver'] = route.destination_warehouse_id.name
                    route.write(vals)
                elif new_type == 'internal':
                    if route.destination_warehouse_id != route.sale_ids[0].shipping_warehouse_id:
                        vals['destination_warehouse_id'] = route.sale_ids[0].shipping_warehouse_id.id
                        vals['return_location_id'] = route.sale_ids[0].shipping_warehouse_id.wh_return_stock_loc_id.id
                        vals['receiver'] = route.sale_ids[0].shipping_warehouse_id.name or ''
                        route.write(vals)
                elif new_type == 'mixed':
                    if route.destination_warehouse_id != route.sale_ids.filtered(lambda task_rec:
                            task_rec.warehouse_id != task_rec.shipping_warehouse_id
                        )[0].shipping_warehouse_id:
                        vals['destination_warehouse_id'] = route.sale_ids.filtered(lambda task_rec:
                            task_rec.warehouse_id != task_rec.shipping_warehouse_id
                        )[0].shipping_warehouse_id.id
                        vals['receiver'] = _('Mixed Route')
                        vals['return_location_id'] = route.warehouse_id.wh_return_stock_loc_id.id
                        route.write(vals)
                else:
                    vals['return_location_id'] = route.warehouse_id.wh_return_stock_loc_id.id
                    route.write(vals)
    
    @api.multi
    def update_received_warehouse_ids_text(self):
        # sudaromas tekstas kuriame yra visi susijusių pardavimų 
        # išleidimų sandėlių(kurie pilnai priimti arba negauti) id
        # kad būtų galima greičiau atlikti būsenos skaičiavimo funkciją
        context = self.env.context or {}
        if context.get('skip_received_wh_calc', False):
            return
        for route in self:
            fully_received_ids = []
            grouped_sales = route.sale_ids.group_sales_by_warehouses()
            for grouped_sales_key in grouped_sales.keys():
                shipping_warehouse_id = grouped_sales_key[1]
                if not route.sale_ids.filtered(lambda sale_record: \
                    sale_record.shipping_warehouse_id.id == shipping_warehouse_id \
                    and not sale_record.route_state_received \
                    and not sale_record.not_received \
                    and not sale_record.state == 'cancel'
                ):
                    fully_received_ids.append(shipping_warehouse_id)
            
            wh_filter = 'id'.join([str(fully_received_id) for fully_received_id in fully_received_ids])
            route.write({
                'fully_received_warehouses_ids_char': 'id' + wh_filter + 'id'
            })
    
    @api.multi
    def update_shipping_warehouse_id_filter(self):
        # sudaromas tekstas kuriame yra visi susijusių pardavimų išleidimų sandėlių id
        # kad būtų galima greičiau atlikti maršrutų paiešką pagal naudotoją
        context = self.env.context or {}
        ctx = context.copy()
        ctx['search_by_user_sale'] = False
        for route in self:
            route = route.with_context(ctx)
            sales_shipping_warehouses = route.sale_ids.filtered(
                lambda task_record: task_record.warehouse_id != task_record.shipping_warehouse_id
            ).mapped('shipping_warehouse_id')
            if sales_shipping_warehouses:
                ship_wh_ids = list(set(sales_shipping_warehouses.mapped('id')))
                wh_filter = 'id'.join([str(id) for id in ship_wh_ids])
                route.write({
                    'shipping_warehouse_id_filter': 'id' + wh_filter + 'id'
                })
            else:
                route.write({
                    'shipping_warehouse_id_filter': ''
                })

        return True

    @api.multi
    def update_picking_warehouse_id_filter(self):
        # sudaromas tekstas kuriame yra visi susijusių pardavimų išleidimų sandėlių id
        # kad būtų galima greičiau atlikti maršrutų paiešką pagal naudotoją
        context = self.env.context or {}
        ctx = context.copy()
        ctx['search_by_user_sale'] = False
        for route in self:
            route = route.with_context(ctx)
            route.write({
                'picking_warehouse_id_filter': route.sale_ids.get_picking_warehouse_id_filter()
            })

        return True
                
    @api.multi
    def action_receive(self):
        # atidaro wizardą, kuriame yra sugrupuoti pardavimai pagal tikslo sandėlius
        # tame wizarde naudotojas pasirenka kuriuos konteinerius gavo
        self.fix_bad_route()
        osv_env = self.env['stock.route.receive.osv']
        osv_line_env = self.env['stock.route.receive.lines.osv']
        usr_env = self.env['res.users']
        wh_env = self.env['stock.warehouse']
        
        osv_lines = osv_line_env.browse([])

        user = usr_env.browse(self.env.uid)
        context = self._context or {}
        grouped_sales = self.mapped('sale_ids').filtered(
            lambda record: not record.route_state_received
        ).group_sales_by_warehouses()
        if not grouped_sales:
            raise UserError(_('All containers are already received'))
        osv = osv_env.create({'route_id': self.id})
        default_warehouse = user.default_warehouse_id and user.default_warehouse_id.id or False
        if not default_warehouse:
            raise UserError(_('To receive containers you need to select warehouse.'))
        route_containers = self.container_line_ids.filtered(
            lambda line_rec: line_rec.state != 'received'
        ).mapped('container_id')
        not_received_containers = self.container_line_ids.filtered(
            lambda line_rec: line_rec.state == 'not_received'
        ).mapped('container_id')
        for key in grouped_sales.keys():
            check_all = False
            sale_containers = grouped_sales[key].mapped('container_ids')
            if not sale_containers:
                continue
            containers = route_containers & sale_containers
            if default_warehouse == key[1]:
                if not (route_containers & not_received_containers):
                    check_all = True
                (containers - not_received_containers).write({
                    'route_received': True, 'route_not_received': False
                })
                (route_containers & not_received_containers).write({
                    'route_received': False, 'route_not_received': True
                })
                
            else:
                containers.write({'route_received': False, 'route_not_received': False})
            line_to_add_to = osv_lines.filtered(lambda  line_record: line_record.shipping_warehouse_id.id == key[1])
            if line_to_add_to:
                line_to_add_to.write({
                    'picking_warehouses': line_to_add_to.picking_warehouses + ' / ' + wh_env.browse(key[0]).code,
                    'container_ids': [(4, container.id) for container in containers],
                    'sales': (check_all and str(len(containers) + len(line_to_add_to.container_ids)) or '0') + '/' + str(len(containers) + len(line_to_add_to.container_ids))
                })
            else:
                osv_lines += osv_line_env.create({
                    'picking_warehouses': wh_env.browse(key[0]).code,
                    'check_all': check_all,
                    'osv_id': osv.id,
                    'picking_warehouse_id': key[0],
                    'shipping_warehouse_id': key[1],
                    'container_ids': [(6, 0, containers.mapped('id'))],
                    'sales': (check_all and str(len(containers)) or '0') + '/' + str(len(containers))
                })
        ctx = context.copy()
        ctx['active_ids'] = self.mapped('id')
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.route.receive.osv',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': ctx,
            'res_id': osv.id,
            'nodestroy': True,
        }
    

    @api.multi
    def get_lines_for_packing_return_act(self):
        context = self.env.context or {}
        if context.get('picking_id_for_tare_act', False):
            picking = self.returned_picking_ids.filtered(lambda pick_rec: pick_rec.id == context['picking_id_for_tare_act'])
        else:
            picking = self.returned_picking_ids[0]

        return picking.get_lines_for_packing_return_act()
        # lines = []
        # total = {
        #     'big_box': 0,
        #     'small_box': 0,
        #     'unit': 0,
        #     'total': 0,
        #     'brutto_weight': 0.0,
        #     'price': 0.0
        # }
        # if self.returned_picking_id:
        #     for move in self.returned_picking_id.move_lines:
        #         line = {}
        #         line['code'] = move.product_id and move.product_id.default_code or ''
        #         line['name'] = move.product_id and move.product_id.name or ''
        #         line['wo_vat'] = move.product_id and move.product_id.standard_price or 0.0
        #         line['w_vat'] = line['wo_vat'] + line['wo_vat'] * 0.21
        #         line['big_box'] = 0
        #         line['small_box'] = 0
        #         line['quantity'] = int(move.product_uom_qty)
        #         line['total_quantity'] = int(move.product_uom_qty)
        #         line['total_wo_vat'] = line['total_quantity'] * line['wo_vat']
        #         line['brutto'] = move.product_id and move.product_id.weight or 0.0
        #         lines.append(line)
        # 
        #         total['big_box'] += line['big_box']
        #         total['small_box'] += line['small_box']
        #         total['unit'] += line['quantity']
        #         total['total'] += line['total_quantity']
        #         total['brutto_weight'] += line['brutto']
        #         total['price'] += line['total_wo_vat']
        # else:
        #     line = {}
        #     line['code'] = ''
        #     line['name'] = ''
        #     line['wo_vat'] = 0.0
        #     line['w_vat'] = 0.0
        #     line['big_box'] = 0.0
        #     line['small_box'] = 0.0
        #     line['quantity'] = 0.0
        #     line['total_quantity'] = 0.0
        #     line['total_wo_vat'] = 0.0
        #     line['brutto'] = 0.0
        #     lines.append(line)
        # return lines, total

    @api.multi
    def update_weight(self):
        ctx = (self.env.context or {}).copy()
        ctx['search_by_user_sale'] = False
        ctx['search_by_user_not_received_sale'] = False
        for route in self.with_context(ctx):
            weight = route.get_total_weight()
            route.write({'weight': weight})
    
    @api.model
    def get_total_weight(self):
        weight = 0.0
        for route in self:
#             sale_weight = route.sale_ids.get_total_weight()
            sale_weight = sum(route.sale_ids.filtered(lambda sale_record:
                sale_record.state != 'cancel' and sale_record.delivery_type != 'collection'
            ).mapped('total_weight'))
#             package_weight = route.collection_package_ids.get_total_weight()
#             container_weight = route.container_line_ids.mapped('container_id').get_total_weight()
            tare_weight = route.picking_ids.get_total_weight()
            weight = sale_weight + tare_weight# + package_weight + container_weight
        return weight

    @api.multi
    def unlink(self):
        context = self.env.context or {}
        if not context.get('allow_to_delete_not_draft_routes', False):
            for route in self:
                if route.state != 'draft':
                    raise UserError(_('You can\'t unlink released or closed routes(%s).') % str(route.id))
        self.mapped('sale_ids').remove_from_route()
        return super(StockRoute, self).unlink()
    
    @api.multi
    def update_counts(self):
        # atnaujina pardavimų kiekį maršrutuose
        
        ctx = (self.env.context or {}).copy()
        ctx['search_by_user_sale'] = False
        ctx['search_by_user_not_received_sale'] = False
        
        for route in self.with_context(ctx):
            route.write({'sale_count': len(route.sale_ids)})
        return True
    
    @api.model_cr
    def init(self):
        cr = self.env.cr
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_route_external_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX stock_route_external_id_index ON stock_route (external_route_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_route_intermediate_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX stock_route_intermediate_id_index ON stock_route (intermediate_id)')
    
    @api.model
    def remove_package_from_route_if_exist(self, package_id, external_route_id):
        self.env.cr.execute("""
            SELECT 
                sr.id,
                rel.package_id
            FROM
                delivery_package_route_rel rel 
                join stock_route sr on (sr.id = rel.delivery_route_id)
            WHERE
                sr.external_route_id != '%s'
                and rel.package_id = %s
                and sr.state = 'draft'
                and sr.type = 'out'
        """ % (external_route_id, str(package_id)))
        res = self.env.cr.fetchall()
        for r in res:
            route = self.browse(r[0])
            route.write({
                'delivery_package_ids': [(3, r[1])]
            })
            self.env.cr.execute("""
                SELECT 
                    sr.id,
                    rel.package_id
                FROM
                    delivery_package_route_rel rel 
                    join stock_route sr on (sr.id = rel.delivery_route_id)
                WHERE
                    sr.internal_route_for_route_id = %s
                    and rel.package_id = %s
                    and sr.state = 'draft'
                    and sr.type = 'internal'
            """ % (str(r[0]), str(package_id)))
            res2 = self.env.cr.fetchall()
            for r2 in res2:
                route2 = self.browse(r2[0])
                route2.write({
                    'delivery_package_ids': [(3, r2[1])]
                })
        return True
    
    @api.multi
    def get_company(self):
        if self.company_id:
            return self.company_id
        else:
            return self.env['res.users'].browse(self.env.uid).company_id
    
    @api.model
    def _convert_dict_to_xml(self, dictionary, doc, root_tag=None):
        
        def create_node_with_val(node_name, val):
            if not isinstance(val, str):
                try:
                    val = str(val)
                except:
                    pass
            node = doc.createElement(node_name)
            value = doc.createTextNode(val)
            node.appendChild(value) 
            return node
        
        if root_tag is not None:
            tag = doc.createElement(root_tag)
        for key in dictionary.keys():
            if key == '_value':
                value = doc.createTextNode(dictionary[key])
                tag.appendChild(value)
            elif key != '_attributes' and key != '_value':
                if isinstance(dictionary[key], dict):
                    new_tag = self._convert_dict_to_xml(dictionary[key], doc, key)
                    tag.appendChild(new_tag)
                elif isinstance(dictionary[key], list):
                    for item in dictionary[key]:
                        new_tag = self._convert_dict_to_xml(item, doc, key)
                        tag.appendChild(new_tag)
                else:
                    new_tag = create_node_with_val(key, dictionary[key])
                    tag.appendChild(new_tag)
            elif key == '_attributes':
                for attr in dictionary[key]:
                    tag.setAttribute(attr[0], attr[1])        
        return tag
    
    @api.model
    def convert_dict_to_xml(self, dictionary, root_tag):
        xml_doc = Document()
        main_tag = self._convert_dict_to_xml(dictionary, xml_doc, root_tag)
        xml_doc.appendChild(main_tag)
        return xml_doc.toxml(encoding='utf-8')

    @api.multi
    def _export_rows(self, fields):
        if self.env.user.company_id.user_faster_export:
            res = self.env['ir.model'].export_rows_with_psql(fields, self)
        else:
            res = super(StockRoute, self)._export_rows(fields)
        return res

    @api.multi
    def get_product_packing_xml(self, warehouse_id=False, language='LT'):
        data = {}
        warehouse_name = self.receiver
        if warehouse_id:
            warehouse_name = self.env['stock.warehouse'].browse(warehouse_id).name
        # seller = self.env['product.owner'].search([('owner_code','=','BSO')], limit=1).get_owner_dict()
        seller = self.env.user.company_id.get_sender_for_loadlist_report().get_owner_dict()
        load_list = {
            'LoadListNr': str(self.id),
            'DocumentNum': self.name or '',
            'Date': self.date,
            'Direction': self.drections_for_drive_report or (self.warehouse_id.id != warehouse_id and warehouse_name) \
                or self.receiver or self.location_id.name or '',
            'LoadAddress': self.source_location_id and self.source_location_id.load_address or '',
            'SellerName': seller.get('Name', '') or self.sender1_id and self.sender1_id.name or '',
            'SellerRegCode': seller.get('RegCode', '') or self.sender1_id and self.sender1_id.ref or '',
            'SellerVatCode': seller.get('VATCode', '') or self.sender1_id and self.sender1_id.vat or '',
            'SellerAddress': seller.get('RegAddress', '') or self.sender1_id and self.sender1_id.street or '',
            'SellerPhone': seller.get('Phone', '') or self.sender1_id and self.sender1_id.phone or '',
            'SellerFax': seller.get('Fax', '') or self.sender1_id and self.sender1_id.fax or '',
            'Currency': 'EUR',
            'SellerName2': self.sender2_id and self.sender2_id.name or '',
            'SellerRegCode2': self.sender2_id and self.sender2_id.ref or '',
            'SellerVatCode2': self.sender2_id and self.sender2_id.vat or '',
            'SellerAddress2': self.sender2_id and self.sender2_id.street or '',
            'SellerPhone2': self.sender2_id and self.sender2_id.phone or '',
            'SellerFax2': self.sender2_id and self.sender2_id.fax or '',
            'RouteNr': self.name or '',
            'RouteDescript': self.description or '',

            # 'RecipName': 'UAB "Officeday"',
            # 'RecipRegCode': '124931353',
            # 'RecipVatCode': '249313515',
            # 'RecipAddress': 'Vilkpedes g. 4, Vilnius'
        }
        driver = {
            'Id': self.location_id and str(self.location_id.id) or 0,
            'CarrierName': self.location_id and self.location_id.owner_id \
                and self.location_id.owner_id.name or '',
            'CarrierRegCode': self.location_id and self.location_id.owner_id \
                and self.location_id.owner_id.ref or '',
            'CarrierAddress': self.location_id and self.location_id.owner_id \
                and self.location_id.owner_id.street or '', 
            'DriverName': self.location_id and self.location_id.name or '', 
            'DriverCode': self.location_id and self.location_id.driver_code or '',
            'AgreementText': self.location_id and self.location_id.contract_no,
                # and self.location_id.owner_id.driving_contract_number or '',
            'CarNumber': self.license_plate or '',
            'TrailerNumber': self.trailer or ''
        }
        load_docs = []
        load_docs2 = []
        done_invoices = []
        done_packages = []
        # taros perdavimo akto pridėjimas
        if self.picking_ids:
            for picking in self.picking_ids:
                load_doc = {
                    'Date': self.date or '',
                    'DocumentNum': picking.name or '',
                    'DocumentType': False and 'G' or 'V',
                    'ClientName': _('Drivers'),
                    'PosId':  '',
                    'PosAddress': '',
                    'Route': '',
                    'InvSum': 0.0,
                    'Weight': picking.get_total_weight(),
                    'BoxCount': '',
                    'IsTobacco': '0',
                    'IsAlco': '0',
                    'CashSum': 0,
                    'OwnerCode': picking.owner_id and picking.owner_id.owner_code or '',
                    'PckOrderNo': ''
                }
                load_docs2.append(load_doc)
                load_docs2 = sorted(load_docs2, key=lambda k: k['DocumentNum'])

        # ruošinių pridėjimas, kurio nebereikia :)
        # for packing in self.packing_for_client_ids.filtered('printed').sorted(key = lambda pack_rec: pack_rec.number):
        #     load_doc = {
        #         'Date': self.date or '',
        #         'DocumentNum': packing.number or '',
        #         'DocumentType': False and 'G' or 'V',
        #         'ClientName': _('Drivers'),
        #         'PosId':  '',
        #         'PosAddress': '',
        #         'Route': '',
        #         'InvSum': 0.0,
        #         'Weight': 0.0,
        #         'BoxCount': '',
        #         'IsTobacco': '0',
        #         'IsAlco': '0',
        #         'CashSum': 0,
        #         'OwnerCode': '',
        #         'PckOrderNo': ''
        #     }
        #     load_docs2.append(load_doc)


        for sale in self.sale_ids.filtered(lambda sale_record: warehouse_id \
            and sale_record.shipping_warehouse_id \
            and sale_record.shipping_warehouse_id.id == warehouse_id
        # ).sorted(key = lambda sale_record: isinstance(sale_record.order_number_by_route, str) and sale_record.order_number_by_route or '9999'):
        ).sorted(key = lambda sale_record: isinstance(sale_record.invoice_number, str) and sale_record.invoice_number or '9999'):
            task_invoices = sale.order_package_type != 'package' and sale.get_invoices() or self.env['account.invoice']
            for invoice in task_invoices:
                if invoice in done_invoices:
                    continue
                done_invoices.append(invoice)
                load_doc={
                    'Date': invoice.date_invoice or '',
                    'DocumentNumSort': invoice.name or '',
                    'DocumentNum': ((sale.after_replan or sale.replanned) and _('(R)') or '') + invoice.name or '',
                    'DocumentType': sale.delivery_type == 'collection' and 'G' or 'V', 
                    'ClientName': invoice.partner_id and invoice.partner_id.name or '',
                    'PosId': invoice.partner_shipping_id and invoice.partner_shipping_id.possid_code or '',
                    'PosAddress': invoice.partner_shipping_id and invoice.partner_shipping_id.street or '',
                    'Route': '', 
                    'InvSum': invoice.amount_total,
                    'Weight': sale.delivery_type == 'delivery' and invoice.get_total_weight() or 0.0,
                    'BoxCount': '',
                    'IsTobacco': str(int(sale.tobacco)),
                    'IsAlco': str(int(sale.alcohol)),
                    'CashSum': invoice.cash_amount,
                    'OwnerCode': sale.owner_id and sale.owner_id.owner_code or '',
                    'PckOrderNo': sale.name or ''
                }
                load_docs.append(load_doc)
                if invoice.nkro_number and invoice.nsad_number and invoice.nkro_number != invoice.nsad_number:
                    load_doc={
                        'Date': invoice.date_invoice or '',
                        'DocumentNumSort': invoice.name == invoice.nkro_number and invoice.nsad_number or invoice.nkro_number or '',
                        'DocumentNum': ((sale.after_replan or sale.replanned) and _('(R)') or '') + (invoice.name == invoice.nkro_number and invoice.nsad_number or invoice.nkro_number or ''),
                        'DocumentType': sale.delivery_type == 'collection' and 'G' or 'V',
                        'ClientName': invoice.partner_id and invoice.partner_id.name or '',
                        'PosId': invoice.partner_shipping_id and invoice.partner_shipping_id.possid_code or '',
                        'PosAddress': invoice.partner_shipping_id and invoice.partner_shipping_id.street or '',
                        'Route': '',
                        'InvSum': 0.0,#invoice.amount_total,
                        'Weight': 0.0,#sale.delivery_type == 'delivery' and invoice.get_total_weight() or 0.0,
                        'BoxCount': '',
                        'IsTobacco': str(int(sale.tobacco)),
                        'IsAlco': str(int(sale.alcohol)),
                        'CashSum': 0.0, #invoice.cash_amount,
                        'OwnerCode': sale.owner_id and sale.owner_id.owner_code or '',
                        'PckOrderNo': sale.name or ''
                    }
                    load_docs.append(load_doc)

            if not task_invoices and sale.related_package_id:
                if sale.related_package_id in done_packages:
                    continue
                done_packages.append(sale.related_package_id)
                package = sale.related_package_id
                load_doc={
                    'Date': package.delivery_date and utc_str_to_local_str(package.delivery_date)[:10] or '',
                    'DocumentNumSort': package.document_ids and ', '.join(package.document_ids.mapped('external_document_id')) \
                        or package.internal_order_number or '',
                    'DocumentNum': ((sale.after_replan or sale.replanned) and _('(R)') or '') + (package.document_ids and ', '.join(package.document_ids.mapped('external_document_id')) \
                        or package.internal_order_number or ''),
                    'DocumentType': sale.delivery_type == 'collection' and 'G' or 'V',
                    'ClientName': sale.partner_id and sale.partner_id.name or '',
                    'PosId': sale.posid and '',
                    'PosAddress': sale.partner_shipping_id and sale.partner_shipping_id.street or '',
                    'Route': '',
                    'InvSum': 0.0,
                    'Weight': sale.delivery_type == 'delivery' and sale.total_weight or 0.0,
                    'BoxCount': '',
                    'IsTobacco': str(int(0)),
                    'IsAlco': str(int(0)),
                    'CashSum': 0.0,
                    'OwnerCode': sale.owner_id and sale.owner_id.owner_code or '',
                    'PckOrderNo': sale.name or ''
                }
                load_docs.append(load_doc)

            if not task_invoices and not sale.related_package_id and sale.order_package_type == 'package' \
                and sale.delivery_type == 'collection' \
            :
                load_doc={
                    'Date': sale.shipping_date or '',
                    'DocumentNumSort': sale.name or '',
                    'DocumentNum': ((sale.after_replan or sale.replanned) and _('(R)') or '') + (sale.name or ''),
                    'DocumentType': sale.delivery_type == 'collection' and 'G' or 'V',
                    'ClientName': sale.partner_id and sale.partner_id.name or '',
                    'PosId': sale.posid and '',
                    'PosAddress': sale.partner_shipping_id and sale.partner_shipping_id.street or '',
                    'Route': '',
                    'InvSum': 0.0,
                    'Weight': 0.0,
                    'BoxCount': '',
                    'IsTobacco': str(int(0)),
                    'IsAlco': str(int(0)),
                    'CashSum': 0.0,
                    'OwnerCode': sale.owner_id and sale.owner_id.owner_code or '',
                    'PckOrderNo': sale.name or ''
                }
                load_docs.append(load_doc)


        load_docs = sorted(load_docs, key=lambda k: k['DocumentNumSort'])
        load_docs = load_docs2 + load_docs

        # for collection_package in self.collection_package_ids:
        #     load_doc = collection_package.to_dict_for_report()
        #     load_doc['DocumentType'] = 'G'
        #     load_doc['ClientName'] = collection_package.sender_id and collection_package.sender_id.name or ''
        #     load_doc['PosId'] = collection_package.sender_address_id and collection_package.sender_address_id.possid_code or ''
        #     load_doc['PosAddress'] = collection_package.sender_address_id and collection_package.sender_address_id.street or ''
        #     load_docs.append(load_doc)
        # 
        # for delivery_package in self.delivery_package_ids:
        #     load_doc = delivery_package.to_dict_for_report()
        #     load_doc['DocumentType'] = 'V'
        #     load_doc['ClientName'] = collection_package.buyer_id and collection_package.buyer_id.name or ''
        #     load_doc['PosId'] = collection_package.buyer_address_id and collection_package.buyer_address_id.possid_code or ''
        #     load_doc['PosAddress'] = collection_package.buyer_address_id and collection_package.buyer_address_id.street or ''
        #     load_docs.append(load_doc)
            
            
        data['LoadList'] = load_list
        data['Driver'] = driver
        data['LoadDoc'] = load_docs
        report = {
            'Data': data,
            '_attributes': [
                ('Type','REPWIN'),
                ('UniqueId','SAVULD371726'),
                ('Language',language),
                ('Form','LOADLIST')
            ]
        }
        return self.convert_dict_to_xml(report, 'PrintDoc')
    
    @api.multi
    def get_carrier_dict(self):
        return {
            'Name': self.location_id and self.location_id.owner_id \
                and self.location_id.owner_id.name or '',
            'RegCode': self.location_id and self.location_id.owner_id \
                and self.location_id.owner_id.ref or '',
            'VATCode': self.location_id and self.location_id.owner_id \
                and self.location_id.owner_id.vat or '',
            'RegAddress': self.location_id and self.location_id.owner_id \
                and self.location_id.owner_id.street or '', 
            'Driver': self.location_id and self.location_id.name or '',
            'CarNumber': self.license_plate or '',
            'TrailNumber': self.trailer or '',
            'AgreementText': self.location_id and self.location_id.owner_id \
                and self.location_id.owner_id.driving_contract_number or '',
        }
    
    @api.multi
    def get_invoice_dict(self, tare_return=False):
        context = self.env.context or {}
        if tare_return:
            if context.get('picking_id_for_tare_act', False):
                picking = self.returned_picking_ids.filtered(lambda pick_rec: pick_rec.id == context['picking_id_for_tare_act'])
            else:
                picking = self.returned_picking_ids and self.returned_picking_ids[0] or self.returned_picking_ids
        else:
            if context.get('picking_id_for_tare_act', False):
                picking = self.picking_ids.filtered(lambda pick_rec: pick_rec.id == context['picking_id_for_tare_act'])
            else:
                picking = self.picking_ids and self.picking_ids[0] or self.picking_ids
        return {
            'Warehouse': self.source_location_id and self.source_location_id.code or '',
            'InvoiceNo': picking and picking.name or (self.move_ids and self.move_ids[0].picking_id.name) or 'T',
            'NKro': '',
            'ChangedInvNo': '',
            'UniqueId': str(self.id),
            'DocType': '',
            'SubType': '',
            'DocumentDate': self.date or '',
            'ShipDate': time.strftime('%Y-%m-%d'),
            'SumTotal': str(self.get_product_sum()),
            'SumDeposit': str(0),
            'SumTara': str(self.get_product_sum('package')),
            'Currency': 'EUR',
            'InvoiceCreateTime': utc_str_to_local_str(self.departure_time),
            'PaymentDays': str(0),
            'OrderNo': '',
            'TextOnInv': self.description or '',
        }

    @api.multi
    def get_seller_dict(self, tare_return=False):
        context = self.env.context or {}
        if tare_return:
            if context.get('picking_id_for_tare_act', False):
                moves = self.return_move_ids.filtered(lambda move_rec: move_rec.picking_id.id == context['picking_id_for_tare_act'])
                if moves:
                    owner = moves[0].product_id.owner_id
                else:
                    owner = False
            else:
                owner = self.return_move_ids and self.return_move_ids[0].product_id.owner_id or False

        else:
            if context.get('picking_id_for_tare_act', False):
                moves = self.move_ids.filtered(lambda move_rec: move_rec.picking_id.id == context['picking_id_for_tare_act'])
                if moves:
                    owner = moves[0].product_id.owner_id
                else:
                    owner = False
            else:
                owner = self.move_ids and self.move_ids[0].product_id.owner_id or False
        owner_dict = owner and owner.get_owner_dict() or {}
        owner_dict['LoadAddress'] = self.source_location_id.load_address or ''
        return owner_dict
        
        # company = self.get_company()
        # address_part = []
        # address = ''
        # if company.street:
        #     address_part.append(company.street)
        # if company.city:
        #     address_part.append(company.city)
        # if company.state_id and company.state_id.name:
        #     address_part.append(company.state_id.name)
        # address = ', '.join(address_part)
        # return {
        #     'Name': company.name or '',
        #     'RegCode': company.company_registry or '',
        #     'VATCode': company.vat or '',
        #     'LoadAddress': '',
        #     'RegAddress': address or '',
        #     'Phone': company.phone or '',
        #     'LogisticsPhone': company.phone or '',
        #     'LogisticsEMail': company.email or '',
        #     'Fax': company.fax or '',
        # }
    
    @api.multi
    def get_client_dict(self):
        return {
            'Name': '',
            'RegCode': '',
            'VatCode': '',
            'RegAddress': '',
            'InidividualActvNr': '',
            'FarmerCode': '',
            'POSAddress': '',
            'PosName': '',
            'InnerCode': '',
            'BSNLicNr': '',
            'Phone': '',
            'Fax': '',
            'POSAddress2': '',
            'EUText': '',
            'PosCode': '',
            'PersonName': '',
            'Route': self.receiver or '',
            'Region': self.warehouse_id and self.warehouse_id.region_id and self.warehouse_id.region_id.name or ''
        }
    
    @api.multi
    def get_logist_dict(self):
        return {
            'LogisticsText': '',
            'Creator': self.env['res.users'].browse(self.env.uid).name or '',
            'ProductsIssuedBy': '',
        }
    
    @api.multi
    def get_seller_bank_acc_dict(self):
        return {
            'BankName': '',
            'BankAccount': ''
        }
    
    @api.multi
    def get_vat_line_dict(self):
        return {
            'VatTrf': str(0),
            'SumWoVat': str(0),
            'VatSum': str(0),
        }

    @api.model
    def get_tare_credit_lines_for_tare_report(self, driver, owner):
        lines = []
        for debt_line in driver.get_drivers_debt_all(owner):
            tare_credit = {
                'Inf_Prek': debt_line.product_code,
                'ProductDescription': debt_line.product_name,
                'Price': round(debt_line.product_id.standard_price, 2),
                'TareCredit': int(debt_line.qty_available),
            }
            lines.append(tare_credit)
        return lines

    @api.multi
    def get_drivers_packing_transfer_act_xml(self, language='LT', tare_return=False):
        data = {}
        context = self.env.context or {}
        invoice = self.get_invoice_dict(tare_return)
        invoice['DocType'] = 'TareActDriver'#'ShipInvoice'
        invoice['SubType'] = 'TARETODRIVER'#'TareAct'
        
        seller = self.get_seller_dict(tare_return)
        
        seller_bank_account = self.get_seller_bank_acc_dict()
        carrier = self.get_carrier_dict()
        client = self.get_client_dict()
        client['Name'] = self.location_id and self.location_id.name or ''
        
        logist = self.get_logist_dict()
        vat_line = self.get_vat_line_dict()
        
        lines = []
        tare_credit_lines = []
        i = 0
        coeff = 1
        if tare_return:
            coeff=-1
            if context.get('picking_id_for_tare_act', False):
                picking = self.returned_picking_ids.filtered(lambda picking_rec: picking_rec.id == context['picking_id_for_tare_act'])
            else:
                picking = self.returned_picking_ids[0]
        else:
            if context.get('picking_id_for_tare_act', False):
                picking = self.picking_ids.filtered(lambda picking_rec: picking_rec.id == context['picking_id_for_tare_act'])
            else:
                picking = self.picking_ids[0]
        if picking:
            for move in picking.move_lines.sorted(key = lambda move_record: move_record.product_code):
                i += 1
                line = {
                    'Line_No': str(i),
                    'ProductCode': move.product_id and move.product_id.default_code or '',
                    'Inf_Prek': move.product_id and move.product_id.default_code or '',
                    'ProductId': move.product_id and str(move.product_id.id) or '',
                    'Barcode': '',
                    'CodeAtClient': '',
                    'ProductDescription': move.product_id and move.product_id.name or '',
                    'MeasUnit': move.product_id and move.product_id.uom_id and move.product_id.uom_id.name or '',
                    'Price': move.product_id and str(move.product_id.standard_price*coeff or 0),
                    'PriceVat': move.product_id and str(move.product_id.standard_price*coeff or 0),
                    'Discount': str(0),
                    'Kd': str(0),
                    'Km': str(0),
                    'Kv': str(0),
                    'Quantity': str(int(move.product_uom_qty or 0)*coeff),
                    'QuantityInUnits': str(int(move.product_uom_qty or 0)*coeff),
                    'SumWoVAT': str((move.product_uom_qty*coeff or 0) * (move.product_id.standard_price or 0)),
                    'LineDiscAmt': str(0),
                    'VatTrf': str(0),
                    'Netto': move.product_id and str((move.product_id.weight or 0)*(move.product_uom_qty*coeff or 0)),
                    'Brutto': move.product_id and str((move.product_id.weight or 0)*(move.product_uom_qty*coeff or 0)),
                    'Tobacco': str(0),
                    'Alco': str(0),
                    'ProductKiekd': str(int(move.product_uom_qty or 0)),
                    'Tara': 'U',
                }
                lines.append(line)
                # tare_credit = {
                #   'Inf_Prek': line['Inf_Prek'],
                #   'ProductDescription': line['ProductDescription'],
                #   'Price': line['Price'],
                #   'TareCredit': move.product_id and str(int(self.location_id.get_drivers_debt(move.product_id.id))) or '0',
                # }
                # tare_credit_lines.append(tare_credit)
            owner = picking.move_lines and picking.move_lines[0].product_id.owner_id or False
            tare_credit_lines = self.get_tare_credit_lines_for_tare_report(self.location_id, owner)
        lines = sorted(lines, key=lambda k: k['ProductCode'])
        tare_credit_lines = sorted(tare_credit_lines, key=lambda k: k['Inf_Prek'])
        data['Invoice'] = invoice
        data['Seller'] = seller
        data['SellerBankAccount'] = seller_bank_account
        data['Client'] = client
        data['Logist'] = logist
        data['Carrier'] = carrier
        data['VatLine'] = vat_line
        data['Line'] = lines
        data['TareCredit'] = tare_credit_lines
        report = {
            'Data': data,
            '_attributes': [
                ('Type','REPWIN'),
                ('Language',language),
                ('Form','SHIPINVOICE')
            ]
        }
        return self.convert_dict_to_xml(report, 'PrintDoc')
    
    @api.multi
    def get_xml_for_report(self, report, warehouse_id=False, language='LT'):
        context = self.env.context or {}
        if report == 'config_sanitex_delivery.product_packing':
            #draivas
            self.fill_in_number()
            return self.env['stock.route'].browse(self.id).get_product_packing_xml(warehouse_id=warehouse_id, language=language)
        elif report == 'config_sanitex_delivery.drivers_packing_transfer_act':
            #Taros perdavimo vairuotojui katas
            if self.move_ids:
                # nespausdinti ir nepildyti numerio jeigu neperduota tara vairuotojui
                return self.get_drivers_packing_transfer_act_xml(language=language)
            else:
                if context.get('show_printing_error', False):
                    raise UserError(_('Route does not have any tare assigned.'))
                return False
        elif report == 'config_sanitex_delivery.packing_return_act':
            return self.get_drivers_packing_transfer_act_xml(language=language, tare_return=True)
            # return self.get_drivers_packing_transfer_act_xml()
    
    @api.multi
    def get_pdf_report(self, report, warehouse_id=False, language='LT'):
        # Iškviečia xml formavio funkciją. Gautą xml'ą paduodą į fukciją, kuri
        # iš jo suformuoja pdf'ą ir išsaugo kompiuteryje ir grąžiną kelią iki pdf'o.
        
        ctx = (self.env.context or {}).copy()
        ctx['search_by_user_sale'] = False
        ctx['search_by_user_not_received_sale'] = False
        xml = self.with_context(ctx).get_xml_for_report(report, warehouse_id=warehouse_id, language=language)
        if not xml:
            return False

        report_name = report
        if report == 'config_sanitex_delivery.product_packing':
            report_name = 'krovinio_gabenimo_vaztarstis_draivas'
        return self.env['printer'].get_report(xml, report_name)
    
    @api.multi
    def get_product_sum(self, prod_type=False):
        total_sum = 0.0
        if self.picking_id:
            total_sum = self.picking_id.get_product_sum(prod_type)
            # for move in self.picking_id.move_lines:
            #     if move.product_id:
            #         if prod_type and move.product_id.type_of_product != prod_type:
            #             continue
            #             total_sum += move.product_id.standard_price*move.product_uom_qty
        return total_sum

    @api.multi
    def copy(self, default=None):
        raise UserError(_('You cannot duplicate a route.'))

    @api.multi
    def update_tare_number(self):
        for route in self:
            if route.picking_ids:
                names = route.picking_ids.mapped('name')
                act_name = ', '.join([name for name in names if name])
                if route.picking_number != act_name:
                    route.write({'picking_number': act_name})

    @api.multi
    def update_return_tare_number(self):
        for route in self:
            if route.returned_picking_ids:
                names = route.returned_picking_ids.mapped('name')
                act_name = ', '.join([name for name in names if name])
                if route.return_picking_number != act_name:
                    route.write({'return_picking_number': act_name})

    @api.onchange('type')
    def on_change_route_type(self):
        if self.type and self.type == 'out':
            self.destination_warehouse_id = False
    
    @api.onchange('warehouse_id')
    def on_change_source_warehouse(self):
        if self.warehouse_id:
            if self.warehouse_id.wh_return_stock_loc_id:
                self.return_location_id = self.warehouse_id.wh_return_stock_loc_id.id
            else:
                self.return_location_id = False
        else:
            self.return_location_id = False

    @api.multi
    def get_route_info(self):
        res = self.warehouse_id.name + ' ---> ' + \
            (self.type == 'internal' and self.destination_warehouse_id.name or 'Clients') + \
            ' [' + ROUTE_STATES[self.state] +']'
        return res

    @api.multi
    def name_get(self):
        if not self:
            return []
        res = []
        for route in self.read([
            'date', 'route_name', 'name', 'receiver'
        ]):
            name = ''
            if route.get('name', False):
                name = route['name']
            elif route.get('route_name', False):
                name = route['route_name']
            elif route.get('receiver', False):
                name = route['receiver']
            if name:
                name += ' '
            name += '[' + route['date'] + ']'
            res.append((route['id'], name))
                
        return res

    @api.multi
    def transfer_orders(self):
        context = self.env.context or {}
        ctx = context.copy()
        
        ctx['order_ids'] = self.sale_ids.mapped('id')
        
        return  {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.route.transfer_orders.osv',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': ctx,
            'nodestroy': True,
        }

    @api.multi
    def remove_not_printed_packings(self):
        context = self.env.context or {}
        ctx_del = context.copy()
        ctx_del['allow_unlink_packing'] = True
        pack_obj = self.env['stock.packing']
        for route in self:
            packs = pack_obj.search([
                ('route_id','=',route.id),
                ('printed','=',False)
            ])
            # Paduodamas admin ID nes bls nori kad ranka niekas negalėtų nieko trinti, todėl paprastos teisės trinimą draudžia.
            packs.sudo().with_context(ctx_del).unlink()
        return True

    @api.multi
    def dummy_print(self):
        return True
    
    @api.model
    def get_sender(self):
        company = self.env['res.users'].browse(self.env.uid).company_id
        return company.bls_owner_partner_id and company.bls_owner_partner_id.id or False
    
#     def fill_in_owner(self, cr, uid, ids, context=None):
#         #nebenaudojama nes pasikeitė taip kad dabar visada vienas ir tas pats siuntėjas bus
#         usr_obj = self.env('res.users')
#         company = usr_obj.browse(cr, uid, uid, context=context).company_id
#         bls_id = company.bls_owner_partner_id and company.bls_owner_partner_id.id or False
#         sanitex_id = company.sanitex_owner_partner_id and company.sanitex_owner_partner_id.id or False
#         if bls_id or sanitex_id:
#             for id in ids:
#                 vals = {
#                     'sender1_id': False,
#                     'sender2_id': False
#                 }
#                 i = 1
#                 route = self.browse(cr, uid, id, context=context)
#                 for sale in route.sale_ids:
#                     if sale.owner_id and sale.owner_id.owner_code and sale.owner_id.owner_code[:3] == SANITEX_OWNER_ID \
#                         and sanitex_id \
#                     :
#                         vals['sender' + str(i) + '_id'] = sanitex_id
#                         i += 1
#                         sanitex_id = False
#                         
#                     if sale.owner_id and sale.owner_id.owner_code and sale.owner_id.owner_code[:3] != SANITEX_OWNER_ID \
#                         and bls_id \
#                     :
#                         vals['sender' + str(i) + '_id'] = bls_id
#                         i += 1
#                         bls_id = False
#                         
#                     if bls_id and sale and (not sale.owner_id or (sale.owner_id and not sale.owner_id.owner_code)):
#                         vals['sender' + str(i) + '_id'] = bls_id
#                         i += 1
#                         bls_id = False
#                         
#                 if vals:
#                     self.write(cr, uid, [id], vals, context=context)
#         return True
    
    @api.multi
    def get_all_related_invoices(self):
#         invoice_ids = []
        invoices = self.env['account.invoice']
#         route = self.browse(cr, uid, id, context=context)
        for sale in self.sale_ids:
            for invoice in sale.get_invoices():
                if invoice.state != 'cancel' \
                    and invoice.owner_id and invoice.owner_id.waybill_declare \
                    and not invoice.ivaz_declared_from_transportation \
                    and invoice.category in ['invoice','picking'] \
                    and (
                        invoice.owner_id.waybill_declare_date_from \
                        and invoice.owner_id.waybill_declare_date_from <= invoice.date_invoice\
                        or not invoice.owner_id.waybill_declare_date_from\
                    )\
                :
                    invoices += invoice
#             for line in sale.order_line:
#                 for invoice_line in line.invoice_line_ids:
#                     if invoice_line.invoice_id.id not in invoice_ids and invoice_line.invoice_id.state != 'cancel' \
#                         and invoice_line.invoice_id.owner_id and invoice_line.invoice_id.owner_id.waybill_declare \
#                     :
#                         invoice_ids.append(invoice_line.invoice_id.id)
        return invoices
    
    @api.multi
    def route_release_check(self):
        for route in self:
            if not route.location_id:
                raise UserError(_('Driver is not selected'))
            if not route.license_plate:
                if not route.location_id.license_plate:
                    raise UserError(_('License plate is not filled'))
            route.sale_ids.route_released()
    
    @api.model
    def cron_extend_task_for_released_routes(self):
        # Dėl netikėtų priežasčių išleidžiant maršrutą galėjo neprasitęsti jo užduotys,
        # bet pats maršrutas išsileisti, taip gali atsitikti nes užduotys prasitesia atskiroje gijoje.
        # Šis cronas bandys surasti tokius maršrutus ir juos sutvarkyti
        
        twenty_minutes_ago = datetime.now() - timedelta(seconds=3600)
        routes = self.search([
            ('state','in',['released', 'closed']),
            ('tasks_extended','=',False),
            ('departure_time','<',twenty_minutes_ago.strftime('%Y-%m-%d %H:%M:%S'))
        ])
        _logger.info('Found %s bad routes %s' % (
            len(routes), str(routes.mapped('id'))
        ))
        for route in routes:
            try:
                route.sale_ids.extend_chain()
                route.write({'tasks_extended': True})
                self.env.cr.commit()
            except Exception as e:
                err_note = 'Failed extend tasks route(ID: %s): %s \n\n' % (str(route.id), tools.ustr(e),)
                trb = traceback.format_exc() + '\n\n'
                _logger.info(err_note + trb)
                self.env.cr.rollback()
            
    
    @api.multi
    def _extend_tasks(self):
        # Atskiroje gijoje paleidžiamas užduočių pratesimas.
        # Taip daroma dėl to kad greičiau įvyktų maršruto išleidimas,
        # nes užduotys prasitesinėja išleidžiant maršrutą.
        
        
        context = self.env.context or {}
        ctx_commit = context.copy()
        ctx_commit['commit_after_each_task_extention'] = True
        
        with Environment.manage():
            new_cr = self.pool.cursor()
            self = self.with_env(self.env(cr=new_cr))
            try:
                for route in self:
                    _logger.info('Extending tasks with IDs: %s for route (%s, ID: %s)' % (
                        route.sale_ids.mapped('id'), route.name, str(route.id)
                    ))
                    route.sale_ids.with_context(ctx_commit).extend_chain()
                    route.write({
                        'tasks_extended': True
                    })
                    _logger.info('Extending tasks for route (%s, ID: %s) finished' % (
                        route.name, str(route.id)
                    ))
                new_cr.commit()
            finally:
                new_cr.close()
        return {}
        
    
    @api.multi
    def extend_tasks_in_thread(self):
        put_in_queue = self.env['res.company'].get_put_in_queue('_extend_tasks')
        if put_in_queue:
            for route in self:
                self.env['action.queue'].create({
                    'function_to_perform': '_extend_tasks',
                    'object_for_action': 'stock.route',
                    'id_of_object': route.id
                })
        else:
            threaded_calculation = threading.Thread(
                target=self._extend_tasks
            )
            threaded_calculation.start()

    @api.multi
    def fix_route_for_releasing(self):
        # Maršrutas negali važiuoti į kelis skirtingus sandėlius, todėl prie visų tarpfilialinių
        # užduočių turi būti tas pats tikslo sandėlis
        for route in self:
            if route.type in ['internal', 'mixed']:
                route.sale_ids.filtered(lambda task_rec:
                    task_rec.shipping_warehouse_id != task_rec.warehouse_id \
                    and task_rec.shipping_warehouse_id != route.destination_warehouse_id
                ).write({'shipping_warehouse_id': route.destination_warehouse_id.id})



    @api.multi
    def action_release_confirm(self):
        # patikrina ar galima išleisti maršrutą, iškviečia funkciją
        # kuri pratesia užduočių grandines ir iškviečia maršruto išleidimą

        context = self.env.context or {}
        route = self[0]
        if route.type == 'mixed':
            raise UserError(
                _('Mixed routing functionality is not used anymore. \
Choose an intermediate warehouse - your own, where you work, to deliver the goods directly to customers (distribution route), \
or specify another warehouse for which the cargo will be transported (interbranch route).'))
        route.fix_route_for_releasing()
        route.fix_bad_route()
        route.route_release_check()
        self.action_release()
        if context.get('extend_sale_not_in_separate_thread', False):
            self.mapped('sale_ids').extend_chain()
            self.write({
                'tasks_extended': True
            })
        else:
            self.extend_tasks_in_thread()
        return True
        
    @api.multi
    def action_assign_intermediate_route(self):
        #
        route = self[0]
        if not route.sale_ids:
            raise UserError(_('There are no tasks to add an intermediate warehouse to.'))
        context = self._context or {}
        ctx = context.copy()
        ctx['active_ids'] = [route.id]
        route.sale_ids.write({'boolean_for_intermediate_wizard': True})
        osv = self.env['stock.route.release.select_intermediate_warehouse.osv'].create({
            'available_sale_ids': [(6, 0, route.sale_ids.mapped('id'))],
            'route_id': route.id
        })
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.route.release.select_intermediate_warehouse.osv',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': ctx,
            'res_id': osv.id,
            'nodestroy': True,
        }

    @api.multi
    def get_route_number(self):
        if self.env.user.company_id.do_use_new_numbering_method():
            doc_env = self.env['document.type']
            return doc_env.get_next_number_by_code(
                'config_sanitex_delivery.product_packing',
                warehouse=self.warehouse_id,
                owner=self.env.user.company_id.loadlist_report_sender_id
            )
        else:
            return self.warehouse_id.sequence_for_route_id.next_by_id()
            
    @api.multi
    def action_release(self):
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        vals = {
            'state': 'released',
            'release_user_id': self.env.uid,
        }
        vals['departure_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
        for route in self:
            route.update_version()
            if not route.license_plate:
                if route.location_id.license_plate:
                    vals['license_plate'] = route.location_id.license_plate
            if route.warehouse_id:
                if not route.name:
                    if route.temp_route_number:
                        vals['name'] = route.temp_route_number
                    else:
                        vals['name'] = route.get_route_number()
                        route.write({'temp_route_number': vals['name']})
                        if commit:
                            self.env.cr.commit()
            route.write(vals)
            route.remove_not_printed_packings()
            if route.type in ['mixed']:
                for container_line in route.container_line_ids:
                    tasks = container_line.get_transportation_task()
                    for task in tasks:
                        if task.warehouse_id == task.shipping_warehouse_id:
                            container_line.container_id.write({'state': 'transported'})
            if route.type in ['out']:
                route.container_line_ids.mapped('container_id').write({'state': 'transported'})

            if route.picking_ids:
                for picking in route.picking_ids:
                    if route.source_location_id and picking.location_id.id != route.source_location_id.id:
                        picking.write({'location_id': route.source_location_id.id})
                        picking.move_lines.write({'location_id': route.source_location_id.id})
                    self.with_context(create_invoice_document_for_picking=True).confirm_picking(picking.id)
                    picking.send_tare_qty_info()
            route.send_route_to_ivaz()
            if commit:
                self.env.cr.commit()
                
            #Dokumentam ir ju eilutems taip pat paupdateinamas versijos timestampas
            for invoice in route.invoice_ids:
                invoice.set_version()
                invoice.invoice_line_ids.set_version()
            for stock_route_container in self.container_line_ids:
                if stock_route_container.container_id:
                    stock_route_container.container_id.set_version()
        self.update_last_route_info_in_documents()
        return True

    @api.multi
    def butt(self):
        return self.send_route_to_ivaz()
    
    @api.multi
    def send_route_to_ivaz(self, cron=True):
        self.ensure_one()
        context = self.env.context or {}

        put_in_queue = True
        if put_in_queue and not context.get('action_from_queue', False):
            self.env['action.queue'].create({
                'function_to_perform': 'send_route_to_ivaz',
                'object_for_action': 'stock.route',
                'id_of_object': self.id
            })
        else:
            ai_env = self.env['account.invoice']
            invoice_ids = self.get_all_related_invoices().mapped('id')

            invoices = ai_env.browse(invoice_ids)
            if cron:
                return invoices.export_invoices_to_ivaz_threaded(self)
            else:
                return invoices.export_invoices_to_ivaz(self)
        
#     def send_route_to_ivaz(self, cr, uid, id, cron=True, context=None):
#         ai_obj = self.env('account.invoice')
#         invoice_ids = self.get_all_related_invoices(cr, uid, [id], context=context).mapped('id')
#         if cron:
#             return ai_obj.export_invoices_to_ivaz_threaded(cr, uid, invoice_ids, id, context=context)
#         else:
#             return ai_obj.export_invoices_to_ivaz(cr, uid, invoice_ids, id, context=context)

    @api.model
    def confirm_picking(self, picking_id):
        pick_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        deleted = False
        
        for i in range(1):
            picking = pick_obj.browse(picking_id)
            if picking.state == 'done':
                break
            
            if not move_obj.search([
                ('picking_id','=',picking_id)
            ]):
                deleted = True
                picking.with_context(recompute=False).unlink()
                break
            
            if picking.state == 'draft':
                picking.action_confirm_bls()
        if deleted:
            return False
            
        picking = pick_obj.browse(picking_id)
        if picking.move_lines:
            picking.move_lines.calculate_reconcilations()
        return True

    @api.multi
    def fix_bad_route(self):
        # Kažkodėl kartais nepasikuria maršrute konteinerių eilutės,
        # nepasiskaičiuoja dokumentai, užsakymų kiekis ir kiti dalykai
        # Ši funkcija turėtų perskaičiuoti tuos dalykus

        for route in self:
            task_count = len(route.sale_ids)
            version = False
            if task_count > 0:
                if not route.invoice_ids:
                    t = time.time()
                    route.update_related_documents()
                    _logger.info('Route %s. Generated documents (%.5f)' % (str(route.id), time.time() - t))

                    t = time.time()
                    route.update_last_route_info_in_documents()
                    _logger.info('Route %s. Updated documents (%.5f)' % (str(route.id), time.time() - t))

                    t = time.time()
                    route.update_shipping_warehouse_id_filter()
                    route.update_picking_warehouse_id_filter()
                    _logger.info('Route %s. Updated filters (%.5f)' % (str(route.id), time.time() - t))
                    version = True

                if len(route.container_line_ids) != task_count:
                    t = time.time()
                    route.update_containers()
                    _logger.info('Route %s. Generated container lines (%.5f)' % (str(route.id), time.time() - t))
                    version = True
                    if len(route.container_line_ids) != task_count:
                        t = time.time()
                        route.sale_ids.create_container_for_sale()
                        route.update_containers()
                        _logger.info('Route %s. Generated containers and container lines (%.5f)' % (
                            str(route.id), time.time() - t
                        ))
                if not route.sale_count and route.sale_count == 0:
                    t = time.time()
                    route.update_counts()
                    _logger.info('Route %s. Count updated (%.5f)' % (str(route.id), time.time() - t))
                    version = True
                if route.weight or route.weight == 0:
                    t = time.time()
                    route.update_weight()
                    _logger.info('Route %s. Weigh updated (%.5f)' % (str(route.id), time.time() - t))
                    version = True
            if version:
                route.update_version()



    @api.model
    def cancel_picking(self, picking_id):
        pick_obj = self.env['stock.picking']

        for i in range(5):
            picking = pick_obj.browse(picking_id)
            if picking.state == 'draft':
                break
            if picking.state not in ['cancel', 'draft']:
                picking.action_cancel_bls()
                
            # picking = pick_obj.browse(cr, uid, picking_id, context=context)
            
            if picking.state == 'cancel':
                picking.action_return_to_draft()
        
        picking = pick_obj.browse(picking_id)
        if picking.move_lines:
            picking.move_lines.calculate_reconcilations()
        return True

    @api.multi
    def action_add_remove_object(self):
        for route in self:
            if route.state != 'released':
                raise UserError(
                    _('Route has to be released')
                )
            if route.return_picking_created:
                raise UserError(
                    _('You can\'t do that, because tare return from driver is already done.'),
                )
        context = self.env.context or {}
        ctx = context.copy()
        ctx['active_model'] = self._name
        ctx['active_ids'] = self.mapped('id')
        return {
            'name': _('Select Product'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.route.add_remove.tare.osv',
            'target': 'new',
            'context': ctx
        }
    
    @api.multi
    def action_return_driver_packing(self):
        for route in self:
            if route.state != 'released':
                raise UserError(
                    _('Route has to be released')
                )
            for packing in route.packing_for_client_ids:
                if packing.state == 'draft':
                    raise UserError(
                        _('All client packings has to be done')
                    )
            if route.return_picking_created:
                raise UserError(
                    _('Return picking is already done'),
                )
            user = self.env.user
            user.check_default_wh_region()
            if user.default_warehouse_id:
                return_location = route.return_location_id
                if return_location:
                    return_warehouse = return_location.get_location_warehouse_id()
                    if return_warehouse != user.default_warehouse_id:
                        raise UserError(
                            _('Return location \'%s\' specified in route %s does not belong to your warehouse \'%s\'. Please change return location before returning tare.') % (
                                return_location.name, route.name, user.default_warehouse_id.name
                            )
                        )
            elif user.default_region_id:
                if route.return_location_id != user.default_region_id.get_return_location():
                    route.write({
                        'return_location_id': user.default_region_id.get_return_location().id
                    })
        context = self.env.context or {}
        ctx = context.copy()
        ctx['active_model'] = self._name
        ctx['active_ids'] = self.mapped('id')
        return {
            'name': _('Return'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.route.return_driver_packing.osv',
            'target': 'new',
            'context': ctx
        }

    @api.multi
    def get_return_act_picking(self):
        context = self.env.context or {}
        if context.get('picking_id_for_tare_act', False):
            picking = self.returned_picking_ids.filtered(lambda pick_rec: pick_rec.id == context['picking_id_for_tare_act'])
        else:
            picking = self.returned_picking_ids and self.returned_picking_ids[0] or self.returned_picking_ids
        return picking

    @api.multi
    def get_return_act_owner(self):
        context = self.env.context or {}
        if context.get('picking_id_for_tare_act', False):
            picking = self.returned_picking_ids.filtered(lambda pick_rec: pick_rec.id == context['picking_id_for_tare_act'])
        else:
            picking = self.returned_picking_ids[0]
        if picking and picking.move_lines:
            owners = picking.move_lines.mapped('product_id').mapped('owner_id')
            if owners:
                return owners[0].get_owner_dict()
        return {}

    @api.multi
    def action_close_multiple_routes(self):
        # Metodas, kuris uždaro kelis maršrutus. Galima uždarinėti tik tuos, kurie neturi taros

        _logger.info('Closing multiple(%s) routes STARTED'% str(len(self)))
        errors = {}
        closed = 0
        not_closed = 0
        for route in self:
            route_name = route.name or ('ID-'+str(route.id))
            try:
                if route.state == 'draft':
                    raise UserError(_('Route is not released.'))
                if route.state == 'closed':
                    raise UserError(_('Route is already closed.'))
                if route.type == 'internal':
                    raise UserError(_('Route is interbranch.'))
                if route.type == 'mixed':
                    raise UserError(_('Route is mixed.'))
                if route.related_move_ids:
                    raise UserError(_('Route has tare movement.'))
                route.action_close()
                closed += 1
                self.env.cr.commit()
            except Exception as e:
                not_closed += 1
                self.env.cr.rollback()
                error_message = tools.ustr(e)
                if error_message not in errors:
                    errors[error_message] = []
                errors[error_message].append(route_name)

            _logger.info('Route %s: %s / %s' % (route_name, str(closed + not_closed), str(len(self))))
        if errors:
            user_error_message = str(closed) + ' ' + _('routes were closed.') + ' ' + str(not_closed) + ' ' + _('routes did not close:')
            for error in errors.keys():
                user_error_message += '\n' + str(len(errors[error])) + ' ' + _('routes') + ' - ' + error + '[' + ', '.join(errors[error]) + ']'

            context = self.env.context or {}
            ctx = context.copy()
            ctx['active_ids'] = self.ids
            ctx['action_model'] = self._name
            ctx['action_function'] = 'dummy_print'
            ctx['warning'] = user_error_message
            ctx['just_close'] = True

            form_view = self.env.ref('config_sanitex_delivery.object_action_warning_osv_form', False)[0]
            _logger.info('Closing multiple(%s) routes FINISHED'% str(len(self)))

            return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'object.confirm.action.osv',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': ctx,
                'nodestroy': True,
                'views': [(form_view.id, 'form')],
            }
        _logger.info('Closing multiple(%s) routes FINISHED'% str(len(self)))
        return False


    @api.multi
    def action_cancel(self):
        vals = {
            'state': 'draft',
#             'release_date': False,
            'release_user_id': False, 
            'departure_time': False,
        }
        for route in self:
            if route.state == 'closed':
                raise UserError(
                    _('You can\'t cancel closed route (ID: %s)') %str(route.id)
                )
            for packing in route.packing_for_client_ids: 
                if packing.state == 'done':
                    raise UserError(
                        _('You can\'t cancel route (%s, ID: %s) because it has client packing(%s, ID: %s) which are already done') %(
                            route.name, str(route.id), packing.number, str(packing.id)
                        )
                    )
                
            if route.picking_id:
                self.cancel_picking(route.picking_id.id)
            
        self.write(vals)
        return True
    
    @api.multi
    def action_confirm_packings(self):
        if not self.packing_for_client_ids:
            raise UserError(_('There are no packings to confirm in route %s') % self.name)
        self.env.user.check_default_wh_region()
        context = self._context or {}
        ctx = context.copy()
        ctx['active_ids'] = [self.id]
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.route.packing.confirm_selected.osv',
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': ctx,
            'nodestroy': True,
        }
    
    @api.multi
    def do_not_print_driver_return(self):
        log_env = self.env['report.print.log']
        report_env = self.env['ir.actions.report']
        for route in self:
            if route.returned_picking_ids:
                for picking in route.returned_picking_ids:
                    if not log_env.search([
                        ('object','=','stock.picking'),
                        ('rec_id','=',picking.id)
                    ]):
                        report_env.do_not_print_report(picking, 'config_sanitex_delivery.packing_return_act')

    @api.multi
    def close_containers(self):
        close_sql = '''
            UPDATE
                stock_package sp
            SET
                planned_collection = False
            FROM
                stock_route_container src,
                account_invoice_container aic
            WHERE
                src.route_id = %s
                AND aic.id=src.container_id
                AND sp.id = aic.package_id
                AND sp.planned_collection = True
        '''
        close_where = (self.id,)
        self.env.cr.execute(close_sql, close_where)

        close_sql = '''
            UPDATE
                account_invoice_container aic
            SET
                state = 'in_terminal'
            FROM
                stock_route_container src,
                sale_order so,
                sale_order_container_rel socr
            WHERE
                src.route_id = %s
                AND aic.id = src.container_id
                AND socr.cont_id = aic.id
                AND socr.sale_id = so.id
                AND so.delivery_type = 'collection'  
        '''
        close_where = (self.id,)
        self.env.cr.execute(close_sql, close_where)

        close_sql = '''
            UPDATE
                account_invoice_container aic
            SET
                state = 'delivered'
            FROM
                stock_route_container src,
                sale_order so,
                sale_order_container_rel socr
            WHERE
                src.route_id = %s
                AND aic.id = src.container_id
                AND socr.cont_id = aic.id
                AND socr.sale_id = so.id
                AND so.delivery_type = 'delivery'
                AND so.replanned != True 
        '''
        close_where = (self.id,)
        self.env.cr.execute(close_sql, close_where)
        
        select_sql = '''
            SELECT
                aic.package_id
            FROM
                stock_route_container src
                LEFT JOIN account_invoice_container aic on (aic.id=src.container_id)
            WHERE
                src.route_id = %s
                and aic.package_id is not null
        '''
        select_where = (self.id,)
        self.env.cr.execute(select_sql, select_where)
        package_ids = self.env.cr.fetchall()
        if package_ids:
            packages = self.env['stock.package'].browse([package_id[0] for package_id in package_ids])
            packages.update_state()
        
    @api.multi
    def action_close(self):
        for route in self:
            for packing in route.packing_for_client_ids: 
                if packing.state != 'done':
                    raise UserError(
                        _('You can\'t close route (%s, ID: %s) because it has client packing(%s, ID: %s) which are not done') %(
                            route.name, str(route.id), packing.number, str(packing.id)
                        )
                    )
            route.sale_ids.check_if_can_close_route()

            # for sale in route.sale_ids:
            #     if sale.state != 'cancel' and sale.warehouse_id.id != sale.shipping_warehouse_id.id and not sale.route_state_received and not sale.not_received:
            #         raise UserError(_('You can\'t close route %s. Because task %s witch is going to %s is neither received or not received.') % (
            #             route.name, sale.name, sale.shipping_warehouse_id.name
            #         ))

            if route.type in ['out', 'mixed']:
                route.close_containers()
                # containers = route.container_line_ids.mapped('container_id')
                # containers.mapped('package_id').filtered('planned_collection').write({'planned_collection': False})
                # registered_containers = self.env['account.invoice.container']
                # delivered_containers = self.env['account.invoice.container']
                # for container_line in route.container_line_ids:
                #     tasks = container_line.get_transportation_task()
                #     for task in tasks:
                #         if task.warehouse_id == task.shipping_warehouse_id:
                #             if task.delivery_type == 'collection' and container_line.container_id.state != 'registered':
                #                 registered_containers += container_line.container_id
                #             elif task.delivery_type == 'delivery' and container_line.container_id.state != 'delivered':
                #                 delivered_containers += container_line.container_id
                # registered_containers.write({'state': 'in_terminal'})
                # delivered_containers.write({'state': 'delivered'})
            route.do_not_print_driver_return()
            # route.in_picking_id.send_tare_qty_info()
            # route.returned_picking_id.send_tare_qty_info()
            # route.out_picking_id.send_tare_qty_info()
            # for packing in route.packing_for_client_ids:
            #     packing.in_picking_id and packing.in_picking_id.send_tare_qty_info()
            #     packing.out_picking_id and packing.out_picking_id.send_tare_qty_info()
            
            
        # vals = {
        #     'state': 'closed',
        #     'return_time': time.strftime('%Y-%m-%d %H:%M:%S')
        # }

        self.env.cr.execute('''
            UPDATE
                stock_route
            SET
                state = 'closed',
                return_time = %s
            WHERE
                id in %s
        ''',(time.strftime('%Y-%m-%d %H:%M:%S'), tuple(self.ids)))

        self.env.cr.execute('''
            SELECT
                id
            FROM
                stock_route_container
            WHERE
                route_id in %s
        ''',(tuple(self.ids),))
        sr_cont_ids = [cont_id[0] for cont_id in self.env.cr.fetchall()]
        self.env['stock.route.container'].browse(sr_cont_ids).update_current_value()
        

        self.env.cr.execute('''
            SELECT
                id
            FROM
                stock_packing
            WHERE
                route_id in %s
        ''',(tuple(self.ids),))
        packing_ids = [pack_id[0] for pack_id in self.env.cr.fetchall()]
        self.invalidate_cache(fnames=['state'], ids=list(self._ids))
        self.env['stock.packing'].browse(packing_ids).recalc_route_state()
        
        # self.write(vals)
        self.with_context(no_closed_edit=False).update_act_status()
        self.update_scanning_log(_('Route was closed.'))
        self.with_context(no_closed_edit=False).reset_document_scanning()
        return {
            'type': 'ir.actions.client',
            'tag': 'breadcrumb_back',
        }

    @api.multi
    def generate_bill(self):
        return True

    @api.model
    def update_args(self, args):
        context = self.env.context or {}
        if context.get('args_updated', False):
            return True
        # context['args_updated'] = True
        
        usr_obj = self.env['res.users']
        #apejimas, kad neismestu is sukurto objekto
        if args and type(args[0]) == type([]) and len(args[0]) > 1 \
            and args[0][0] == 'id' and args[0][1] == 'in' \
            and context.get('search_default_current', False) \
        :
            del context['search_default_current']
            
        if args and type(args[0]) == type([]) and len(args[0]) > 1 \
            and args[0][0] == 'id' and args[0][1] == 'in' \
            and context.get('get_current_routes', False) \
        :
            pass
            # del context['get_current_routes']
            
        # if not context.get('get_all_routes', False):# and self.env.uid != 1:
        #     wh_obj = self.env['stock.warehouse']
        #     whs = wh_obj.search([
        #         ('responsible_user_ids','in',[self.env.uid])
        #     ])
        #     args.append('|')
        #     args.append(('type','=','mixed'))
        #     args.append('|')
        #     args.append(('warehouse_id','in',whs.mapped('id')))
        #     args.append(('destination_warehouse_id','in',whs.mapped('id')))
            
        if context.get('get_current_routes', False):
            tomorrow = datetime.now() + timedelta(days=1)
            args.append(('date','<=',tomorrow))
            args.append(('date','>=',time.strftime('%Y-%m-%d')))

        if context.get('get_incoming_routes', False):
            user = usr_obj.browse(self.env.uid)
            default_warehouse_id = user.default_warehouse_id and user.default_warehouse_id.id or False
            args.append(('state','=','released'))
            args.append(('type','!=','out'))
            args.append('|')
            args.append(('fully_received_warehouses_ids_char','not ilike','%id' + str(default_warehouse_id) + 'id%'))
            args.append(('fully_received_warehouses_ids_char','=',False))
            if user.default_region_id:
                self.env.cr.execute('''
                    SELECT
                        id
                    FROM
                        stock_route
                    WHERE
                        type = 'mixed'
                        AND state = 'released'
                        AND shipping_warehouse_id_filter = fully_received_warehouses_ids_char
                ''')
                res_res = self.env.cr.fetchall()
                res_ids = [res_id[0] for res_id in res_res]
                if res_ids:
                    args.append(('id','not in',res_ids))
        
        if context.get('search_by_user', False):# and uid!= 1:
            user = usr_obj.browse(self.env.uid)
            allowed_wh_ids = user.get_current_warehouses().mapped('id')
            if (user.default_warehouse_id or user.default_region_id) and context.get('search_by_user_type', '') == 'incoming':
                args.extend([
                    # ('warehouse_id','!=',user.default_warehouse_id.id),
                    ('state','!=','draft'),
                    '|',
                    '&',
                    ('type','=','internal'),
                    ('destination_warehouse_id','in',allowed_wh_ids),
                    '&',
                    ('type','=','mixed'),
                    # ('shipping_warehouse_id_filter','like','%id'+str(user.default_warehouse_id.id)+'id%')
                ])
                for allowed_wh_id in allowed_wh_ids:
                    args.append('|')
                    args.append(('shipping_warehouse_id_filter','like','%id'+str(allowed_wh_id)+'id%'))
                args.pop(-2)
            elif (user.default_warehouse_id or user.default_region_id) and context.get('search_by_user_type', '') == 'outgoing':
                for allowed_wh_id in allowed_wh_ids:
                    args.append('|')
                    args.append(('picking_warehouse_id_filter','like','%id'+str(allowed_wh_id)+'id%'))
                # args.pop(-2)
                args.extend([('warehouse_id','in',allowed_wh_ids)])
            elif user.default_warehouse_id or user.default_region_id:
                args.extend(['|',('warehouse_id','=',user.default_warehouse_id.id),('destination_warehouse_id','=',user.default_warehouse_id.id)])

        return True

    @api.model
    def _search(
        self, args, offset=0, limit=None,
        order=None, count=False,
        access_rights_uid=None
    ):
        context = self.env.context or {}
        ctx = context.copy()
        self.with_context(ctx).update_args(args)
        return super(StockRoute, self.with_context(ctx))._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):

        # context = self.env.context
        # ctx = context.copy()
        # self.with_context(ctx).update_args(args)
        
        return super(StockRoute, self).search(
            args, offset=offset, limit=limit,
            order=order, count=count
        )

    @api.multi
    def get_source_location(self):
        if self.source_location_id:
            return self.source_location_id.id
        if self.warehouse_id and self.warehouse_id.wh_output_stock_loc_id:
            return self.warehouse_id.wh_output_stock_loc_id.id
        return False
    
    @api.multi
    def get_return_location(self, type='out'):
        if self.return_location_id:
            return self.return_location_id.id
        if self.type == 'out':            
            if self.warehouse_id and self.warehouse_id.wh_return_stock_loc_id:
                return self.warehouse_id.wh_return_stock_loc_id.id
        else:
            if self.destination_warehouse_id and self.destination_warehouse_id.wh_return_stock_loc_id:
                return self.destination_warehouse_id.wh_return_stock_loc_id.id
        return False

    @api.multi
    def get_destination_location(self):
        if self.warehouse_id and self.warehouse_id.wh_output_stock_loc_id:
            return self.warehouse_id.wh_output_stock_loc_id.id
        return False

    @api.multi
    def get_defect_location(self):
        if self.warehouse_id and self.warehouse_id.wh_defect_stock_loc_id:
            return self.warehouse_id.wh_defect_stock_loc_id.id
        return False

    @api.multi
    def get_client_location(self):
        loc_obj = self.env['stock.location']
        location = loc_obj.search([
            ('usage','=','customer')
        ], limit=1)
        
        return location and location.id or False

    @api.multi
    def get_supplier_location(self):
        loc_obj = self.env['stock.location']
        location = loc_obj.search([
            ('name','=','Suppliers')
        ], limit=1)
        
        return location and location.id or False

    @api.model
    def get_related_move_ids(self, field_name):
        ids = []
        try:
            if field_name != 'related_move_ids' and field_name.startswith('related_move_ids'):
                picking_name = field_name[len('related_move_ids_'):]
                move_ids_sql = '''
                    SELECT
                        sm.id
                    FROM
                        stock_move sm
                        LEFT JOIN stock_picking sp on (sp.id = sm.picking_id)
                    WHERE
                        sp.name = %s
                '''
                move_ids_where = (picking_name,)
                self.env.cr.execute(move_ids_sql,move_ids_where)
                ids = [res[0] for res in self.env.cr.fetchall()]
        except:
            pass
        return ids


    @api.multi
    def read(self, fields=None, load='_classic_read'):
        res = super(StockRoute, self).read(fields=fields, load=load)
        for field in fields:
            if field.startswith('related_move_ids_'):
                for route_read in res:
                    route_read[field] = self.get_related_move_ids(field)
        return res

    @api.multi
    def remove_not_needed_packings(self):
        # Ruošiniai maršrute, kuriasi pagal susijusias užduotis.
        # Iš maršruto išėmus užduotis turi išsitrinti ir susiję ruošiniai.
        pack_obj = self.env['stock.packing']
        context = self.env.context or {}
        if context.get('skip_packing_remove', False):
            return False
        ctx_del = context.copy()
        ctx_del['allow_unlink_packing'] = True
        to_delete_ids = []
        for route in self:
            if route.packing_for_client_ids:
                for packing in route.packing_for_client_ids:
                    all_orders_of_posid_removed_from_route = True
                    for order in route.sale_ids:
                        if order.partner_shipping_id and packing.address_id\
                            and order.partner_shipping_id.id == packing.address_id.id\
                        :
                            all_orders_of_posid_removed_from_route = False
                            break
                    if all_orders_of_posid_removed_from_route:
                        to_delete_ids.append(packing.id)
        packings = pack_obj.with_context(ctx_del).browse(to_delete_ids)
        packings.unlink()

    @api.multi
    def check_route(self):
        for route in self:
            if route.warehouse_id and route.destination_warehouse_id \
                and route.warehouse_id.id == route.destination_warehouse_id.id \
            :
                raise UserError(
                    _('Route(%s: ID: %s) can\'t have same source and destination warehouses') % (
                        (route.receiver, str(route.id))
                    )
                )
            if not route.warehouse_id:
                raise UserError(_('You have to fill in a warehouse.'))


    @api.model
    def update_vals(self, vals):
        if vals.get('location_id', False):
            vals['driver_name'] = self.env['stock.location'].browse(vals['location_id']).name
            vals['driver_picked'] = True

    @api.multi
    def write(self, vals):
        context = self.env.context or {}
        if 'closed' in self.mapped('state') and context.get('no_closed_edit', False):
            raise UserError('You can\'t update closed route.')

        # if vals.get('type', False):
        #     if vals['type'] in ['mixed']:
        #         for route in self:
        #             if route.type != vals['type'] and vals['type'] != route.sale_ids.get_type_for_route():
        #                 raise UserError(_('You cant change route type to %s. Use button \'Assign intermediate Warehouse\'') % vals['type'])



        self.update_vals(vals)

        res = super(StockRoute, self).write(vals)
        if vals.get('destination_warehouse_id', False):
            if vals.get('type', '') == 'internal':
                self.mapped('sale_ids').write({'shipping_warehouse_id': vals['destination_warehouse_id']})
            self.update_route_type(destination_changed_in_route=True)
        elif vals.get('type', '') == 'internal':
            for route in self:
                if route.destination_warehouse_id:
                    route.sale_ids.write({'shipping_warehouse_id': route.destination_warehouse_id.id})
            self.update_route_type(destination_changed_in_route=True)
        # if vals.get('sale_ids', False) or vals.get('state', False) or vals.get('destination_warehouse_id', False):
        #     self.mapped('sale_ids').update_shipping_warehouse_route_released()
                    
        if vals.get('sale_ids', False):
            self.remove_not_needed_packings()
            self.update_counts()
            self.update_weight()
            self.update_shipping_warehouse_id_filter()
            self.update_picking_warehouse_id_filter()
            self.update_route_type()
            self.update_containers()
            self.update_related_documents()
        self.check_route()
        if 'state' in vals.keys():
            self.mapped('container_line_ids').update_current_value()

        if 'type' in vals.keys():
            if vals['type'] == 'out':
                self.convert_route_to_out()
            if vals['type'] == 'mixed':
                self.convert_route_to_mixed()
            if vals['type'] == 'internal':
                self.convert_route_to_internal()

            # else:
            #     self.update_route_type()

        if 'state' in vals.keys() or 'packing_for_client_ids' in vals.keys():
            for route in self:
                route.packing_for_client_ids.recalc_route_state()
        
        return res

    @api.multi
    def get_document_ids(self):
        if self:
            document_sql = '''
                SELECT
                    rel.invoice_id
                FROM
                    stock_route sr
                    JOIN stock_route_invoice_rel rel on (rel.route_id = sr.id)
                WHERE
                    sr.id = %s
            '''
            document_where = (self.id,)
            self.env.cr.execute(document_sql, document_where)
            return [res[0] for res in self.env.cr.fetchall()]
        return []

    @api.multi
    def get_document_ids_by_document_name(self):
        if self:
            document_sql = '''
                SELECT
                    ai.id, ai.name
                FROM
                    stock_route sr
                    JOIN stock_route_invoice_rel rel on (rel.route_id = sr.id)
                    JOIN account_invoice ai on (rel.invoice_id = ai.id)
                WHERE
                    sr.id = %s
            '''
            document_where = (self.id,)
            self.env.cr.execute(document_sql, document_where)
            return 
        return []

    @api.multi
    def get_related_document_data_for_check_up(self):
        document_info = []
        document_ids = self.get_document_ids()
        if document_ids:
            documnet_info_sql = '''
                SELECT
                    id, 
                    all_document_numbers,
                    sending_type,
                    delivery_type
                FROM 
                    account_invoice 
                WHERE 
                    id in %s
            '''
            documnet_info_where = (tuple(document_ids),)
            self.env.cr.execute(documnet_info_sql, documnet_info_where)
            document_info = self.env.cr.fetchall()
        return document_info



    @api.multi
    def create_scanning_lines(self):
        # Sukuriamos skenavimo eilutės maršrutui. Pagal eilutes matosi kuris dokumentas
        # buvo nuskenuotas, kuris dar ne.
        scan_env = self.env['stock.route.document.scanning']
        for route in self:
            if not route.document_scanning_line_ids:
                route.update_scanning_log(
                    _('Document scaning started at %s by %s') % (utc_str_to_local_str(), self.env.user.name)
                )
            document_info = route.get_related_document_data_for_check_up()
            # document_ids = route.get_document_ids()
            # if document_ids:
            #     documnet_info_sql = '''
            #         SELECT
            #             id,
            #             all_document_numbers,
            #             sending_type,
            #             delivery_type
            #         FROM
            #             account_invoice
            #         WHERE
            #             id in %s
            #     '''
            #     documnet_info_where = (tuple(document_ids),)
            #     self.env.cr.execute(documnet_info_sql, documnet_info_where)
            #     document_info = self.env.cr.fetchall()
            for document in document_info:
                line_vals = {'invoice_type': 'need_scanning', 'scanned': route.fully_checked}
                if document[3] and document[3] == 'collection':
                    line_vals['invoice_type'] = 'collection_package'
                elif document[2] and document[2] == 'electronical':
                    line_vals['invoice_type'] = 'digital_doc'

                for document_no in document[1].split(','):
                    scan_env.create_if_not_exists(route.id, document[0], document_no.strip(), line_vals)

    @api.multi
    def reset_document_scanning(self):
        # Nuresetinamos dokumentų skenavimas ištrinant scenavimo eilutes.
        for route in self:
            route.update_scanning_log(route.get_scanned_document_summary())
            route.document_scanning_line_ids.unlink()
            # route.write({
            #     'fully_checked': False,
            #     'last_user_to_reset_scannig_id': self.env.uid,
            #     'scanning_reset_datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
            #     'document_count_left_to_check': route.document_count,
            # })
            self.env.cr.execute('''
                UPDATE
                    stock_route
                SET
                    fully_checked = False,
                    last_user_to_reset_scannig_id = %s,
                    scanning_reset_datetime = %s,
                    document_count_left_to_check = %s
                WHERE
                    id = %s
            ''', (self.env.uid, time.strftime('%Y-%m-%d %H:%M:%S'), route.document_count, route.id))
            route.update_scanning_log(_('Document scanning was reset at %s by %s.') % (
                utc_str_to_local_str(), self.env.user.name
            ))


    @api.multi
    def action_run_document_check_up(self):
        # Paleidžiamas dokumentų sutikrinimas. Sukuriamos skenavimo eilutės, jeigu jos dar nebuvo sukurtos.
        if not self.fully_checked:
            self.with_context(no_closed_edit=False).create_scanning_lines()
        check_up_env = self.env['stock.route.document.check_up.osv']
        check_up_osv = check_up_env.with_context(no_closed_edit=False).create({
            'route_id': self.id,
            'log': self.scanning_log
        })
        check_up_osv.load()
        context = self.env.context or {}
        ctx = context.copy()
        ctx['active_ids'] = [self.id]
        ctx['check_up_osv_id'] = check_up_osv.id
        ctx['no_closed_edit'] = False
        # ctx['route_documents'] = self.get_document_ids_by_document_name()

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.route.document.check_up.osv',
            'target': 'new',
            'res_id': check_up_osv.id,
            'type': 'ir.actions.act_window',
            'context': ctx,
            'nodestroy': True,
        }

    @api.multi
    def convert_route_to_out(self):
        for route in self:
            if route.sale_ids.get_type_for_route != 'out':
                route.sale_ids.filtered(
                    lambda sale_rec: sale_rec.warehouse_id != route.warehouse_id
                ).write({
                    'warehouse_id': route.warehouse_id.id
                })
                route.sale_ids.filtered(
                    lambda sale_rec: sale_rec.shipping_warehouse_id != route.warehouse_id
                ).write({
                    'shipping_warehouse_id': route.warehouse_id.id
                })
            if route.state == 'draft' and route.type == 'out':
                route.action_product_act_generate()

    @api.multi
    def convert_route_to_internal(self):
        for route in self:
            if route.type == 'internal':
                route.packing_for_client_ids.unlink()

    @api.multi
    def convert_route_to_mixed(self):
        for route in self:
            if route.type == 'mixed':
                route.action_product_act_generate()



#     @api.multi
#     def fill_in_containers(self):
#         # NEBENAUDOJAMA
#         for route in self(nenaudojama):
#             container_to_be_ids = []
#             container_is_ids = [cont.id for cont in route.delivery_container_ids]
#             for package in route.delivery_package_ids:
#                 for container in package.container_ids:
#                     container_to_be_ids.append(container.id)
#             container_to_add_ids = list(set(container_to_be_ids) - set(container_is_ids))
#             container_to_remove_ids = list(set(container_is_ids) - set(container_to_be_ids))
#             containers = [(4, add_id) for add_id in container_to_add_ids] + [(3, remove_id) for remove_id in container_to_remove_ids]
#             route.write({'delivery_container_ids': containers})
#         return True
    
    @api.multi
    def fill_in_number(self):
        # seq_env = self.env['ir.sequence']
        # seq = seq_env.search([('code','=','released_route')])
        # if seq:
        for route in self:
            if route.name:
                continue
            route.write({
                'name': route.warehouse_id.sequence_for_route_id.next_by_id()
            })

    @api.model
    def create(self, vals):
        vals['release_user_id'] = self._uid
        vals['departure_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
        vals['picking_number'] = ''
        vals['return_picking_number'] = ''
        if vals.get('destination_warehouse_id', False):
            vals['destination_filled'] = True
        vals['sender1_id'] = self.get_sender()
        self.update_vals(vals)
        route = super(StockRoute, self).create(vals)
        route.write({'route_id_str': str(route.id)})
        route.check_route()
        route.update_weight()
        route.update_shipping_warehouse_id_filter()
        route.update_picking_warehouse_id_filter()
        
        route.packing_for_client_ids.recalc_route_state()
        return route
        
    @api.multi
    def get_driver(self):
        if self.location_id:
            return self.location_id.id
        else:
            model_obj = self.env['ir.model.data']
            model = model_obj.search([
                ('module','=','config_sanitex_delivery'),
                ('model','=','stock.location'),
                ('name','=','empty_stok_location')
            ], limit=1)
            if model:
                location_id = model.res_id
                return location_id
        return False
    
#     def do_not_generate(self, cr, uid, route_id, sale_id, context=None):
#         """Nebenaudojama"""
#         so_obj = self.env('sale.order')
#         prod_stock_obj = self.env('sanitex.product.partner.stock')
#         
# #         route = self.browse(cr, uid, route_id, context=context)
#         sale = so_obj.browse(cr, uid, sale_id, context=context)
#         product_ids = self.get_products_for_packing(
#             cr, uid, route_id, sale.partner_shipping_id.id, context=context
#         )#[prod.id for prod in route.warehouse_id.product_ids]
#         
#         route = self.browse(cr, uid, route_id, context=context)
#         if route.move_ids:
#             return False
#         
#         client_qty = 0.0
#         possid_qty = 0.0
#             
#         prod_stock_part_ids = prod_stock_obj.search(cr, uid, [
#             ('product_id','in',product_ids),
#             ('partner_id','=',sale.partner_id.id)
#         ], context=context)
#         for prod_stock_part_id in prod_stock_part_ids:
#             part_stocks = prod_stock_obj.browse(
#                 cr, uid, prod_stock_part_id, context=context
#             )
#             client_qty += part_stocks.qty_available
#         
#         prod_stock_possid_ids = prod_stock_obj.search(cr, uid, [
#             ('product_id','in',product_ids),
#             ('partner_id','=',sale.partner_shipping_id.id)
#         ], context=context)
#         for prod_stock_possid_id in prod_stock_possid_ids:
#             possid_stocks = prod_stock_obj.browse(
#                 cr, uid, prod_stock_possid_id, context=context
#             )
#             possid_qty += possid_stocks.qty_available
#         if possid_qty >= 0.0 and client_qty > 0.0:
#             return False
#         
#         return True
    
#     def get_products_for_packing(self, cr, uid, id, partner_id, context=None):
#         """Nebenaudojama"""
#         stck_obj = self.env('sanitex.product.partner.stock')
#         product_ids = []
#         route = self.browse(cr, uid, id, context=context)
#         if route.move_ids:
#             product_ids = [move.product_id.id for move in route.move_ids]
#         else:
#             product_ids = [prod.id for prod in route.warehouse_id.product_ids]
#         debt_prod_ids = stck_obj.search(cr, uid, [
#             ('product_id','not in',product_ids),
#             '|',('partner_id','=',partner_id),
#             ('partner_id.parent_id','=',partner_id),
#             ('qty_available','>',0)
#         ], context=context)
#         for stock_id in debt_prod_ids:
#             stck = stck_obj.browse(cr, uid, stock_id, context=context)
#             if stck.product_id.id not in product_ids:
#                 product_ids.append(stck.product_id.id)
#         
#         return product_ids 
    
#     def generate_product_act_for_sales(self, cr, uid, id, sale_ids, context=None):
#         """Nebenaudojama"""
#         pack_obj = self.env('stock.packing')
#         pack_ln_obj = self.env('stock.packing.line')
#         part_obj = self.env('res.partner')
#         prod_obj = self.env('product.product')
#         so_obj = self.env('sale.order')
# #         prod_stock_obj = self.env('sanitex.product.partner.stock')
#         
#         route = self.browse(cr, uid, id, context=context)
#         if route.state != 'draft':
#             raise osv.except_osv(
#                 _('Error'),
#                 _('Route has to be in draft state')
#             )
#         if route.type != 'out':
#             raise osv.except_osv(
#                 _('Error'),
#                 _('Route has to be \'Out\' type')
#             )
#         for sale_id in sale_ids:
#             sale = so_obj.browse(cr, uid, sale_id, context=context)
#             
#             pack_ids = pack_obj.search(cr, uid, [
#                 ('route_id','=',id),
#                 ('address_id','=',sale.partner_shipping_id.id)
#             ], context=context)
#             if not pack_ids:
#                 packing_vals = {}
#                 packing_vals['partner_id'] = sale.partner_id.id
#                 packing_vals['route_id'] = id
#                 packing_vals['address_id'] = sale.partner_shipping_id.id
#                 packing_vals['manual_packing'] = False
#                 packing_vals['warehouse_id'] = sale.warehouse_id.id
#                 packing_id = pack_obj.create(cr, uid, packing_vals, context=context)                
#                 for product in prod_obj.browse(cr, uid, 
#                     self.get_products_for_packing(
#                         cr, uid, id, sale.partner_id.id, context=context
#                     ),
#                     context=context
#                 ):
#                     line_vals = {}
#                     line_vals['product_id'] = product.id
#                     line_vals['product_code'] = product.default_code
#                     line_vals['return_to_driver_qty'] = 0.0
#                     line_vals['give_to_customer_qty'] = 0.0
#                     line_vals['customer_qty'] = part_obj.get_product_qty(
#                         cr, uid, sale.partner_shipping_id.id, 
#                         product.id, context=context
#                     )
# #                     line_vals['customer_posid_qty'] = part_obj.get_product_qty(
# #                         cr, uid, sale.partner_shipping_id.id, 
# #                         product.id, context=context
# #                     )
#                     line_vals['customer_posid_qty'] = line_vals['customer_qty']
#                     line_vals['final_qty'] = part_obj.get_product_qty(
#                         cr, uid, sale.partner_id.id, product.id, context=context
#                     )
#                     line_vals['packing_id'] = packing_id
#                     pack_ln_obj.create(cr, uid, line_vals, context=context)
#             else:
#                 packing_id = pack_ids[0]
#             so_obj.write(cr, uid, [sale_id], {'packing_id': packing_id}, context=context)
#         self.write(cr, uid, [id], {
#             'packings_generated': True
#         }, context=context)
#         return True
#     
#     def generate_product_act(self, cr, uid, ids, context=None):
#         """Nebenaudojama"""
#         for id in ids:
#             route = self.browse(cr, uid, id, context=context)
#             self.generate_product_act_for_sales(
#                 cr, uid, id, [order.id for order in route.sale_ids], context=context
#             )
#         return True
    
    @api.multi
    def get_products_for_packing_new(self, partner_id):
        if self.move_ids:
            product_ids = [move.product_id.id for move in self.move_ids]
        else:
            product_ids = []#[prod.id for prod in self.warehouse_id.product_ids]
        product_where = ''
        if product_ids:
            product_where = ' and spps.product_id not in (%s)' % ', '.join([str(product_id) for product_id in product_ids])
        self.env.cr.execute("""
            SELECT
                distinct(product_id)            
            FROM
                sanitex_product_partner_stock spps 
                JOIN res_partner rp on (spps.partner_id = rp.id)
            WHERE 
                spps.qty_available > 0
                %s 
                and (rp.id = %s or rp.parent_id = %s)
        """ % (product_where, str(partner_id), str(partner_id)))
        results = self.env.cr.fetchall()
        if results:
            for product_result in results:
                product_ids.append(product_result[0])
        # res = self.env['product.product'].browse(product_ids)
        if product_ids:
            self.env.cr.execute('''select id, default_code, owner_id from product_product where id in %s''', (tuple(product_ids),))
            res = self.env.cr.fetchall()
        else:
            res = []
        return res

    @api.multi
    def action_product_act_generate(self):
        return self.generate_product_act_new()

    @api.model
    def group_products_by_owner(self, products_with_owner):
        grouped_products = {}
        for product_tuple in products_with_owner:
            if product_tuple[2] not in grouped_products.keys():
                grouped_products[product_tuple[2]] = []
            grouped_products[product_tuple[2]].append((product_tuple[0], product_tuple[1]))
        return grouped_products

    @api.multi
    def generate_product_act_new(self, sale_ids=[]):
        # Sugeneruojami ruošiniai maršrutui. Generuojama pagal susijusius 
        # pardavimus(grupuojant pagal posidą) ir tik tuos pardavimus, kurie keliauja pas
        # klientus, o ne į kitą sandėlį. Ruošinys sukuriamas su ta tara, 
        # kuri yra priskirta prie maršruto ir kurios skola posido klientui yra didesnė už nulį 
        
        ctx = dict(self._context or {})
        ctx['force_finish_packing_line_create'] = True
        ctx['mail_create_nosubscribe'] = True
        ctx['mail_track_log_only'] = True
        ctx['mail_create_nolog'] = True
        ctx_pack = dict(ctx or {})
        ctx['tracking_disable'] = True
        ctx_fast = dict(self._context or {})
        ctx_fast['calculate_fast'] = True
        for route in self:
            posids = {}
            for packing in route.packing_for_client_ids:
                posids[(packing.address_id.id, packing.owner_id.id)] = packing.id
            if route.state != 'draft':
                raise UserError(_('Route has to be in draft state'))
            if route.type == 'internal':
                raise UserError(_('Route has to be \'Out\' or \'Mixed\' type'))
            for sale in route.sale_ids.filtered(
                lambda record: record.shipping_warehouse_id \
                    and record.shipping_warehouse_id.id == record.warehouse_id.id
            ):
                if isinstance(sale_ids, list) and sale_ids and sale.id not in sale_ids:
                    continue
                prodycts_with_owner = route.get_products_for_packing_new(sale.partner_id.id)
                prodycts_by_owner = route.group_products_by_owner(prodycts_with_owner)
                for owner_key in prodycts_by_owner.keys():
                    products = prodycts_by_owner[owner_key]
                    if (sale.partner_shipping_id.id, owner_key) not in posids.keys():
                        packing_vals = {}
                        packing_vals['partner_id'] = sale.partner_id.id
                        packing_vals['route_id'] = route.id
                        packing_vals['address_id'] = sale.partner_shipping_id.id
                        packing_vals['manual_packing'] = False
                        packing_vals['owner_id'] = owner_key
                        packing_vals['warehouse_id'] = sale.warehouse_id.id
                        packing = self.env['stock.packing'].with_context(ctx_pack).create(packing_vals)
                        packing_id = packing.id   
                        posids[(sale.partner_shipping_id.id, owner_key)] = packing_id
                        line_vals = {}
                        line_vals['return_to_driver_qty'] = 0.0
                        line_vals['give_to_customer_qty'] = 0.0
                        line_vals['packing_id'] = packing_id
                        line_vals['partner_id'] = packing_vals['partner_id']
                        line_vals['address_id'] = packing_vals['address_id']
                        line_vals['warehouse_id'] = packing_vals['warehouse_id']
    
                        for product in products:
                            line_vals['product_id'] = product[0]#.id
                            line_vals['product_code'] = product[1]#.default_code
                            line_vals['customer_qty'] = sale.partner_shipping_id.with_context(ctx_fast).get_debt(product[0])#.id)
    
                            line_vals['customer_posid_qty'] = line_vals['customer_qty']
                            line_vals['final_qty'] = sale.partner_id.with_context(ctx_fast).get_debt(product[0])#.id)
                            self.env['stock.packing.line'].with_context(ctx).create(line_vals)
                    else:
                        packing_id = posids[(sale.partner_shipping_id.id, owner_key)]
                    # sale.write({'packing_id': packing_id})
                    self.env.cr.execute('''update sale_order set packing_id=%s where id=%s''',(packing_id, sale.id))
            route.write({'packings_generated': True})
            route.calc_number_of_packing_for_client_lines()
            route.update_act_status()
        return True

    @api.multi
    def update_packings(self):
        line_env = self.env['stock.packing.line']
        ctx = dict(self._context or {})
        ctx['force_finish_packing_line_create'] = True
        ctx['mail_create_nosubscribe'] = True
        ctx['mail_track_log_only'] = True
        ctx['mail_create_nolog'] = True
        ctx['tracking_disable'] = True
        dicts_to_create = []
        for route in self:
            if route.packings_generated and route.type != 'internal':
                route.generate_product_act_new()

                packings = route.packing_for_client_ids
                for move in route.move_ids:
                    packings_to_update = packings.filtered(
                        lambda  pack_rec: move.product_id not in pack_rec.line_ids.mapped('product_id') \
                            and pack_rec.owner_id == move.product_id.owner_id
                    )                        
                    for packing_to_update in packings_to_update:
                        line_vals = {
                            'product_id': move.product_id.id,
                            'product_code': move.product_id.default_code,
                            'partner_id': packing_to_update.partner_id.id,
                            'address_id': packing_to_update.address_id.id,
                            'warehouse_id': packing_to_update.warehouse_id.id,
                            'packing_id': packing_to_update.id
                        }
                        dicts_to_create.append(line_vals)
                    
        for line_vals in dicts_to_create:
            line_env.with_context(ctx).create(line_vals)

    @api.model
    def OrderExternalPackets(self, list_of_route_packet_vals):
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        inter_obj = self.env['stock.route.integration.intermediate']
        log_obj = self.env['delivery.integration.log']

        create_datetime = time.strftime('%Y-%m-%d %H:%M:%S')

        ctx_en = context.copy()
        ctx_en['lang'] = 'en_US'
        error = self.with_context(ctx_en).check_imported_route_packet_values(list_of_route_packet_vals)
        if error:
            log_vals = {
                'create_date': create_datetime,
                'function': 'OrderExternalPackets',
                'received_information': str(json.dumps(list_of_route_packet_vals, indent=2)),
                'returned_information': str(json.dumps(error, indent=2))
            }

            log_obj.create(log_vals)
            return error

        itermediate = inter_obj.create({
            'datetime': create_datetime,
            'function': 'OrderExternalPackets',
            'received_values': str(json.dumps(list_of_route_packet_vals, indent=2)),
            'processed': False
        })
        if commit:
            self.env.cr.commit()
        itermediate.process_intermediate_objects_threaded()
        return itermediate.id

    @api.model
    def CreateRoute(self, list_of_route_vals):
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        inter_obj = self.env['stock.route.integration.intermediate']
        log_obj = self.env['delivery.integration.log']
        
        create_datetime = time.strftime('%Y-%m-%d %H:%M:%S')
        
        ctx_en = context.copy()
        ctx_en['lang'] = 'en_US'
        error = self.with_context(ctx_en).check_imported_route_values(list_of_route_vals)
        if error:
            log_vals = {
                'create_date': create_datetime,
                'function': 'CreateRoute',
                'received_information': str(json.dumps(list_of_route_vals, indent=2)),
                'returned_information': str(json.dumps(error, indent=2))
            }
            
            log_obj.create(log_vals)
            return error
        
        itermediate = inter_obj.create({
            'datetime': create_datetime,
            'function': 'CreateRoute',
            'received_values': str(json.dumps(list_of_route_vals, indent=2)),
            'processed': False
        })
        if commit:
            self.env.cr.commit()
        itermediate.process_intermediate_objects_threaded()
        return itermediate.id

    def check_imported_route_packet_values(self, list_of_route_packet_vals):
        result = {}
        return result
        
    @api.model
    def check_imported_route_values(self, list_of_route_vals):
        inter_obj = self.env['stock.route.integration.intermediate']
        result = {}
        required_values = [
            'orders', 'external_route_id', 'date', 
            'receiver', 'type', 'warehouse_id',
        ]
        inter_obj.check_import_values(list_of_route_vals, required_values, result)
        if result:
            return result
        selection_values = {
            'type': ['internal', 'out'],
        }
        required_order_values = []
        i = 0
        for route_dict in list_of_route_vals:
            i = i + 1
            index = str(i)
            line_results = {}
            inter_obj.check_import_values(
                route_dict.get('orders', []),
                required_order_values, line_results, prefix=_('Order')
            )
            if line_results:
                if index in result.keys():
                    result[index].append(line_results)
                else:
                    result[index] = [line_results]
            for selection_key in selection_values.keys():
                if selection_key in route_dict.keys():
                    selection_result = inter_obj.check_selection_values(
                        selection_key, route_dict[selection_key],
                        selection_values[selection_key]
                    )
                    if selection_result:
                        if index in result.keys():
                            result[index].append(selection_result)
                        else:
                            result[index] = [selection_result]
        return result

    @api.multi
    def confirm_and_print_all(self):

        if self.type == 'mixed':
            raise UserError(
                _('Mixed routing functionality is not used anymore. \
Choose an intermediate warehouse - your own, where you work, to deliver the goods directly to customers (distribution route), \
or specify another warehouse for which the cargo will be transported (interbranch route).'))
        return {
            'name': 'All Report',
            'res_model': 'stock.route.print_packing_report.osv',
            'view_type': 'form',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'context': {
                'report_to_print': 'config_sanitex_delivery.all_report',
                'active_ids': self.mapped('id'),
                'for_confirmation': True
            },
            'target': 'new'
        }

    @api.multi
    def print_all(self):
        return {
            'name': 'All Report',
            'res_model': 'stock.route.print_packing_report.osv',
            'view_type': 'form',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'context': {'report_to_print': 'config_sanitex_delivery.all_report', 'active_ids': self.mapped('id')},
            'target': 'new'
        }

    @api.multi
    def print_report(self, report_name, printer=None, reprint_reason=None, copies=None):
        report_env = self.env['ir.actions.report']
        report = report_env.search([('report_name','=',report_name)])
        if not report:
            raise UserError(_('Report %s does not exist') % report_name)
        for route in self:
            report.print_report(route, printer=printer, reprint_reason=reprint_reason, copies=copies)
    
    @api.model
    def check_route_vals(self, route_vals):
        if not route_vals.get('date', False):
            raise UserError(
                _('Route has to have \'%s\' filled') % _('Date')
            )
        if not route_vals.get('type', False):
            raise UserError(
                _('Route has to have \'%s\' filled') % _('Type')
            )
        if not route_vals.get('warehouse_id', False):
            raise UserError(
                _('Route has to have \'%s\' filled') % _('Warehouse')
            )
        if route_vals['type'] == 'internal' and not route_vals.get('destination_warehouse_id', False):
            raise UserError(
                _('Route has to have \'%s\' filled') % _('Type')
            )
        return True

    # @api.model
    # def route_create(self, vals):
    #     # Nebenaudojama
    #     interm_obj = self.env('stock.route.integration.intermediate')
    #     if context is None:
    #         context = {}
    #     commit = not context.get('no_commit', False)
    #     ids = self.search(cr, uid, [
    #         ('external_route_id','=',vals['external_route_id'])
    #     ], context=context)
    #
    #     route_vals = vals.copy()
    #     if ids:
    #         id = ids[0]
    #         route = self.browse(cr, uid, id, context=context)
    #         if 'sale_ids' in route_vals:
    #             sales_ids = [sale.id for sale in route.sale_ids]
    #             for sale_tuple in route_vals['sale_ids']:
    #                 if sale_tuple[1] in sales_ids and sale_tuple[0] == 4:
    #                     route_vals['sale_ids'].remove(sale_tuple)
    #         if route.state != 'draft':
    #             raise osv.except_osv(
    #                 _('Error'),
    #                 _('Route already exist and it is released')
    #             )
    #         interm_obj.remove_same_values(cr, uid, id, route_vals, 'stock.route', context=context)
    #         if route_vals:
    #             self.write(cr, uid, [id], route_vals, context=context)
    #             if 'updated_driver_ids' in context:
    #                 context['updated_route_ids'].append((vals['external_route_id'], id))
    #             context['route_message'] = _('Route was successfully updated')
    #     else:
    #         route_vals['intermediate_id'] = context.get('intermediate_id', False)
    #         self.check_route_vals(cr, uid, route_vals, context=context)
    #         id = self.create(cr, uid, route_vals, context=context)
    #         if 'created_driver_ids' in context:
    #             context['created_route_ids'].append((route_vals['external_route_id'], id))
    #         context['route_message'] = _('Route was successfully created')
    #     if commit:
    #         self.env.cr.commit()
    #     return id
#     
#     def do_include_partner(self, cr, uid, partner_id, route_id, context=None):
#         """Nebenaudojama"""
#         part_stock_obj = self.env('sanitex.product.partner.stock')
#         if self.do_partner_has_contract(cr, uid, partner_id, context=context):
#             return 1
#         product_ids = self.get_products_for_packing(cr, uid, route_id, context=context)
#         part_stock_ids = part_stock_obj.search(cr, uid, [
#             ('partner_id','=',partner_id),
#             ('product_id','in',product_ids)
#         ], context=context)
#         for part_stock_id in part_stock_ids:
#             part_stock = part_stock_obj.browse(cr, uid, part_stock_id, context=context)
#             if part_stock.qty_available:
#                 return -1
#         return 0

    @api.model
    def do_partner_has_contract(self, partner_id):
        usr_obj = self.env['res.users']
        part_obj = self.env['res.partner']
        comp = usr_obj.browse(self.env.uid).company_id
        if not comp.use_contract:
            return True
        partner = part_obj.browse(partner_id)
        if partner.product_contract_number:
            return True
        return False
    
    @api.multi
    def open_internal_routes(self):
        return {
            'name': _('Internal Routes'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.route',
            'type': 'ir.actions.act_window',
            'domain': [
                ('internal_route_for_route_id','in',[route.id for route in self]),
            ]
        }

    @api.multi
    def do_not_print_reports(self, reports=None):
        if reports is None:
            reports = [
                'config_sanitex_delivery.packing_return_act', # taros grąžinimo aktas iš vairuotojo
                'config_sanitex_delivery.drivers_packing_transfer_act', # taros perdavimo aktas vairuotojui
                'config_sanitex_delivery.product_packing', # draivas
            ]
        elif isinstance(reports, str):
            reports = [reports]

        report_env = self.env['ir.actions.report']

        for route in self:
            for report_name in reports:
                if report_name == 'config_sanitex_delivery.packing_return_act':
                    for picking in route.returned_picking_ids:
                        report_env.do_not_print_report(picking, report_name)
                elif report_name == 'config_sanitex_delivery.drivers_packing_transfer_act':
                    for picking in route.picking_ids:
                        report_env.do_not_print_report(picking, report_name)
                else:
                    report_env.do_not_print_report(route, report_name)


    @api.multi
    def create_invoice_and_picking(self):
        transportation_orders = self.env['transportation.order']
        for sale in self.sale_ids:
            if sale.state == 'need_invoice' and sale.transportation_order_id:
                transportation_orders += sale.transportation_order_id
        return transportation_orders.create_invoice_and_picking()
    
    @api.multi
    def close_route_if_needed(self):
        # Kai tarfilialiniame maršrute arba mišriame maršrute(kuriame nėra užsakymų
        # tiesiai pas klientus) naudotojai pažymi, kad visi konteineriai buvo gauti,
        # maršrutas turi automatiškai užsidaryti.
        # TODO: išsiaiškinti ar uždaryti maršrutą jeigu konteineris negautas niekeno

        for route in self:
            if route.state != 'released':
                continue
            if route.type == 'out':
                # vadinasi maršrutą uždaryti turi siuntėjas
                continue
            if 'none' in route.container_line_ids.mapped('state'):
                # vadinasi ne visi konteineriai gauti
                continue
            if route.sale_ids.filtered(
                lambda task_record: \
                    task_record.warehouse_id == task_record.shipping_warehouse_id and task_record.state != 'cancel'
            ):
                # vadinasi kaikurios užduotys yra tiesiai pas klientus)
                continue
            if 'not_received' in route.container_line_ids.mapped('state'):
                if route.container_line_ids.filtered(
                    lambda line_record: line_record.state=='not_received' \
                        and line_record.get_transportation_task().sequence == 0
                ):
                    continue
            route.action_close()
            
            
    @api.multi
    def remove_from_system(self):
        return self.with_context(allow_to_delete_not_draft_routes=True).sudo().unlink()
    
#     def can_delete_invoice(self, date_until=None):
#         if date_until is None:
#             user = self.env['res.users'].browse(self.env.uid)
#             company = user.company_id
#             days_after = company.delete_containers_after
#             today = datetime.datetime.now()
#             date_until = (today - datetime.timedelta(days=days_after)).strftime('%Y-%m-%d %H:%M:%S')        
#         if not (self.delivery_date and self.delivery_date < date_until or not self.delivery_date) and not self.delete_containers_after < date_until:
#             return False
#         return True
            
    
    @api.model
    def cron_delete_old_routes(self):
        # Krono paleidžiama funkcija, kuri trina senas sąskaitas faktūras        
        
        user = self.env['res.users'].browse(self.env.uid)
        company = user.company_id
        log = company.log_delete_progress or False
        days_after = company.delete_routes_after
        date_field = company.get_date_field_for_removing_object(self._name)
        
        _logger.info('Removing old Routes (%s days old) using date field \'%s\'' % (str(days_after), date_field))

        today = datetime.now()
        date_until = today - timedelta(days=days_after)

        routes = self.search([
            (date_field,'<',date_until.strftime('%Y-%m-%d %H:%M:%S')),
        ])
        _logger.info('Removing old Routes: found %s records' % str(len(routes)))
        if log:
            all_routes_count = float(len(routes))
            i = 0
            last_log = 0
        for route in routes:
            if not route.exists():
                continue
            try:
                route.remove_from_system()
                self.env.cr.commit()
                if log:
                    i += 1
                    if last_log < int((i / all_routes_count)*100):
                        last_log = int((i / all_routes_count)*100)
                        _logger.info('Routes delete progress: %s / %s' % (str(i), str(int(all_routes_count))))
            except Exception as e:
                err_note = 'Failed to delete route(ID: %s): %s \n\n' % (str(route.id), tools.ustr(e),)
                trb = traceback.format_exc() + '\n\n'
                _logger.info(err_note + trb)
                
    @api.model
    def show_hidden_close_buttons(self):
        routes = self.search([
            ('departure_time','<=',(datetime.now() - timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S')),
            ('hide_close_button','=',True),
            ('state','=',"released"),
        ])
        return routes.write({'hide_close_button': False})
    
    #Metodas kvieciamas is JS, patikrinimui, ar panaikinti PRINT mygtuka
    @api.model
    def show_print_button(self, ids, context):
        if len(ids) != 1:
            return False
        if not context:
            context = {}
        
        route = self.browse(ids[0])

        route_type = context.get('search_by_user_type', 'outgoing')
        if route_type == 'outgoing' and route.state == 'draft':
            return False
        elif route_type == 'incoming' and route.state_receive == 'planned':
            return False
        
        return True
    
    @api.multi
    def calc_number_of_packing_for_client_lines(self):
        for route in self:
            route.write({
                'number_of_packing_for_client_lines': len(route.packing_for_client_ids)
            })
        return True
    
    @api.model
    def get_number_of_arriving_routes(self):
        route_ids = self.with_context(
            {
                'get_incoming_routes': True,
                'search_by_user': True,
                'search_by_user_type': 'incoming',
                'search_by_user_sale': False,
            }
        ).search([])
        return len(route_ids)
    
    @api.model
    def get_pod_domain(self, obj):
        return [('state','in',['released','closed'])]
    
    @api.multi
    def to_dict_for_pod_integration(self, obj):
        fleet_env = self.env['stock.fleet']
        vals = {
            'routeId': str(self.id) or '',
            'estimatedDistance': self.route_length or 0,
            'estimatedStartTime': date_to_iso_format(self.departure_time) or '',
            'name': self.receiver or self.name or '',
            'carrierId': self.location_id and self.location_id.owner_id and self.location_id.owner_id.ref or \
                self.location_id.owner_id.id_carrier or \
                self.location_id.owner_id.external_customer_id or '',
            'estimatedFinishTime': "",
            'deleted': False,
            'status': self.state == 'released' and 'waiting' or 'finished',
            'driverId': self.location_id and (self.location_id.external_driver_id or str(self.location_id.id*10000)) or '',
            'truckFleetId': fleet_env.get_id_by_number(self.license_plate, 'truck'), #self.license_plate or '',
            'trailerFleetId': fleet_env.get_id_by_number(self.trailer, 'trailer'), #self.trailer or '',
            'id_version': self.id_version,
        }
        return vals
    
    @api.multi
    def set_version(self):
        for route in self:
            self._cr.execute('''
                UPDATE
                    stock_route
                SET
                    id_version = %s
                WHERE id = %s
            ''', (get_local_time_timestamp(), route.id))
        return True
    
class StockPicking(models.Model):
    _inherit = "stock.picking"
    _order = 'date desc'

    @api.model
    def _get_all_operation_types(self):
        return self.env['internal.operation']._get_all_operation_types()

    route_id = fields.Many2one('stock.route', 'Route')
    transfer_route_id = fields.Many2one('stock.route', 'Route')
    transfer_to_route_id = fields.Many2one('stock.route', 'Route')
    picking_to_warehouse_for_packing_id = fields.Many2one('stock.packing.correction', 'Correction', readonly=True)
    picking_to_driver_for_packing_id = fields.Many2one('stock.packing.correction', 'Correction', readonly=True)
    owner_id = fields.Many2one('product.owner', 'Owner', readonly=True)
    picking_part = fields.Integer('Part of a Document', readonly=True, default=1)
    
    return_from_driver_picking_for_route_id = fields.Many2one('stock.route', 'Route', readonly=True, 
        help='Curent picking is return from driver act generated from this route.', index=True
    )
    transfer_to_driver_picking_for_route_id = fields.Many2one('stock.route', 'Route', readonly=True,
        help='Curent picking is transfer to driver act generated from this route.', index=True
    )
    exported_as_tare_document = fields.Boolean('Exported as Tare Document', default=False)
    picking_to_warehouse_for_internal_order_id = fields.Many2one('internal.operation', 'Internal Operation', readonly=True)
    picking_from_warehouse_for_internal_order_id = fields.Many2one('internal.operation', 'Internal Operation', readonly=True)
    related_route_id = fields.Many2one('stock.route', 'Related Route', readonly=True, index=True)
    invoice_id = fields.Many2one('account.invoice', 'Document', readonly=True)
    # internal_movement = fields.Boolean('Internal Movement', readonly=True, default=False,
    #     help="Shows if picking created for internal movement between warehouses/statuses."
    # )
    # internal_adjustment = fields.Boolean('Internal Adjustment', readonly=True, default=False,
    #     help="Shows if picking created for internal product adjustment."
    # )
    operation_type = fields.Selection(_get_all_operation_types, 'Operation Type', readonly=True)
    received_by_user_id = fields.Many2one('res.users', 'Received By', readonly=True)
    receive_time = fields.Datetime('Receive Date, Time', readonly=True)
    # state = fields.Char('State')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute=False,
        copy=False, index=True, readonly=True, track_visibility='onchange', default='draft',
        help=" * Draft: not confirmed yet and will not be scheduled until confirmed.\n"
             " * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows).\n"
             " * Waiting: if it is not ready to be sent because the required products could not be reserved.\n"
             " * Ready: products are reserved and ready to be sent. If the shipping policy is 'As soon as possible' this happens as soon as anything is reserved.\n"
             " * Done: has been processed, can't be modified or cancelled anymore.\n"
             " * Cancelled: has been cancelled, can't be confirmed anymore.")

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id, picking_part)', 'Reference must be unique per company!'),
    ]

    @api.model
    def get_adjustment_location(self):
        location = self.env.ref('stock.location_inventory')
        if not location:
            raise UserError(_('Misiing inventory location'))
        return location

    @api.model
    def get_negative_adjustment_location(self):
        return self.get_adjustment_location()

    @api.model
    def get_positive_adjustment_location(self):
        return self.get_adjustment_location()

    @api.model
    def get_number_of_arriving_movements(self):
        picking_count = self.with_context(receiving_picking_search_by_warehouse=True).search([
            ('operation_type','=','atlas_movement'),
            ('received_by_user_id','=',False)
        ], count=True)
        return picking_count

    @api.model
    def get_user_domain(self, args=None):
        # funkcija kuri sukuria sale.order paieškos domeną
        # atsižvelgiant į conteksto reikšmę
        if args is None:
            args = []
        if self.env.uid == SUPERUSER_ID and False:
            return []

        context = self.env.context or {}
        domain = []
        if context.get('receiving_picking_search_by_warehouse', False):
            usr_env = self.env['res.users']
            user = usr_env.browse(self.env.uid)
            if user.default_warehouse_id or user.default_region_id:
                warehouses = user.get_current_warehouses()
                location_ids = self.env['stock.location'].search([
                    ('location_id', 'child_of', list(warehouses.mapped('lot_stock_id')._ids))
                ]).mapped('id')
                domain.append(('location_dest_id','in',location_ids))
        return domain

    @api.model
    def _search(
            self, args, offset=0, limit=None,
            order=None, count=False,
            access_rights_uid=None
    ):
        args += self.get_user_domain(args)
        return super(StockPicking, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )

    @api.multi
    def action_receive(self):
        # Metodas gauti movementus
        self.write({
            'received_by_user_id': self.env.uid,
            'receive_time': time.strftime('%Y-%m-%d %H:%M:%S')
        })

    @api.multi
    def get_receiver_for_report_log(self, report_name):
        # Metodas naudojamas papildyti spausdintų ataskaitų logui
        receiver = ''
        if report_name in ['config_sanitex_delivery.packing_return_act', 'config_sanitex_delivery.driver_return_act',
            'config_sanitex_delivery.tare_to_driver_act', 'config_sanitex_delivery.drivers_packing_transfer_act'
        ]:
            receiver = self.location_dest_id and self.location_dest_id.name or ''
        elif report_name in ['config_sanitex_delivery.client_packing_from_picking']:
            receiver = self.move_lines and self.move_lines[0].partner_name or ''
        return receiver

    @api.multi
    def get_vals_for_invoice(self):
        inv_env = self.env['account.invoice']
        vals = inv_env.default_get(inv_env._fields)
        vals_sql = '''
            SELECT
                p.name,
                p.date,
                r.name,
                COALESCE(r.warehouse_id, corr.return_to_warehouse_id, ino.warehouse_id),
                CASE 
                    WHEN m.move_type in ('wh2dr') THEN m.location_id
                    WHEN m.move_type in ('dr2cl', 'cl2dr') THEN r.source_location_id
                    WHEN m.move_type in ('dr2wh') THEN m.location_dest_id
                    WHEN m.move_type in ('wh2cl') THEN m.location_id
                    WHEN m.move_type in ('cl2wh') THEN m.location_dest_id
                    WHEN m.move_type in ('wh2wh') THEN m.location_id
                    WHEN m.move_type in ('wh2adj') THEN m.location_id
                    WHEN m.move_type in ('adj2wh') THEN m.location_dest_id
                END,
                m.address_id,
                part.parent_id,
                m.partner_code,
                m.partner_name,
                m.move_type,
                part.street,
                CASE 
                    WHEN m.move_type in ('wh2dr', 'cl2dr') THEN loc_dest.name
                    WHEN m.move_type in ('dr2cl', 'dr2wh') THEN loc_src.name
                END,
                part.possid_code,
                p.owner_id,
                CASE
                    WHEN 
                        m.move_type in ('wh2wh') 
                        AND p.operation_type in ('warehouse_movement', 'bls_movement', 'atlas_movement') 
                    THEN 
                        ino.location_to_id
                END,
                p.operation_type
            FROM
                stock_picking p
                LEFT JOIN stock_move m on (p.id = m.picking_id)
                LEFT JOIN internal_operation ino on (
                    ino.id = p.picking_to_warehouse_for_internal_order_id 
                    OR ino.id = p.picking_from_warehouse_for_internal_order_id)
                LEFT JOIN stock_packing_correction corr on (
                    corr.id = p.picking_to_warehouse_for_packing_id
                    OR corr.id = p.picking_to_driver_for_packing_id
                )
                LEFT JOIN res_partner part on (part.id = m.address_id)
                LEFT JOIN stock_packing pack on (pack.id = m.packing_id)
                LEFT JOIN stock_route r on (
                    r.id = p.related_route_id OR r.id = pack.route_id
                )
                LEFT JOIN stock_location loc_src on (loc_src.id = m.location_id)
                LEFT JOIN stock_location loc_dest on (loc_dest.id = m.location_dest_id)
            WHERE
                p.id = %s
            LIMIT 1
        '''
        vals_where = (self.id,)
        self.env.cr.execute(vals_sql, vals_where)
        vals_result = self.env.cr.fetchall()[0]
        vals.update({
            'name': vals_result[0],
            'date_invoice': utc_str_to_local_str(vals_result[1])[:10],
            'time_invoice': utc_str_to_local_str(vals_result[1])[11:16],
            'route_number': vals_result[2] or '',
            'picking_warehouse_id': vals_result[3] or False,
            'picking_location_id': vals_result[4] or False,
            'partner_ref': vals_result[7] or '',
            'partner_name': vals_result[8] or '',
            'partner_address': vals_result[10] or '',
            'driver_name': vals_result[11] or '',
            'external_invoice_id': 'FROM_PICKING_' + str(self.id),
            'partner_shipping_id': vals_result[5] or False,
            'partner_invoice_id': vals_result[6] or False,
            'partner_id': vals_result[6] or False,
            'posid': vals_result[12] or '',
            'document_operation_type': vals_result[9] or '',
            'all_document_numbers': vals_result[0],
            'owner_id': vals_result[13] or False,
            'destination_location_id': vals_result[14] or False,
            'operation_type': vals_result[15] or False
        })
        return vals
    
    @api.multi
    def update_invoice_reference(self, invoice_id):
        if not self:
            return
        update_sql = '''
            UPDATE
                stock_move
            SET
                invoice_id = %s
            WHERE
                picking_id in %s
        '''
        update_where = (invoice_id, self._ids)
        self.env.cr.execute(update_sql, update_where)
        update_sql = '''
            UPDATE
                stock_picking
            SET
                invoice_id = %s
            WHERE
                id in %s
        '''
        update_where = (invoice_id, self._ids)
        self.env.cr.execute(update_sql, update_where)


    @api.multi
    def create_invoice(self):
        # BLS'as nori visus važtaraščius matyti kaip dokumentus kartu su invoice'ais
        # todėl važtaraščiams sukuriami invoice'ai. Kolkas tik dėl duomenų atvaizdavimo

        inv_env = self.env['account.invoice']
        inv_line_env = self.env['account.invoice.line']
        for picking in self:
            if not picking.read(['invoice_id'])[0]['invoice_id']:
                invoice_vals = picking.get_vals_for_invoice()
                invoice = inv_env.with_context(
                    skip_full_name_update=True,
                    skip_invoice_create_readonly_update=True
                ).create(invoice_vals)
                picking.update_invoice_reference(invoice.id)
            else:
                invoice = inv_env.browse(picking.read(['invoice_id'])[0]['invoice_id'][0])
            for move in picking.move_lines:
                if not move.invoice_line_id:
                    invoice_line_vals = move.get_vals_for_invoice_line()
                    invoice_line_vals['invoice_id'] = invoice.id
                    invoice_line = inv_line_env.create(invoice_line_vals)
                    move.update_invoice_line_reference(invoice_line.id)
            invoice.update_line_count()
            invoice.update_amounts()

    @api.multi
    def get_product_sum(self, prod_type=False):
        total_sum = 0.0
        if self:
            for move in self.move_lines:
                if move.product_id:
                    if prod_type and move.product_id.type_of_product != prod_type:
                        continue
                    total_sum += move.product_id.standard_price*move.product_uom_qty
        return total_sum
    
    @api.multi
    def get_lines_for_packing_return_act(self):
        lines = []
        total = {
            'big_box': 0,
            'small_box': 0,
            'unit': 0,
            'total': 0,
            'brutto_weight': 0.0,
            'price': 0.0
        }
        if self:
            for move in self.move_lines:
                line = {}
                line['code'] = move.product_id and move.product_id.default_code or ''
                line['name'] = move.product_id and move.product_id.name or ''
                line['wo_vat'] = move.product_id and move.product_id.standard_price or 0.0
                line['w_vat'] = line['wo_vat'] + line['wo_vat'] * 0.21
                line['big_box'] = 0
                line['small_box'] = 0
                line['quantity'] = int(move.product_uom_qty)
                line['total_quantity'] = int(move.product_uom_qty)
                line['total_wo_vat'] = line['total_quantity'] * line['wo_vat']
                line['brutto'] = move.product_id and move.product_id.weight*move.product_uom_qty or 0.0
                lines.append(line)

                total['big_box'] += line['big_box']
                total['small_box'] += line['small_box']
                total['unit'] += line['quantity']
                total['total'] += line['total_quantity']
                total['brutto_weight'] += line['brutto']
                total['price'] += line['total_wo_vat']
        else:
            line = {}
            line['code'] = ''
            line['name'] = ''
            line['wo_vat'] = 0.0
            line['w_vat'] = 0.0
            line['big_box'] = 0.0
            line['small_box'] = 0.0
            line['quantity'] = 0.0
            line['total_quantity'] = 0.0
            line['total_wo_vat'] = 0.0
            line['brutto'] = 0.0
            lines.append(line)
        return lines, total

    @api.multi
    def send_tare_qty_info(self):
        context = self.env.context or {}
        put_in_queue = True
        if put_in_queue and not context.get('action_from_queue', False):
            for picking in self:
                self.env['action.queue'].create({
                    'function_to_perform': 'send_tare_qty_info',
                    'object_for_action': 'stock.picking',
                    'id_of_object': picking.id
                })
        else:
            pickings = self.search([
                ('name','=',self.name),
                ('state','=','done'),
                ('exported_as_tare_document','=',False)
            ], order='id')
            if len(pickings) > 1:
                pickings.with_context(combine_client_packing=True).mapped('move_lines').export_as_tare_documents()
            else:
                pickings and pickings.mapped('move_lines').export_as_tare_documents()
            pickings.write({'exported_as_tare_document': True})
            # self.move_lines.export_as_tare_documents()
        return True

    @api.model
    def get_picking_name(self, operation_type, warehouse=None, owner=None):
        # Metodas atitinka get_pick_name, tik perdarytas pagal naują numeracijos būdą

        doc_env = self.env['document.type']

        document_type = doc_env.get_document_type(operation_type)
        return doc_env.get_next_number_by_code(document_type,
            warehouse=warehouse, owner=owner
        )


    @api.model
    def get_pick_name(self, warehouse_id, picking_type=''):
        # Senas metodas, greit bus nebenaudojamas

        wh_obj = self.env['stock.warehouse']
        seq_obj = self.env['ir.sequence']
        warehouse = wh_obj.browse(warehouse_id)
        name = ''
        if picking_type == 'driver':
            name = warehouse.sequence_for_driver_picking_id.next_by_id()
        elif picking_type == 'client_packing':
            name = warehouse.sequence_for_client_packing_id.next_by_id()
        else:
            if warehouse.prefix_for_route:
                name = name + warehouse.prefix_for_route
            seq = seq_obj.search([
                ('code','=','stock_picking_name'),
            ], limit=1)
            if seq:
                name = name + seq.next_by_id()
        return name

    @api.multi
    def get_location_type(self, pick_type):
        type_obj = self.env['stock.picking.type']
        return type_obj.search([
            ('code','=',pick_type)
        ])

    @api.multi
    def action_confirm_bls(self):
        context = self.env.context or {}
        for picking in self:
            picking.move_lines.action_done_bls()
#         self.write({'state': 'done'})
        if self:
            self._cr.execute('''
                UPDATE stock_picking
                SET state = 'done'
                WHERE id in %s
            ''', (tuple(self.ids),))

        if context.get('create_invoice_document_for_picking', False):
            self.create_invoice()

    @api.multi
    def action_cancel_bls(self):
        return True

    @api.multi
    def get_total_weight(self):
        total_weight = 0.0
        for picking in self:
            for move in picking.move_lines:
                if not move.product_id:
                    continue
                total_weight += move.product_id.weight * move.product_uom_qty
        return total_weight

    @api.multi
    def action_return_to_draft_bls(self):
        move_obj = self.env['stock.move']
        move_cancel = self.env['stock.move']
        for pick in self:
            for move in pick.move_lines:
                if move.state != 'cancel':
                    move_cancel += move
                move_obj += move
            if move_cancel:
                move_cancel.action_cancel_bls()
            if move_obj:
                move_obj.action_return_bls()
        return True
    
    @api.multi
    def reconcile(self, move_type, route_id):
        if move_type == 'from_client':
            return False
        route_obj = self.env['stock.route']
        move_obj = self.env['stock.move']
        rec_obj = self.env['stock.move.reconcile']
        
        route = route_obj.browse(route_id)
        
        if move_type == 'to_client':
            route_moves = route.move_ids
            add_driver_route_move_ids = move_obj.search([
                ('open','=',True),
                ('location_dest_id','=',route.location_id.id),
                ('id','not in',route_moves.mapped('id'))
            ], order='date')
            route_moves += add_driver_route_move_ids
            
        for picking in self:
            if move_type == 'to_client':
                for move in picking.move_lines:
                    for route_move in route_moves:
                        if move.get_reconciled_from_qty() >= move.product_uom_qty:
                            continue
                        if route_move.product_id.id == move.product_id.id\
                            and route_move.price_unit == move.price_unit\
                            and route_move.get_reconciled_to_qty() < route_move.product_uom_qty\
                        :
                            rec_obj.reconcile(route_move.id, move.id)
                
            if move_type == 'to_warehouse':
                for move in picking.move_lines:
                    for route_move in route_moves:
                        if move.get_reconciled_from_qty() >= move.product_uom_qty:
                            continue
                        if route_move.product_id.id == move.product_id.id\
                            and route_move.price_unit == move.price_unit\
                            and route_move.get_reconciled_to_qty() < route_move.product_uom_qty\
                        :
                            rec_obj.reconcile(route_move.id, move.id)
        
        return True

    @api.multi
    def print_picking_from_route(self):
        # Galimybė iš važtaraščio atsispausdinti ataskaitas

        # print_route = self.env['stock.route.print_report.osv']
        # print_correction = self.env['stock.correction.print_report.osv']
        res = {
            'view_type': 'form',
            'view_mode': 'form',
            # 'res_model': 'stock.route.release.select_intermediate_warehouse.osv',
            'target': 'new',
            'type': 'ir.actions.act_window',
            # 'context': ctx,
            # 'res_id': osv.id,
            'nodestroy': True,
        }
        context = self.env.context or {}
        ctx = context.copy()
        if self.return_from_driver_picking_for_route_id:
            ctx['report_to_print'] = 'config_sanitex_delivery.packing_return_act'
            ctx['active_ids'] = [self.return_from_driver_picking_for_route_id.id]
            res['res_model'] = 'stock.route.print_report.osv'
        elif self.transfer_to_driver_picking_for_route_id:
            ctx['report_to_print'] = 'config_sanitex_delivery.drivers_packing_transfer_act'
            ctx['active_ids'] = [self.transfer_to_driver_picking_for_route_id.id]
            res['res_model'] = 'stock.route.print_report.osv'
        elif self.picking_to_warehouse_for_packing_id or self.picking_to_driver_for_packing_id:
            ctx['report_to_print'] = 'config_sanitex_delivery.report_stock_correction'
            ctx['active_ids'] = (self.picking_to_warehouse_for_packing_id | self.picking_to_driver_for_packing_id).mapped('id')
            res['res_model'] = 'stock.correction.print_report.osv'
        elif self.picking_to_warehouse_for_internal_order_id or self.picking_from_warehouse_for_internal_order_id:
            ctx['report_to_print'] = 'config_sanitex_delivery.client_packing_from_picking'
            internal_client_ids = (self.picking_to_warehouse_for_internal_order_id | self.picking_from_warehouse_for_internal_order_id).mapped('id')
            ctx['active_ids'] = self.env['internal.operation.client'].search([
                ('operation_id','in',internal_client_ids)
            ], limit=1)._ids
            ctx['active_model'] = 'internal.operation.client'
            res['res_model'] = 'print.report.from.object.osv'

        res['context'] = ctx
        return res


    @api.multi
    def _autoconfirm_picking(self):
        return


    @api.multi
    def get_logist_dict(self):
        return {
            'LogisticsText': '',
            'Creator': self.env['res.users'].browse(self.env.uid).name or '',
            'ProductsIssuedBy': '',
        }

    @api.model
    def create(self, vals):
        if 'state' not in vals:
            vals['state'] = 'draft'
        return super(StockPicking, self.with_context(mail_create_nosubscribe=True)).create(vals)

    @api.multi
    def get_client_dict(self):
        addresses = self.mapped('move_lines').mapped('address_id')
        if addresses:
            return addresses[0].get_client_dict_for_tare_report()
        return {
            'Name': '',
            'RegCode': '',
            'VatCode': '',
            'RegAddress': '',
            'InidividualActvNr': '',
            'FarmerCode': '',
            'POSAddress': '',
            'PosName': '',
            'InnerCode': '',
            'BSNLicNr': '',
            'Phone': '',
            'Fax': '',
            'POSAddress2': '',
            'EUText': '',
            'PosCode': '',
            'PersonName': '',
        }

    @api.multi
    def get_vat_line_dict(self):
        return {
            'VatTrf': str(0),
            'SumWoVat': str(0),
            'VatSum': str(0),
        }

    @api.multi
    def get_carrier_dict(self):
        if self.location_dest_id.driver:
            return self.location_dest_id.get_carrier_dict_from_driver()
        else:
            return self.env['stock.location'].get_empty_carrier_dict_from_driver()

    @api.multi
    def get_invoice_dict(self):
        return {
            'Warehouse': self.location_id and self.location_id.code or '',
            'InvoiceNo': self.name or 'T',
            'NKro': '',
            'ChangedInvNo': '',
            'UniqueId': str(self.id),
            'DocType': '',
            'SubType': '',
            'DocumentDate': self.date and self.date[:10] or '',
            'ShipDate': time.strftime('%Y-%m-%d'),
            'SumTotal': str(self.get_product_sum()),
            'SumDeposit': str(0),
            'SumTara': str(self.get_product_sum('package')),
            'Currency': 'EUR',
            'InvoiceCreateTime': utc_str_to_local_str(self.date),
            'PaymentDays': str(0),
            'OrderNo': '',
            'TextOnInv': self.note or '',
        }

    @api.multi
    def get_seller_dict(self):
        owner = self.move_lines and self.move_lines[0].product_id.owner_id or False
        owner_dict = owner and owner.get_owner_dict() or {}
        owner_dict['LoadAddress'] = self.location_id.load_address or ''
        return owner_dict

    @api.multi
    def get_seller_bank_acc_dict(self):
        return {
            'BankName': '',
            'BankAccount': ''
        }

    @api.multi
    def get_drivers_packing_transfer_act_xml(self, language='LT', tare_return=False):
        route_env = self.env['stock.route']
        data = {}

        invoice = self.get_invoice_dict()
        invoice['DocType'] = 'TareActDriver'#'ShipInvoice'
        invoice['SubType'] = 'TARETODRIVER'#'TareAct'

        seller = self.get_seller_dict()

        seller_bank_account = self.get_seller_bank_acc_dict()
        carrier = self.get_carrier_dict()
        client = self.get_client_dict()
        client['Name'] = self.location_dest_id and self.location_dest_id.name or ''

        logist = self.get_logist_dict()
        vat_line = self.get_vat_line_dict()
        coeff = 1
        if tare_return:
            client['Name'] = self.location_id and self.location_id.name or ''
            coeff=-1
        lines = []
        tare_credit_lines = []
        i = 0
        if self:
            for move in self.move_lines.sorted(key=lambda move_record: move_record.product_code):
                i += 1
                line = {
                    'Line_No': str(i),
                    'ProductCode': move.product_id and move.product_id.default_code or '',
                    'Inf_Prek': move.product_id and move.product_id.default_code or '',
                    'ProductId': move.product_id and str(move.product_id.id) or '',
                    'Barcode': '',
                    'CodeAtClient': '',
                    'ProductDescription': move.product_id and move.product_id.name or '',
                    'MeasUnit': move.product_id and move.product_id.uom_id and move.product_id.uom_id.name or '',
                    'Price': move.product_id and str(move.product_id.standard_price*coeff or 0),
                    'PriceVat': move.product_id and str(move.product_id.standard_price*coeff or 0),
                    'Discount': str(0),
                    'Kd': str(0),
                    'Km': str(0),
                    'Kv': str(0),
                    'Quantity': str(int(move.product_uom_qty or 0)*coeff),
                    'QuantityInUnits': str(int(move.product_uom_qty or 0)*coeff),
                    'SumWoVAT': str((move.product_uom_qty*coeff or 0) * (move.product_id.standard_price or 0)),
                    'LineDiscAmt': str(0),
                    'VatTrf': str(0),
                    'Netto': move.product_id and str((move.product_id.weight or 0) * (move.product_uom_qty*coeff or 0)),
                    'Brutto': move.product_id and str((move.product_id.weight or 0) * (move.product_uom_qty*coeff or 0)),
                    'Tobacco': str(0),
                    'Alco': str(0),
                    'ProductKiekd': str(int(move.product_uom_qty*coeff or 0)),
                    'Tara': 'U',
                }
                lines.append(line)
                tare_credit = {
                    'Inf_Prek': line['Inf_Prek'],
                    'ProductDescription': line['ProductDescription'],
                    'Price': line['Price'],
                    'TareCredit': move.product_id and str(
                        int(self.location_dest_id.get_drivers_debt(move.product_id.id))) or '0',
                }
                tare_credit_lines.append(tare_credit)
            tare_credit_lines = route_env.get_tare_credit_lines_for_tare_report(self.location_dest_id, self.owner_id)
        lines = sorted(lines, key=lambda k: k['ProductCode'])
        tare_credit_lines = sorted(tare_credit_lines, key=lambda k: k['Inf_Prek'])
        data['Invoice'] = invoice
        data['Seller'] = seller
        data['SellerBankAccount'] = seller_bank_account
        data['Client'] = client
        data['Logist'] = logist
        data['Carrier'] = carrier
        data['VatLine'] = vat_line
        data['Line'] = lines
        data['TareCredit'] = tare_credit_lines
        report = {
            'Data': data,
            '_attributes': [
                ('Type', 'REPWIN'),
                ('Language', language),
                ('Form', 'SHIPINVOICE')
            ]
        }
        return route_env.convert_dict_to_xml(report, 'PrintDoc')

    @api.multi
    def get_client_packing_act_xml(self, language='LT'):
        data = {}
        lines = []
        invoice = self.get_invoice_dict()
        invoice['DocType'] = 'TareActClient'#'TareAct'
        invoice['SubType'] = 'TARETOCLIENT'#'TareAct'


        seller = self.get_seller_dict()
        carrier = self.get_carrier_dict()
        bank_acc = self.get_seller_bank_acc_dict()
        client = self.get_client_dict()
        logist = self.get_logist_dict()
        vat_line = self.get_vat_line_dict()
        i = 0
        for move in self.move_lines.sorted(key=lambda move_rec: move_rec.product_code):
            i += 1
            line_d = move.get_move_dict_for_report()
            line_d['Line_No'] = str(i)
            lines.append(line_d)

        lines = sorted(lines, key=lambda k: k['ProductCode'])
        data['Invoice'] = invoice
        data['Seller'] = seller
        data['Carrier'] = carrier
        data['SellerBankAccount'] = bank_acc
        data['Client'] = client
        data['Logist'] = logist
        data['VatLine'] = vat_line
        data['Line'] = lines

        report = {
            'Data': data,
            '_attributes': [
                ('Type','REPWIN'),
                ('Language',language),
                ('Form','TAREACT')
            ]
        }
        return self.env['stock.route'].convert_dict_to_xml(report, 'PrintDoc')

    @api.multi
    def get_xml_for_report(self, report, language='LT'):
        if report == 'config_sanitex_delivery.tare_to_driver_act':
            return self.get_drivers_packing_transfer_act_xml(language=language)
        elif report == 'config_sanitex_delivery.client_packing_from_picking':
            return self.get_client_packing_act_xml(language=language)
        elif report == 'config_sanitex_delivery.driver_return_act':
            return self.get_drivers_packing_transfer_act_xml(language=language, tare_return=True)

    @api.multi
    def get_pdf_report(self, report, language='LT'):
        xml = self.get_xml_for_report(report, language=language)
        return self.env['printer'].get_report(xml, report)



class StockPacking(models.Model):
    _name = 'stock.packing'
    _description = 'Stock Packing'
    
    _inherit = ['mail.thread']

    @api.model
    def _get_number(self):
        seq_obj = self.env['ir.sequence']
        seq = seq_obj.search([
            ('code','=','stock_packing_number'),
        ], limit=1)
        if seq:
            return seq.next_by_id()
        return ''

    @api.model
    def _get_wh(self):
        context = self.env.context or {}
        if context.get('wh_for_packing', False):
            return context['wh_for_packing']
        return False

    @api.model
    def _get_partner(self):
        so_obj = self.env['sale.order']
        res = []
        context = self.env.context or {}
        if context.get('sale_ids_for_partner_search', False):
            for so_id in context['sale_ids_for_partner_search']:
                so = so_obj.browse(so_id[1])
                if so.partner_id.id not in res:
                    res.append(so.partner_id.id)
        return res

    @api.model
    def _get_address(self):
        so_obj = self.env['sale.order']
        res = []
        context = self.env.context or {}
        if context.get('sale_ids_for_partner_search', False):
            for so_id in context['sale_ids_for_partner_search']:
                so = so_obj.browse(so_id[1])
                if so.partner_id.id not in res:
                    res.append(so.partner_shipping_id.id)
        return res
    
    @api.model
    def get_route_states_selection(self):
        return self.env['stock.route'].get_route_states_selection()
        
    
    id = fields.Integer('ID', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Partner', required=True,
        states={'done':[('readonly',True)]}, 
        track_visibility='onchange'
    )
    address_id = fields.Many2one(
        'res.partner', 'Partner POSID Address', required=True,
        states={'done':[('readonly',True)]}, 
        track_visibility='onchange'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], 'State', readonly=True, track_visibility='onchange', default='draft')
    number = fields.Char('Number', readonly=True,
        track_visibility='onchange'
    )
    route_id = fields.Many2one('stock.route', 'Route',
        states={'done':[('readonly',True)]}, 
        track_visibility='onchange'
    )
    line_ids = fields.One2many(
        'stock.packing.line', 'packing_id', 'Lines',
        states={'done':[('readonly',True)]}, 
        track_visibility='onchange'
    )
    manual_packing = fields.Boolean('Manually Created Packing', readonly=True, 
        track_visibility='onchange'
    )
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', 
        track_visibility='onchange', default=_get_wh
    )
    move_ids = fields.One2many('stock.move', 'packing_id', 'Generated Moves',
        states={'done':[('readonly',True)]}, 
        track_visibility='onchange'
    )
    domain_partner_ids = fields.Many2many(
        'res.partner', 'res_partner_packing_rel', 
        'pack_id', 'part_id', 'Sales', 
        track_visibility='onchange', default=_get_partner
    )
    domain_address_ids = fields.Many2many(
        'res.partner', 'res_partner_addr_packing_rel', 
        'pack_id', 'part_id', 'Sales', 
        track_visibility='onchange', default=_get_address
    )
    printed = fields.Boolean('Printed', readonly=True, 
        track_visibility='onchange', default=False
    )
    partner_name = fields.Char('Partner Name', size=128, readonly=True)
    posid = fields.Char('POSID', size=128, readonly=True)
    complete_operation_exist = fields.Boolean('Completed Operations Exist', default=False, readonly=True)
    out_picking_id = fields.Many2one('stock.picking', 'Out Picking', readonly=True, track_visibility='onchange')
    in_picking_id = fields.Many2one('stock.picking', 'In Picking', readonly=True, track_visibility='onchange')
    owner_id = fields.Many2one('product.owner', 'Owner', readonly=True)
    route_state = fields.Selection(get_route_states_selection, "Route State", readonly=True)

    @api.multi
    def get_receiver_for_report_log(self, report_name):
        # Metodas naudojamas papildyti spausdintų ataskaitų logui
        receiver = ''
        if report_name == 'config_sanitex_delivery.stock_packing_report':
            receiver = self.partner_name or self.partner_id.name or ''
        return receiver

    @api.multi
    def do_not_print_reports(self, reports=None):
        if reports is None:
            reports = [
                'config_sanitex_delivery.stock_packing_report', # Taros perdavimo-grąžinimo aktas klientui
            ]
        elif isinstance(reports, str):
            reports = [reports]

        report_env = self.env['ir.actions.report']

        for packing in self:
            for report_name in reports:
                report_env.do_not_print_report(packing, report_name)

    @api.multi
    def _export_rows(self, fields):
        if self.env.user.company_id.user_faster_export:
            res = self.env['ir.model'].export_rows_with_psql(fields, self)
        else:
            res = super(StockPacking, self)._export_rows(fields)
        return res
    
    @api.multi
    def copy(self, default=None):
        raise UserError(_('You cannot duplicate a packing.'))

    @api.multi
    def name_get(self):
        if not self:
            return []
        res = []
        for packing in self.read([
            'number', 'partner_id',
        ]):
            name = ''
            if packing.get('number', False):
                name = packing['number']
            if packing.get('partner_id', False):
                try:
                    name += packing['partner_id'] and packing['partner_id'][1] and (' ' + packing['partner_id'][1])
                except:
                    pass
            name = '[' + name.strip() + ']'
            res.append((packing['id'], name))
                
        return res

    @api.multi
    def print_packing(self):
        for packing in self:
            if packing.number:
                continue
            if self.env.user.company_id.do_use_new_numbering_method():
                packing.write({
                    'number': self.env['stock.picking'].get_picking_name(
                        'route_transfer_to_client', warehouse=packing.route_id.warehouse_id, owner=packing.owner_id
                    ),
                    'printed': True
                })

            else:
                packing.write({
                    'number': packing.route_id.warehouse_id.sequence_for_client_packing_id.next_by_id(),
                    'printed': True
                })
        return True

    @api.multi
    def assign_packing_to_order(self):
        for packing in self:
            if packing.route_id and packing.address_id:
                for order in packing.route_id.sale_ids:
                    if order.partner_shipping_id.id == packing.address_id.id:
                        order.sudo().write({
                            'packing_id': packing.id
                        })
        return True
    
#     def create(self, cr, uid, vals, context=None):
#         if 'manual_packing' not in vals:
#             vals['manual_packing'] = True
#         id = super(stock_packing, self).create(
#             cr, uid, vals, context=context
#         )
#         
#         return id
    
    
    @api.model
    def update_vals(self, vals):
        if 'partner_id' in vals.keys():
            if vals['partner_id']:
                vals['partner_name'] = self.env['res.partner'].browse(vals['partner_id']).name or ''
            else:
                vals['partner_name'] = ''
        if 'address_id' in vals.keys():
            if vals['address_id']:
                vals['posid'] = self.env['res.partner'].browse(vals['address_id']).possid_code or ''
            else:
                vals['posid'] = ''
    
    @api.model
    def create(self, vals):
        self.update_vals(vals)
        if 'manual_packing' not in vals:
            vals['manual_packing'] = True
        return super(StockPacking, self).create(vals)

    @api.multi
    def write(self, vals):
        line_obj = self.env['stock.packing.line']
        self.update_vals(vals)
        res = super(StockPacking, self).write(vals)
        if 'address_id' in vals or 'partner_id' in vals or 'warehouse_id' in vals:
            lines = line_obj.search([
                ('packing_id','in',self.mapped('id'))
            ])
            if lines:
                line_vals = {}
                if 'address_id' in vals:
                    line_vals['address_id'] = vals['address_id']
                if 'partner_id' in vals:
                    line_vals['partner_id'] = vals['partner_id']
                if 'warehouse_id' in vals:
                    line_vals['warehouse_id'] = vals['warehouse_id']
                lines.write(line_vals)
            
        if 'address_id' in vals:
            self.assign_packing_to_order()
        return res
    
    @api.multi
    def create_stock_picking(self, route, stock_type):
        pick_obj = self.env['stock.picking']
        type_obj = self.env['stock.picking.type']
        loc_env = self.env['stock.location']
        
        pick_vals = {}
        pick_vals.update(pick_obj.default_get(pick_obj._fields))
        pick_vals['owner_id'] = self.owner_id.id
        if stock_type == 'incoming':
            pick_vals['name'] = self.number or str(self.id) or route.name# + '/' + route.warehouse_id.sequence_for_client_packing_id.prefix + '/IN'
            pick_vals['location_id'] = route.get_client_location()
            pick_vals['location_dest_id'] = route.get_driver()
        elif stock_type == 'outgoing':
            pick_vals['name'] = self.number or str(self.id) or route.name# + '/' + route.warehouse_id.sequence_for_client_packing_id.prefix + '/OUT'
            pick_vals['location_id'] = route.get_driver()
            pick_vals['location_dest_id'] = route.get_client_location()
        pick_vals['picking_part'] = len(self.in_picking_id + self.out_picking_id) + 1
        warehouse = loc_env.browse(pick_vals['location_id']).get_location_warehouse_id()
        if not warehouse:
            warehouse = loc_env.browse(pick_vals['location_dest_id']).get_location_warehouse_id()
        if warehouse:
            type_record = type_obj.search([
                ('code','=',stock_type),
                ('warehouse_id','=',warehouse.id)
            ], limit=1)
        else:
            type_record = type_obj.search([
                ('code','=',stock_type)
            ], limit=1)
            
        pick_vals['picking_type_id'] = type_record.id
        picking = pick_obj.create(pick_vals)
        return picking.id

    @api.model
    def get_move_vals(self, line_id):
        vals = {
            'tare_movement': True
        }
        
        line = self.env['stock.packing.line'].browse(line_id)
        route = line.packing_id.route_id
        
        if line.return_to_driver_qty > line.give_to_customer_qty:
            return_qty = line.return_to_driver_qty - line.give_to_customer_qty
            
            product_qty_dict = line.packing_id.address_id.get_quantities_by_price(line.product_id.id, qty=return_qty)
            if len(product_qty_dict.keys()) > 1:
                vals['split_by'] = product_qty_dict
            # vals['product_qty'] = line.return_to_driver_qty
            vals['product_uom_qty'] = return_qty
            vals['product_uos_qty'] = return_qty
            vals['picking_id'] = line.packing_id.in_picking_id and line.packing_id.in_picking_id.id \
                or line.packing_id.create_stock_picking(route, 'incoming')
            vals['location_id'] = route.get_client_location()
            vals['location_dest_id'] = route.get_driver()
            if not line.packing_id.in_picking_id:
                line.packing_id.write({
                    'in_picking_id': vals['picking_id'],
                })
        elif line.return_to_driver_qty < line.give_to_customer_qty:
            given_qty = line.give_to_customer_qty - line.return_to_driver_qty
            # vals['product_qty'] = line.give_to_customer_qty
            vals['product_uom_qty'] = given_qty
            vals['product_uos_qty'] = given_qty
            vals['picking_id'] = line.packing_id.out_picking_id and line.packing_id.out_picking_id.id \
                or line.packing_id.create_stock_picking(route, 'outgoing')
            vals['location_id'] = route.get_driver()
            vals['location_dest_id'] = route.get_client_location()
            if not line.packing_id.out_picking_id:
                line.packing_id.write({
                    'out_picking_id': vals['picking_id'],
                })
        return vals 
    
#     def update_existing_picking(self, cr, uid, line_id, context=None):
#         move_obj = self.env('stock.picking')
#         line = self.env('stock.packing.line').browse(
#             cr, uid, line_id, context=context
#         )
#         route = line.packing_id.route_id
#         if line.return_to_driver_qty:
#             if route.out_picking_id:
#                 move_obj.search(cr, uid, )
#         else:
#             a
#         return 

    @api.multi
    def create_picking(self):
        move_obj = self.env['stock.move']
        
        for line in self.line_ids:
            if line.return_to_driver_qty or line.give_to_customer_qty:
                if line.return_to_driver_qty == line.give_to_customer_qty:
                    continue
                move_vals = {}
                move_vals['product_id'] = line.product_id.id
                update_vals = self.get_move_vals(line.id)
                temp_move = move_obj.new(move_vals)
                temp_move.onchange_product_id()
                move_vals.update(temp_move._convert_to_write(temp_move._cache))
                move_vals.update(update_vals)

#                 move_vals['route_id'] = route.id
                move_vals['packing_id'] = self.id
                move_vals['address_id'] = self.address_id.id
                move_vals['price_unit'] = line.product_id.get_price()
                if 'split_by' in move_vals.keys():
                    for price in move_vals['split_by'].keys():
                        move_vals_after_split = move_vals.copy()
                        del move_vals_after_split['split_by']
                        move_vals_after_split['price_unit'] = price
                        # move_vals_after_split['product_qty'] = move_vals['split_by'][price]
                        move_vals_after_split['product_uom_qty'] = move_vals['split_by'][price]
                        move_vals_after_split['product_uos_qty'] = move_vals['split_by'][price]
                        move_obj.create(move_vals_after_split)
                else:
                    move_obj.create(move_vals)
                
        return True

    @api.multi
    def action_done(self):
        route_obj = self.env['stock.route']
        # pick_obj = self.env['stock.picking']
        self.write({'state': 'done'})
        packings_by_route = {}
        for packing in self:
            route_id = packing.route_id and packing.route_id.id or False
            if route_id not in packings_by_route.keys():
                packings_by_route[route_id] = []
            if packing.id not in packings_by_route[route_id]:
                packings_by_route[route_id].append(packing.id)
        
        for route_id in packings_by_route.keys():
            i = 0
            # pack_count = len(packings_by_route[route_id])
            for id in packings_by_route[route_id]:
                i += 1
                packing = self.browse(id)
                # route_id = packing.route_id and packing.route_id.id or False
                if packing.route_id.state != 'released':
                    raise UserError(
                        _('Route(%s, ID: %s) of this packing(%s, ID: %s) has to be released') % (
                            packing.route_id.name, str(packing.route_id.id), packing.number, str(packing.id),
                        )
                    )
                if not route_obj.do_partner_has_contract(packing.partner_id.id):
                    for line in packing.line_ids:
                        if line.give_to_customer_qty > 0.0:
                            raise UserError(
                                _('Packing(%s, ID: %s): Partner %s has not have contract signed, so you can\'t give him %s product') % (
                                    packing.number, str(packing.id), packing.partner_id.name, line.product_id.name
                                )
                            )
                # if i == 1:
                #     if packing.route_id and packing.route_id.in_picking_id \
                #         and packing.route_id.in_picking_id.state == 'done' \
                #     :
                #         route_obj.cancel_picking(packing.route_id.in_picking_id.id)
                #     if packing.route_id and packing.route_id.out_picking_id \
                #         and packing.route_id.out_picking_id.state == 'done' \
                #     :
                #         route_obj.cancel_picking(packing.route_id.out_picking_id.id)
    #             cr.commit()
                packing.create_picking()
                packing.in_picking_id and route_obj.with_context(create_invoice_document_for_picking=True).confirm_picking(packing.in_picking_id.id)
                packing.out_picking_id and route_obj.with_context(create_invoice_document_for_picking=True).confirm_picking(packing.out_picking_id.id)
                packing.out_picking_id \
                    and packing.out_picking_id.reconcile('to_client', packing.route_id.id)
                packing.out_picking_id and packing.out_picking_id.send_tare_qty_info()
                packing.in_picking_id and packing.in_picking_id.send_tare_qty_info()
                packing.route_id.update_act_status()
                # if i == pack_count:
                #     if packing.route_id and packing.route_id.out_picking_id \
                #         and packing.route_id.out_picking_id.state == 'draft' \
                #     :
                #         route_obj.confirm_picking(packing.route_id.out_picking_id.id)
                #         packing.route_id.out_picking_id.reconcile('to_client', packing.route_id.id)
                #     if packing.route_id and packing.route_id.in_picking_id \
                #         and packing.route_id.in_picking_id.state == 'draft' \
                #     :
                #         route_obj.confirm_picking(packing.route_id.in_picking_id.id)
#nebereikia iš kliento sugretinti
#
#                         pick_obj.reconcile(
#                             cr, uid, [packing.route_id.in_picking_id.id], 'from_client',
#                             packing.route_id.id, context=context
#                         )
        return True

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self.env.context or {}
        
        if context.get('report_for_packings', False):
            if context['report_for_packings'] == 'config_sanitex_delivery.all_report' and False:
                args.append(('printed','=',False))
        return super(StockPacking, self).search(
            args, offset=offset, limit=limit,
            order=order, count=count
        )

    @api.multi
    def unlink(self):
        context = self.env.context or {}
        if not context.get('allow_unlink_packing', False):
            for pack in self:
                if pack.route_id.state != 'draft' or pack.printed:
                    raise UserError(_('You can\'t delete packing(%s, ID: %s), because it is related to released route(%s, ID: %s) or already printed') % (
                        pack.number, str(pack.id), pack.route_id.name_get() \
                            and pack.route_id.name_get()[0] \
                            and pack.route_id.name_get()[0][1] \
                            or pack.route_id.name, str(pack.route_id.id)
                    ))
        
        elif not context.get('allow_unlink_done_packing', False):
            for pack in self:
                if pack.state != 'draft':
                    raise UserError(_('You can\'t delete done packings(%s, ID: %s)') % (pack.number, str(pack.id)))
        
        routes = self.env['stock.route']
        for pack in self:
            if pack.route_id:
                routes += pack.route_id
        res = super(StockPacking, self).unlink()
        routes.calc_number_of_packing_for_client_lines()
        routes.update_act_status()
        return res

    @api.multi
    def action_cancel(self):
        route_obj = self.env['stock.route']
        move_obj = self.env['stock.move']
        
        self.write({'state': 'draft'})
        for packing in self:
            if packing.route_id.state != 'released':
                raise UserError(
                    _('Route(%s, ID: %s) of this packing(%s, ID: %s) has to be released') % (
                        packing.route_id.name, str(packing.route_id.id), packing.number, str(packing.id)
                    )
                )
            if packing.route_id.returned_picking_id:
                raise UserError(
                    _('You can\'t cancel packing(%s, ID: %s) because related route(%s, ID: %s) has drivers return picking') % (
                        packing.number, str(packing.id), packing.route_id.name, str(packing.route_id.id) 
                    )
                )
            if packing.route_id:
                if packing.route_id and packing.route_id.in_picking_id \
                    and packing.route_id.in_picking_id.state == 'done' \
                :
                    route_obj.cancel_picking(packing.route_id.in_picking_id.id)
                    moves = move_obj.search([
                        ('picking_id','=',packing.route_id.in_picking_id.id),
                        ('packing_id','=',packing.id)
                    ])
                    moves.unlink()
                    if move_obj.search([
                        ('picking_id','=',packing.route_id.in_picking_id.id),
                    ]):
                        route_obj.with_context(create_invoice_document_for_picking=True).confirm_picking(packing.route_id.in_picking_id.id)
                    else:
                        packing.route_id.in_picking_id.unlink()
                if packing.route_id and packing.route_id.out_picking_id \
                    and packing.route_id.out_picking_id.state == 'done' \
                :
                    route_obj.cancel_picking(packing.route_id.out_picking_id.id)
                    moves = move_obj.search([
                        ('picking_id','=',packing.route_id.out_picking_id.id),
                        ('packing_id','=',packing.id)
                    ])
                    moves.unlink()
                    if move_obj.search([
                        ('picking_id','=',packing.route_id.out_picking_id.id),
                    ]):
                        route_obj.with_context(create_invoice_document_for_picking=True).confirm_picking(packing.route_id.out_picking_id.id)
                    else:
                        packing.route_id.out_picking_id.unlink()
        return True
    
    @api.multi
    def get_client_dict(self):
        client = self.route_id.get_client_dict()
        client['Name'] = self.partner_id and self.partner_id.name or ''
        client['RegCode'] = self.partner_id and self.partner_id.ref or ''
        client['VatCode'] = self.partner_id and self.partner_id.vat or ''
        client['RegAddress'] = self.partner_id and self.partner_id.street or ''
        client['POSAddress'] = self.address_id and self.address_id.street or ''
        client['InnerCode'] = self.address_id and self.address_id.possid_code or ''
        sales = self.route_id.sale_ids.filtered(lambda sale_record: sale_record.partner_shipping_id == self.address_id)
        if sales:
            route_order = sales[0].order_number_by_route
            if route_order:
                try:
                    client['RouteOrder'] = int(route_order)
                except:
                    pass
        return client

    @api.multi
    def get_seller_dict(self):
        owner_dict = self.owner_id and self.owner_id.get_owner_dict() or {}
        owner_dict['LoadAddress'] = self.route_id and self.route_id.source_location_id.load_address or ''
        return owner_dict

    @api.multi
    def get_tare_xml(self, language='LT'):
        context = self.env.context or {}
        data = {}
        lines = []
        invoice = self.route_id.get_invoice_dict()
        invoice['DocType'] = 'TareActClient'#'TareAct'
        invoice['SubType'] = 'TARETOCLIENT'#'TareAct'
        invoice['InvoiceNo'] = self.number or ''
        invoice['InvoiceNoInPick'] = context.get('packing_no_in_route', [0,0])[0]
        invoice['TotalInvoicesInPick'] = context.get('packing_no_in_route', [0,0])[1]

        
        seller = self.get_seller_dict()
        carrier = self.route_id.get_carrier_dict()
        bank_acc = self.route_id.get_seller_bank_acc_dict()
        client = self.get_client_dict()
        logist = self.route_id.get_logist_dict()
        vat_line = self.route_id.get_vat_line_dict()
        i = 0
        for line in self.line_ids.sorted(key=lambda line_rec: line_rec.product_code):
            i += 1
            line_d = line.get_report_dict()
            line_d['Line_No'] = str(i)
            lines.append(line_d)

        lines = sorted(lines, key=lambda k: k['ProductCode'])
        data['Invoice'] = invoice
        data['Seller'] = seller
        data['Carrier'] = carrier
        data['SellerBankAccount'] = bank_acc
        data['Client'] = client
        data['Logist'] = logist
        data['VatLine'] = vat_line
        data['Line'] = lines

        report = {
            'Data': data,
            '_attributes': [
                ('Type','REPWIN'),
                ('Language',language),
                ('Form','TAREACT')
            ]
        }
        return self.env['stock.route'].convert_dict_to_xml(report, 'PrintDoc')
    
    @api.multi
    def get_xml_for_report(self, report, language='LT'):
        if report == 'config_sanitex_delivery.stock_packing_report':
            self.print_packing()
            return self.get_tare_xml(language=language)
    
    @api.multi
    def get_pdf_report(self, report, language='LT'):
        xml = self.get_xml_for_report(report, language=language)
        return self.env['printer'].get_report(xml, report)


    @api.multi
    def print_report(self, report_name, printer=None, reprint_reason=None, copies=None, route=None):
        report_env = self.env['ir.actions.report']
        report = report_env.search([('report_name','=',report_name)], limit=1)
        if not report:
            raise UserError(_('Report %s does not exist') % report_name)
        pack_no = 0
        for packing in self:
            pack_no += 1
            report.print_report(
                packing.with_context(packing_no_in_route=(pack_no, len(self))), printer=printer, reprint_reason=reprint_reason, copies=copies
            )
        if not self and route:
            report.print_report(route, printer=printer, reprint_reason=reprint_reason, copies=copies)
            
    @api.multi
    def check_completed_operation_exist(self):
        packing_line_env = self.env['stock.packing.line']
        for packing in self:
            packing_lines = packing_line_env.search([
                ('packing_id','=',packing.id),
                '|',
                ('return_to_driver_qty','!=',0),
                ('give_to_customer_qty','!=',0),
            ], limit=1)
            if packing_lines:
                packing.write({'complete_operation_exist': True})
            else:
                packing.write({'complete_operation_exist': False})
            
        return True
    
    @api.onchange('line_ids')
    def onchange_lines(self):
        complete_operation_exist = False
        for line in self.line_ids:
            if line.return_to_driver_qty or line.give_to_customer_qty:
                complete_operation_exist = True
                break
        self.complete_operation_exist = complete_operation_exist
        
    @api.multi
    def recalc_route_state(self):
        if self:
            self.env.cr.execute('''
                UPDATE
                    stock_packing sp
                SET
                    route_state = sr.state
                FROM
                    stock_route sr
                WHERE
                    sp.route_id = sr.id
                    AND sp.id in %s
            ''', (tuple(self.ids),))
        # for packing in self:
        #     route = packing.route_id
        #     if route:
        #         packing.write({
        #             'route_state': route.read(['state'])[0]['state']
        #         })
        return True

class StockPackingLine(models.Model):
    _name = 'stock.packing.line'
    _description = 'Stock Picking Line'
    
    _inherit = ['mail.thread']
    
    _order = 'product_code, packing_id desc'

    partner_id = fields.Many2one('res.partner', 'Partner', readonly=True,
        track_visibility='onchange'
    )
    address_id = fields.Many2one(
        'res.partner', 'Delivery Address', readonly=True,
        track_visibility='onchange'
    )
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse',
        track_visibility='onchange'
    )
    packing_id = fields.Many2one('stock.packing', 'Packing',
        track_visibility='onchange', required=True, ondelete='cascade'
    )
    product_id = fields.Many2one('product.product', 'Product',
        track_visibility='onchange', required=True
    )
    return_to_driver_qty = fields.Integer('Return Quantity',
        track_visibility='onchange'
    )
    give_to_customer_qty = fields.Integer(
        'Give to Customer Quantity',
        track_visibility='onchange'
    )
    customer_posid_qty = fields.Integer('Left to Customer POSID',
        track_visibility='onchange', readonly=True
    )
    product_code = fields.Char('Product Code', readonly=True,
        track_visibility='onchange'
    )
    customer_qty = fields.Integer('Left to Customer', readonly=True,
        track_visibility='onchange'
    )
    difference_qty = fields.Integer('Difference', readonly=True, help='Quantity given to customer - quantity taken from customer')
    final_qty = fields.Integer('Final Quantity', readonly=True,
        track_visibility='onchange'
    )
    product_filled = fields.Boolean('Product Filled', readonly=True,
        track_visibility='onchange'
    )
    
    @api.multi
    def get_report_dict(self):
        return {
            'Line_No': 1,
            'ProductCode': self.product_id and self.product_id.default_code or '',
            'Inf_Prek': self.product_id and self.product_id.default_code or '',
            'ProductId': self.product_id and self.product_id.id and str(self.product_id.id) or '',
            'Barcode': '',
            'CodeAtClient': '',
            'ProductDescription': self.product_id and self.product_id.name or '',
            'MeasUnit': self.product_id and self.product_id.uom_id and self.product_id.uom_id.name or '',
            'Price': self.product_id and str(self.product_id.standard_price or 0),
            'PriceVat': self.product_id and str(self.product_id.standard_price or 0),
            'Discount': str(0),
            'Kd': str(0),
            'Km': str(0),
            'Kv': str(0),
            'Quantity': str(int(self.give_to_customer_qty or 0)),
            'PosTareCredit': str(int(self.customer_posid_qty or 0)),
            'OrgTareCredit': str(int(self.final_qty or 0)),
            'QuantityInUnits': str(int(self.give_to_customer_qty or 0)),
            'SumWoVAT': str(0),
            'LineDiscAmt': str(0),
            'VatTrf': str(0),
            'Netto': str(0),
            'Brutto': str(0),
            'Tobacco': str(0),
            'Alco': str(0),
            'ProductKiekd': str(int(self.give_to_customer_qty or 0)),
            'Tara': 'U',
        }
    
    @api.model 
    def create(self, vals):
        context = self.env.context or {}
        if vals.get('product_id', False):
            vals['product_filled'] = True
        line = super(StockPackingLine, self).create(vals)
        if context.get('force_finish_packing_line_create', False):
            return line
        if line.packing_id.state == 'done':
            raise UserError(
                _('You can\'t edit packing line(ID: %s) because packing(%s, ID: %s) is done') %(
                    str(line.id), line.packing_id.number, str(line.packing_id.id)
                )
            )
        new_vals = {
            'partner_id': line.packing_id.partner_id.id,
            'address_id': line.packing_id.address_id.id,
            'warehouse_id': line.packing_id.warehouse_id 
                and line.packing_id.warehouse_id.id or False
        }
        line.write(new_vals)
        if line.product_id:
            if line.packing_id.address_id:
                debt = line.packing_id.address_id.get_debt(line.product_id.id)
                value = {
                    'customer_posid_qty': debt,
                    'customer_qty': debt \
                        + vals.get('give_to_customer_qty', 0.0) \
                        - vals.get('return_to_driver_qty', 0.0)
                }
                line.write(value)
        line.packing_id.check_completed_operation_exist()
        return line

    @api.multi
    def write(self, vals):
        packings = self.env['stock.packing']
        if 'return_to_driver_qty' in vals or 'give_to_customer_qty' in vals:
            for line in self:
                packings |= line.packing_id
                if line.packing_id.state == 'done':
                    raise UserError(
                        _('You can\'t edit packing line(ID: %s) because packing(%s, ID: %s) is done') %(
                            str(line.id), line.packing_id.number, str(line.packing_id.id)
                        )
                    )
                new_vals = {}
                new_vals['customer_qty'] = line.customer_posid_qty \
                    + vals.get('give_to_customer_qty', 0.0) \
                    - vals.get('return_to_driver_qty', 0.0)
                new_vals['difference_qty'] = vals.get('give_to_customer_qty', 0.0) \
                    - vals.get('return_to_driver_qty', 0.0)
                line.write(new_vals)
        res = super(StockPackingLine, self).write(vals)
        if packings:
            packings.check_completed_operation_exist()
                
        return res

#     @api.onchange('return_to_driver_qty')
#     def on_change_return_qty(self):
#         if self.customer_posid_qty:
#             posid_qty = self.customer_posid_qty
#         else:
#             posid_qty = 0.0
# 
#         self.customer_qty = posid_qty - self.return_to_driver_qty
#         if self.return_to_driver_qty > 0.0:
#             self.give_to_customer_qty = 0.0
#             self.customer_qty = posid_qty - self.return_to_driver_qty
#         else:
#             self.customer_qty = posid_qty - self.return_to_driver_qty + self.give_to_customer_qty
# 
#     @api.onchange('give_to_customer_qty')
#     def on_change_give_qty(self):
#         self.customer_qty = 0.0
# 
#         if self.customer_posid_qty:
#             posid_qty = self.customer_posid_qty
#         else:
#             posid_qty = 0.0
# 
#         if self.give_to_customer_qty > 0.0:
#             self.return_to_driver_qty = 0.0
#             self.customer_qty = posid_qty + self.give_to_customer_qty
#         else:
#             self.customer_qty = posid_qty + self.give_to_customer_qty - self.return_to_driver_qty

    @api.onchange('return_to_driver_qty','give_to_customer_qty')
    def on_change_qty(self):
        if self.customer_posid_qty:
            posid_qty = self.customer_posid_qty
        else:
            posid_qty = 0.0
 
        self.customer_qty = posid_qty - self.return_to_driver_qty + self.give_to_customer_qty
        self.difference_qty = 0 - self.return_to_driver_qty + self.give_to_customer_qty


    @api.onchange('product_id')
    def on_change_product_id(self):
        if self.product_id:
            self.product_code = self.product_id.get_product_code()
            if self.address_id:
                address_debt = self.address_id.get_debt(self.product_id.id)
                self.customer_posid_qty = address_debt
            if self.partner_id:
                partner_debt = self.partner_id.get_debt(self.product_id.id)
                self.final_qty = partner_debt
#         self.on_change_return_qty()
#         self.on_change_give_qty()
        self.on_change_qty()
            

    @api.multi
    def unlink(self):
        packings = self.env['stock.packing']
        for line in self:
            packings |= line.packing_id
            if line.packing_id.state == 'done' or line.packing_id.printed:
                raise UserError(
                    _('You cant delete line(%s, ID: %s) of client packing(%s, ID: %s). Because client packing is done or already printed') % (
                    line.product_id.name, str(line.id), line.packing_id.number, str(line.packing_id.id)
                ))
        res = super(StockPackingLine, self).unlink()
        if packings:
            packings.check_completed_operation_exist()
        return res
    
class StockMove(models.Model):
    _inherit = "stock.move"

    route_id = fields.Many2one('stock.route', 'Route')
    packing_id = fields.Many2one('stock.packing', 'Packing', readonly=True)
    address_id = fields.Many2one('res.partner', 'POSSID')
    product_qty = fields.Float(
        'Quantity', digits=dp.get_precision('Product Unit of Measure'), required=False
    )
    product_uom_qty = fields.Float(
        'Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True
    )
    # temp_product_uom_qty = fields.Float(
    #     'Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True
    # )
    product_uos_qty = fields.Float(
        'Quantity', digits=dp.get_precision('Product Unit of Measure'), required=False
    )
    product_code = fields.Char('Product Code', readonly=True)
    reconcile_to_ids = fields.One2many(
        'stock.move.reconcile', 'move_from_id', 'Reconcile To',
        readonly=True
    )
    reconcile_from_ids = fields.One2many(
        'stock.move.reconcile', 'move_to_id', 'Reconcile From',
        states={'done':[('readonly',True)]},
    )
    open = fields.Boolean('Open', readonly=True, default=False)
    left_qty = fields.Integer('Qty left', readonly=True, default=0)
    driver_code = fields.Char(
        "Driver ID", size=128, readonly=True
    )
    driver_company_code = fields.Char(
        "Drivers Comp. Code", size=128, readonly=True
    )
    driver_company_name = fields.Char(
        "Drivers Company", size=256, readonly=True
    )
    partner_name = fields.Char('Client Name', size=256, readonly=True)
    partner_code = fields.Char('Client Code', size=128, readonly=True)
    move_type = fields.Selection([
        ('wh2dr','Warehouse --> Driver'),
        ('dr2cl','Driver --> Client'),
        ('cl2dr','Client --> Driver'),
        ('dr2wh','Driver --> Warehouse'),
        ('dr2dr','Driver --> Driver'),
        ('wh2wh','Warehouse --> Warehouse'),
        ('cl2cl','Client --> Client'),
        ('wh2cl','Warehouse --> Client'),
        ('cl2wh','Client --> Warehouse'),
        ('adj2wh','Adjustment --> Warehouse'),
        ('wh2adj','Warehouse --> Adjustment'),
    ], 'Type of Move', readonly=True)
    owner_code_of_product_code = fields.Char('Owner code', size=128)
    intermediate_for_tare_export_id = fields.Many2one(
        'stock.route.integration.intermediate', 'Intermediate', readonly=True
    )
    tare_document_exported = fields.Boolean('Exported', default=False)
    product_name = fields.Char('Product Name', size=128, readonly=True)
    source_location_name = fields.Char('Source Location Name', size=128, readonly=True)
    destination_location_name = fields.Char('Destiantion Location Name', size=128, readonly=True)
    create_user_name = fields.Char('User Name', size=128, readonly=True)
    user_warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)
    user_warehouse_name = fields.Char('Warehouse Name', size=64, readonly=True)
    return_for_route_id = fields.Many2one('stock.route', 'Route', readonly=True, index=True, help='This move is return from driver created in this route.')
    related_route_id = fields.Many2one('stock.route', 'Related Route', readonly=True, index=True)
    invoice_id = fields.Many2one('account.invoice', readonly=True, index=True)
    invoice_line_id = fields.Many2one('account.invoice.line', readonly=True, index=True)
    tare_movement = fields.Boolean('Tare Movement', readonly=True, help='Shows if this is tare move', default=False)

    @api.multi
    def get_vals_for_invoice_line(self):
        vals = {
            'product_id': self.product_id and self.product_id.id or False,
            'quantity': self.product_uom_qty or 0.0,
            'discount': 0.0,
            'price_unit': self.price_unit or 0.0,
            'uom_id': self.product_uom and self.product_uom.id,
            'name': self.product_id and self.product_id.name or '',

        }
        return vals

    @api.model_cr
    def init(self):
        cr = self.env.cr
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_move_intermediate_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX stock_move_intermediate_id_index ON stock_move (intermediate_for_tare_export_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_move_sale_line_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX stock_move_sale_line_id_index ON stock_move (sale_line_id)')

    @api.multi
    def _export_rows(self, fields):
        if self.env.user.company_id.user_faster_export:
            res = self.env['ir.model'].export_rows_with_psql(fields, self)
        else:
            res = super(StockMove, self)._export_rows(fields)
        return res

    @api.multi
    def get_move_dict_for_report(self):
        vals = self.product_id.get_product_dict_for_report()
        vals.update({
            'Line_No': 1,
            'Price': self.price_unit and str(self.price_unit or 0),
            'PriceVat': self.price_unit and str(self.price_unit or 0),
            'Discount': str(0),
            'Kd': str(0),
            'Km': str(0),
            'Kv': str(0),
            'Quantity': str(int(self.product_uom_qty or 0)),
            'PosTareCredit': str(int(0)),
            'OrgTareCredit': str(int(0)),
            'QuantityInUnits': str(int(self.product_uom_qty or 0)),
            'SumWoVAT': str((self.price_unit or 0)*(self.product_uom_qty or 0)),
            'LineDiscAmt': str(0),
            'VatTrf': str(0),
            'Netto': self.product_id and str((self.product_id.weight_neto or 0)*(self.product_uom_qty or 0)),
            'Brutto': self.product_id and str((self.product_id.weight or 0)*(self.product_uom_qty or 0)),
            'ProductKiekd': str(int(self.product_uom_qty or 0)),
            'Tara': 'U',
        })
        if self.address_id and self.product_id:
            vals.update({
                'PosTareCredit': str(int(self.address_id.get_debt(self.product_id.id) or 0)),
                'OrgTareCredit': str(int(self.address_id.parent_id.get_debt(self.product_id.id) or 0)),
            })
        return vals

    @api.constrains('reconcile_from_ids')
    def _check_reconcile_from(self):
        context = self.env.context or {}
        if context.get('ignore_reconcile_to_from_check', False):
            return True
        # if not context.get('lang', False):
        #     usr_obj = self.env['res.users']
        #     usr = usr_obj.browse(self.env.uid)
        #     context['lang'] = usr.lang

        if self.reconcile_from_ids:
            qty = 0
            for line in self.reconcile_from_ids:
                qty += line.quantity
                if line.move_from_id.location_dest_id.id != self.location_id.id:
                    raise ValidationError(
                        _('Every move in reconciliation line has to have the same destination location as move\'s source location (%s). Wrong location: %s') % (
                            self.location_id.name, line.move_from_id.location_dest_id.name
                        ))
            if qty > self.product_uom_qty:
                raise ValidationError(
                    _('''The sum quantity of lines from field 'Reconcile From' has to be equal to quantity of stock move.(ID: %s) ''') % str(self.id)
                )

    @api.constrains('reconcile_to_ids')
    def _check_reconcile_to(self):
        context = self.env.context or {}
        if context.get('ignore_reconcile_to_from_check', False):
            return True
        # if not context.get('lang', False):
        #     usr_obj = self.env['res.users']
        #     usr = usr_obj.browse(self.env.uid)
        #     context['lang'] = usr.lang

        if self.reconcile_to_ids:
            qty = 0
            for line in self.reconcile_to_ids:
                qty += line.quantity
                if line.move_to_id.location_id.id != self.location_dest_id.id:
                    raise ValidationError(
                        _('Every move in reconciliation line has to have the same source location as move\'s destination location (%s). Wrong location: %s') % (
                            self.location_dest_id.name, line.move_to_id.location_id.name
                        ))
            if qty > self.product_uom_qty:
                raise ValidationError(
                    _('''The sum quantity of lines from field 'Reconcile To' has to be equal to quantity of stock move.(ID: %s) ''') % str(self.id)
                )
    
    _order = 'date desc'
    
    @api.multi
    def group_by_owner(self):
        # Sugrupuoja perkėlimus pagal sąvininką, kuris yra nurodytas prie produkto.
        # Geupavimas yra reikalingas siunčiant taros perkėlimo važtaraštį, nes BLS'ui
        # reikia, kad tame pačiame dokumente nebūtų dviejų skirtingų savininkų produktų.
        
        res = {}
        owners = self.mapped('product_id').mapped('owner_id')
        used_owners = self.browse()
        for owner in owners:
            res[owner.owner_code] = self.filtered(lambda move_record: 
                move_record.product_id.owner_id and move_record.product_id.owner_id.id == owner.id
            )
            used_owners += res[owner.owner_code]
        if self-used_owners:
            res[False] = self-used_owners
        return res

    @api.model
    def get_sumed_qty_with_sql(self, location_id, product_id):
        sum_qty = 0.0
        sum_sql = '''
            SELECT
                SUM(
                    CASE
                        WHEN location_id = %s THEN -product_uom_qty
                        WHEN location_dest_id = %s THEN product_uom_qty
                    END
                ) 
            FROM
                stock_move
            WHERE
                product_id = %s
                AND (location_id=%s 
                    OR location_dest_id = %s)
                AND state='done' 
        '''
        sum_where = (location_id, location_id, product_id, location_id, location_id)
        # print(sum_sql % sum_where)
        self.env.cr.execute(sum_sql, sum_where)
        result = self.env.cr.fetchall()
        if result:
            sum_qty = result[0][0]
        return sum_qty

    
    @api.multi
    def export_as_tare_documents(self):
        company = self.env['res.users'].browse(self.env.uid).company_id
        context = self.env.context or {}
        commit = not context.get('no_commit', False)
        if not company.export_tare_document or context.get('do_not_export_tare_info', False):
            return True
        owner_grouped_moves = self.group_by_owner()
        intermediates = []
        for owner_code in owner_grouped_moves.keys():
            try:
                moves = owner_grouped_moves[owner_code]
                for tare_dict in moves.to_dict_for_export():
                    moves = []
                    for line in tare_dict['lines']:
                        moves.append(line['move_id'])
                    if tare_dict['lines'] and tare_dict['lines'][0]['intermediate_id']:
                        intermediate = self.env['stock.route.integration.intermediate'].browse(tare_dict['lines'][0]['intermediate_id'])
                    else:
                        intermediate = self.env['stock.route.integration.intermediate'].create({
                            'datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'processed': False,
                            'function': 'TareDocumentExport',
                        })
                    self.browse(moves).write({'intermediate_for_tare_export_id': intermediate.id})
                    if commit:
                        self.env.cr.commit()
                    intermediates.append(intermediate.id)
            
            except UserError as e:
                err_note = _('Failed to export tare documents: %s') % (tools.ustr(e),)
                trb = traceback.format_exc()
                _logger.info(err_note + '\n')
                _logger.info(trb.encode('utf-8').decode('unicode-escape') + '\n')
                self.env.cr.rollback()
            except Exception as e:
                err_note = _('Failed to export tare documents: %s') % (tools.ustr(e),)
                trb = traceback.format_exc()
                _logger.info(err_note + '\n')
                _logger.info(trb.encode('utf-8').decode('unicode-escape') + '\n')
                self.env.cr.rollback()
            self.env['stock.route.integration.intermediate'].browse(intermediates).process_intermediate_objects()
        return True
    
    
    @api.multi
    def to_dict_for_export(self, id=False, source=''):
        loc_env = self.env['stock.location']
        part_env = self.env['res.partner']

        context = self.env.context or {}

        def format_date(str_date):
            date_date = datetime.strptime(str_date, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc).astimezone(timezone('Europe/Vilnius'))
            return date_date.isoformat()
        
        id_sufix = ''
        if id:
            id_sufix += '_'+id
        res = []
        res_dict = {}
        for move in self:
            if move.state != 'done':
                continue
            if move.move_type not in ['wh2dr', 'dr2wh', 'cl2dr', 'dr2cl', 'wh2cl', 'cl2wh']:
                continue
            if move.tare_document_exported:
                continue
            sender = {}
            receiver = {}
            if move.move_type not in res_dict.keys():
                if move.move_type == 'cl2dr' and context.get('combine_client_packing', False):
                    if 'dr2cl' not in res_dict.keys():
                        res_dict['dr2cl'] = {}
                else:
                    res_dict[move.move_type] = {}

            if move.move_type == 'cl2dr' and context.get('combine_client_packing', False):
                if DRIVER_WAREHOUSE not in res_dict['dr2cl'].keys():
                    res_dict['dr2cl'][DRIVER_WAREHOUSE] = {}

                if move.address_id.id not in res_dict['dr2cl'][DRIVER_WAREHOUSE].keys():
                    res_dict['dr2cl'][DRIVER_WAREHOUSE][move.address_id.id] = {}
                dict_to_send = res_dict['dr2cl'][DRIVER_WAREHOUSE][move.address_id.id]

            elif move.move_type == 'wh2dr':
                if move.location_id.id not in res_dict[move.move_type].keys():
                    res_dict[move.move_type][move.location_id.id] = {}
                
                if move.location_dest_id.id not in res_dict[move.move_type][move.location_id.id].keys():
                    res_dict[move.move_type][move.location_id.id][move.location_dest_id.id] = {}
                dict_to_send = res_dict[move.move_type][move.location_id.id][move.location_dest_id.id]
                    
            elif move.move_type == 'dr2cl':
                if DRIVER_WAREHOUSE not in res_dict[move.move_type].keys():
                    res_dict[move.move_type][DRIVER_WAREHOUSE] = {}
                
                if move.address_id.id not in res_dict[move.move_type][DRIVER_WAREHOUSE].keys():
                    res_dict[move.move_type][DRIVER_WAREHOUSE][move.address_id.id] = {}
                dict_to_send = res_dict[move.move_type][DRIVER_WAREHOUSE][move.address_id.id]
            elif move.move_type == 'cl2dr':
                if move.address_id.id not in res_dict[move.move_type].keys():
                    res_dict[move.move_type][move.address_id.id] = {}
                
                if DRIVER_WAREHOUSE not in res_dict[move.move_type][move.address_id.id].keys():
                    res_dict[move.move_type][move.address_id.id][DRIVER_WAREHOUSE] = {}
                dict_to_send = res_dict[move.move_type][move.address_id.id][DRIVER_WAREHOUSE]
            elif move.move_type == 'dr2wh':
                if move.location_id.id not in res_dict[move.move_type].keys():
                    res_dict[move.move_type][move.location_id.id] = {}
                
                if move.location_dest_id.id not in res_dict[move.move_type][move.location_id.id].keys():
                    res_dict[move.move_type][move.location_id.id][move.location_dest_id.id] = {}
                dict_to_send = res_dict[move.move_type][move.location_id.id][move.location_dest_id.id]
            ## --------------------------------------------------------------------------------
            elif move.move_type == 'cl2wh':
                if move.address_id.id not in res_dict[move.move_type].keys():
                    res_dict[move.move_type][move.address_id.id] = {}

                if move.location_dest_id.id not in res_dict[move.move_type][move.address_id.id].keys():
                    res_dict[move.move_type][move.address_id.id][move.location_dest_id.id] = {}
                dict_to_send = res_dict[move.move_type][move.address_id.id][move.location_dest_id.id]
            elif move.move_type == 'wh2cl':
                if move.location_id.id not in res_dict[move.move_type].keys():
                    res_dict[move.move_type][move.location_id.id] = {}

                if move.address_id.id not in res_dict[move.move_type][move.location_id.id].keys():
                    res_dict[move.move_type][move.location_id.id][move.address_id.id] = {}
                dict_to_send = res_dict[move.move_type][move.location_id.id][move.address_id.id]
            ## --------------------------------------------------------------------------------
            
            if move.picking_id.name not in dict_to_send.keys():
                dict_to_send[move.picking_id.name] = {
                    'source': source,
                    'documentid': str(move.picking_id.id) + '_' + str(move.id)+id_sufix,
                    'created': move.picking_id.date and format_date(move.picking_id.date) or '',
                    'lines': [],
                    'documentnumber': move.picking_id.name or '',
                    'author': self.env['res.users'].browse(self.env.uid).get_author_dict(),
                    'sellerCompany': move.product_id and move.product_id.owner_id \
                        and move.product_id.owner_id.get_owner_dict_for_tare_export(owner_type='seller') or {},#kolkas pardavėjas visada toks pat kaip savininkas. Nežinau kada skirsis.

                }
            pick = dict_to_send[move.picking_id.name]
            
            m = {
                'productid': str(move.product_id.default_code or ''),
                'name': move.product_id.name or '',
                'quantity': move.product_uom_qty and int(move.product_uom_qty) or 0,
                'price': move.product_id.standard_price or 0,
                'barcode': '',
                'ownerCompany': move.product_id and move.product_id.owner_id \
                    and move.product_id.owner_id.get_owner_dict_for_tare_export() or {},
            }
            if context.get('combine_client_packing', False) and move.move_type == 'cl2dr':
                m['quantity'] = -1*m['quantity']
            if not id:
                m['move_id'] = move.id
                m['intermediate_id'] = move.intermediate_for_tare_export_id and move.intermediate_for_tare_export_id.id or False
            pick['lines'].append(m)

        for key in res_dict.keys():
            if key == 'wh2dr':
                for wh_id in res_dict[key].keys():
                    sender = {}
                    sender['sendertype'] = 'warehouse'
                    sender['warehousesender'] = loc_env.browse(wh_id).get_warehouse_dict()
                    for loc_id in res_dict[key][wh_id].keys():
                        receiver = {}
                        receiver['receivertype'] = 'driver'
                        receiver['driverreceiver'] = loc_env.browse(loc_id).get_driver_dict()
                        for pick_id in res_dict[key][wh_id][loc_id].keys():
                            final_dict = res_dict[key][wh_id][loc_id][pick_id]
                            final_dict.update(sender)
                            final_dict.update(receiver)
                            res.append(final_dict)
                            
            elif key == 'dr2cl':
                for loc_id in res_dict[key].keys():
                    sender = {}
                    sender['sendertype'] = 'warehouse'
                    sender['warehousesender'] = loc_env.browse(loc_id).get_driver_wh_dict()
                    for part_id in res_dict[key][loc_id].keys():
                        receiver = {}
                        receiver['receivertype'] = 'client'
                        receiver['clientreceiver'] = part_env.browse(part_id).get_client_dict()
                        for pick_id in res_dict[key][loc_id][part_id].keys():
                            final_dict = res_dict[key][loc_id][part_id][pick_id]
                            final_dict.update(sender)
                            final_dict.update(receiver)
                            res.append(final_dict)
                            
            elif key == 'cl2dr':
                for part_id in res_dict[key].keys():
                    sender = {}
                    sender['sendertype'] = 'client'
                    sender['clientsender'] = part_env.browse(part_id).get_client_dict()
                    for loc_id in res_dict[key][part_id].keys():
                        receiver = {}
                        receiver['receivertype'] = 'warehouse'
                        receiver['warehousereceiver'] = loc_env.browse(loc_id).get_driver_wh_dict()
                        for pick_id in res_dict[key][part_id][loc_id].keys():
                            final_dict = res_dict[key][part_id][loc_id][pick_id]
                            final_dict.update(sender)
                            final_dict.update(receiver)
                            res.append(final_dict)
                        
            elif key == 'dr2wh':
                for loc_id in res_dict[key].keys():
                    sender = {}
                    sender['sendertype'] = 'driver'
                    sender['driversender'] = loc_env.browse(loc_id).get_driver_dict()
                    for wh_id in res_dict[key][loc_id].keys():
                        receiver = {}
                        receiver['receivertype'] = 'warehouse'
                        receiver['warehousereceiver'] = loc_env.browse(wh_id).get_warehouse_dict()
                        for pick_id in res_dict[key][loc_id][wh_id].keys():
                            final_dict = res_dict[key][loc_id][wh_id][pick_id]
                            final_dict.update(sender)
                            final_dict.update(receiver)
                            res.append(final_dict)
            ## ---------------------------------------------------------------------------------------------

            elif key == 'cl2wh':
                for part_id in res_dict[key].keys():
                    sender = {}
                    sender['sendertype'] = 'client'
                    sender['clientsender'] = part_env.browse(part_id).get_client_dict()
                    for wh_id in res_dict[key][part_id].keys():
                        receiver = {}
                        receiver['receivertype'] = 'warehouse'
                        receiver['warehousereceiver'] = loc_env.browse(wh_id).get_warehouse_dict()
                        for pick_id in res_dict[key][part_id][wh_id].keys():
                            final_dict = res_dict[key][part_id][wh_id][pick_id]
                            final_dict.update(sender)
                            final_dict.update(receiver)
                            res.append(final_dict)

            elif key == 'wh2cl':
                for wh_id in res_dict[key].keys():
                    sender = {}
                    sender['sendertype'] = 'warehouse'
                    sender['warehousesender'] = loc_env.browse(wh_id).get_warehouse_dict()
                    for part_id in res_dict[key][wh_id].keys():
                        receiver = {}
                        receiver['receivertype'] = 'client'
                        receiver['clientreceiver'] = part_env.browse(part_id).get_client_dict()
                        for pick_id in res_dict[key][wh_id][part_id].keys():
                            final_dict = res_dict[key][wh_id][part_id][pick_id]
                            final_dict.update(sender)
                            final_dict.update(receiver)
                            res.append(final_dict)
            ## ---------------------------------------------------------------------------------------------
        return res

    @api.multi
    def make_name(self):
        pick_name = ''
        date = ''
        transfer = ''
        product = ''
        
        if self.picking_id and self.picking_id.name:
            pick_name = self.picking_id.name
            
        if self.picking_id and self.picking_id.date:
            date = self.picking_id.date
            
        if self.location_id and self.location_id.name:
            transfer = self.location_id.name + ' > '
            
        if self.location_dest_id and self.location_dest_id.name:
            transfer += self.location_dest_id.name
        
        if self.product_id:
            if self.product_id.default_code:
                product = self.product_id.default_code
            elif self.product_id.name:
                product = self.product_id.name
        
        price = str(self.price_unit)
        
        name = '[' + pick_name + ', ' + date + '] - ' + product + ' (' + price + ')' + ': ' + transfer
        return name

    @api.multi
    def get_total_sum(self):
        total_sum = 0.0
        if not self:
            return total_sum
        sum_sql = '''
            SELECT
                SUM(product_uom_qty*price_unit)
            FROM
                stock_move
            WHERE
                id in %s
        '''
        sum_where = (self._ids,)
        self.env.cr.execute(sum_sql, sum_where)
        sum_result = self.env.cr.fetchall()
        if sum_result:
            total_sum = sum_result[0][0]
        return total_sum

    @api.multi
    def name_get(self):
        res = []
        for move in self:
            name = move.make_name()
            res.append((move.id, name))
        return res
    
    @api.model
    def get_moves_to_reconcile_from(self, move_to_id, move_from_ids=None, reconcile_qty=None):
        if move_from_ids is None:
            move_from_ids = []
        route_obj = self.env['stock.route']
        res = []
        
        move_to = self.browse(move_to_id)
        
        if reconcile_qty is None:
            reconcile_qty = move_to.product_uom_qty - move_to.get_reconciled_from_qty()
        reconciled_qty = 0
        if not move_from_ids:
            domain = [
                ('state','=','done'),
                ('location_dest_id','=',move_to.location_id.id),
                ('product_id','=',move_to.product_id.id),
                ('open','=',True),
                ('date','<',move_to.date),
            ]
            if move_to.address_id and move_to.location_id.id == route_obj.get_client_location():
                if move_to.address_id.parent_id:
                    part_id = move_to.address_id.parent_id.id
                else:
                    part_id = move_to.address_id.id
                domain.append('|')
                domain.append(('address_id','=',part_id))
                domain.append(('address_id.parent_id','=',part_id))
            moves_from = self.search(domain, order='date')
        else:
            moves_from = self.browse(move_from_ids)
        
        for move_from in moves_from:
            
            if move_to.product_uom_qty <= move_to.get_reconciled_from_qty():
                break
            if reconciled_qty >= reconcile_qty:
                break
            
            if move_from.product_id.id == move_to.product_id.id\
                and move_to.get_reconciled_to_qty() < move_to.product_uom_qty\
            :
                qty = min([
                    move_to.product_uom_qty - move_to.get_reconciled_from_qty(), 
                    move_from.product_uom_qty - move_from.get_reconciled_to_qty(),
                    reconcile_qty - reconciled_qty
                ])
                if qty > 0:
                    res.append((move_from.id, qty))
                    reconciled_qty += qty
                
        return res

    @api.model
    def manual_reconciliation(self):
        for move in self:
            self.reconciliate_moves(move.id)

    @api.model
    def reconciliate_moves(self, move_to_id, move_from_ids=[], reconcile_qty=None):
        rec_obj = self.env['stock.move.reconcile']
        records = self.env['stock.move.reconcile']
        for rec_move in self.get_moves_to_reconcile_from(move_to_id, move_from_ids, reconcile_qty):
            records += rec_obj.create({
                'move_from_id': rec_move[0],
                'move_to_id': move_to_id,
                'quantity': rec_move[1]
            })
        return records
    
    @api.multi
    def calculate_reconcilations(self, calculate_previous=True):
        for move in self:
            if calculate_previous:
                for rec_from_line in move.reconcile_from_ids:
                    rec_from_line.move_from_id.calculate_reconcilations(False)
            if move.state == 'done':
                reconcile_quantity = 0
                for rec_line in move.reconcile_to_ids:
                    if rec_line.move_to_id.state == 'done':
                        reconcile_quantity += rec_line.quantity
                        rec_line.check_reconciliation()
                if reconcile_quantity == move.product_uom_qty:
                    open_move = False
                else:
                    open_move = True
                
            else:
                open_move = False
                reconcile_quantity = 0
            move.write({
                'open': open_move,
                'left_qty': move.product_uom_qty - reconcile_quantity
            })
        return True
    
    @api.model
    def recalculate_reconciliation_info(
        self, product_ids, location_ids, partner_ids
    ):
        domain = []
        if product_ids:
            domain.append(('product_id','in',product_ids))
        if location_ids:
            domain.append('|')
            domain.append(('location_id','in',location_ids))
            domain.append(('location_dest_id','in',location_ids))
        if partner_ids:
            domain.append('|')
            domain.append(('address_id','in',partner_ids))
            domain.append(('address_id.parent_id','in',partner_ids))
        
        moves = self.search(domain, order='date')
        
        _logger.info('Recociliation info')
        
        i = 0
        all_moves = len(moves)
        for move in moves:
            i += 1
            res = i*100/all_moves
            if res/10 > ((i-1)*100/all_moves)/10:
                _logger.info('Progress: %s / %s' % (str(i), str(all_moves)))
            move.reconciliate_moves(move.id)
            move.calculate_reconcilations()
        
        return True

    @api.model
    def thread_recalculate_reconciliation_info(
        self, product_ids, location_ids, partner_ids
    ):
        with Environment.manage():
            new_cr = self.pool.cursor()
            new_self = self.with_env(self.env(cr=new_cr))
            try:
                new_self.recalculate_reconciliation_info(
                    product_ids, location_ids, partner_ids
                )
                new_cr.commit()
            finally:
                new_cr.close()
        return True
    
    @api.model
    def recalculate_reconciliation_info_threaded(
        self, product_ids=[], location_ids=[], partner_ids=[]
    ):
        
        t = threading.Thread(target=self.thread_recalculate_reconciliation_info, args=(
            product_ids, location_ids, partner_ids
        ))
        t.start()
        return True

    @api.multi
    def calculate_move_type(self):
        for move in self:
            from_l = False
            to_l = False
            loc_src = move.location_id
            loc_dest = move.location_dest_id
            if loc_src:
                if loc_src.driver:
                    from_l = 'dr'
                elif loc_src.usage == 'customer':
                    from_l = 'cl'
                elif loc_src.usage == 'inventory':
                    from_l = 'adj'
                else:
                    from_l = 'wh'
            if loc_dest:
                if loc_dest.driver:
                    to_l = 'dr'
                elif loc_dest.usage == 'customer':
                    to_l = 'cl'
                elif loc_dest.usage == 'inventory':
                    to_l = 'adj'
                else:
                    to_l = 'wh'
            if from_l and to_l and move.move_type != from_l+'2'+to_l:
                move.write({
                    'move_type': from_l+'2'+to_l
                })
        return True

    @api.multi
    def update_driver_info(self):
        for move in self:
            move.write(move.location_dest_id.get_driver_info())


    @api.model
    def update_vals(self, vals, create=False):
        prod_obj = self.env['product.product']
        loc_obj = self.env['stock.location']
        addr_obj = self.env['res.partner']
        
        from_l = False
        to_l = False
        
        # if 'product_uom_qty' in vals:
        #     vals['temp_product_uom_qty'] = vals['product_uom_qty']
        # elif 'product_uos_qty' in vals:
        #     vals['temp_product_uom_qty'] = vals['product_uos_qty']
        # elif 'product_qty' in vals:
        #     vals['temp_product_uom_qty'] = vals['product_qty']

        if create:
            vals['create_user_name'] = self.env.user.name or ''
            warehouse = self.env.user.default_warehouse_id or (
                self.env.user.default_region_id.location_id
                and self.env.user.default_region_id.location_id.get_location_warehouse_id()
                or False
            ) or False
            if warehouse:
                vals['user_warehouse_id'] = warehouse.id
                vals['user_warehouse_name'] = warehouse.name

        if 'product_id' in vals:
            if vals.get('product_id', False):
                product = prod_obj.browse(vals['product_id'])
                vals['product_code'] = product.default_code or ''
                vals['product_name'] = product.name or ''
                vals['owner_code_of_product_code'] = product.owner_id and product.owner_id.owner_code or ''
                if 'price_unit' not in vals.keys():
                    vals['price_unit'] = product.get_price()
            else:
                vals['product_code'] = ''
                vals['owner_code_of_product_code'] = ''
                vals['product_name'] = ''

        if vals.get('location_id', False):
            vals['source_location_name'] = self.env['stock.location'].browse(vals['location_id']).name

        if 'location_dest_id' in vals:
            if vals.get('location_dest_id', False):
                driver = loc_obj.browse(vals['location_dest_id'])
                vals.update(driver.get_driver_info())
                vals['destination_location_name'] = self.env['stock.location'].browse(vals['location_dest_id']).name
                
                if driver.driver:
                    to_l = 'dr'
                elif driver.usage == 'customer':
                    to_l = 'cl'
                elif driver.usage == 'inventory':
                    to_l = 'adj'
                else:
                    to_l = 'wh'

            else:
                vals['driver_code'] = ''
                vals['driver_company_code'] = ''
                vals['driver_company_name'] = ''
                
        if 'address_id' in vals:
            if vals.get('address_id', False):
                address = addr_obj.browse(vals['address_id'])
                vals['partner_name'] = address.parent_id and address.parent_id.name or address.name or ''
                vals['partner_code'] = address.parent_id and address.parent_id.ref or address.ref or ''
            else:
                vals['partner_name'] = ''
                vals['partner_code'] = ''
        
        if vals.get('location_id', False):
            location = loc_obj.browse(vals['location_id'])
            
            if location.driver:
                from_l = 'dr'
            elif location.usage == 'customer':
                from_l = 'cl'
            elif location.usage == 'inventory':
                from_l = 'adj'
            else:
                from_l = 'wh'
        if from_l and to_l:
            vals['move_type'] = from_l+'2'+to_l
            
        if 'product_uom_qty' in vals and 'product_uos_qty' not in vals:
            vals['product_uos_qty'] = vals['product_uom_qty']
            
        if 'company_id' not in vals.keys():
            vals['company_id'] = self.env['res.users'].browse(self.env.uid).company_id.id
            
        # if 'product_uom_qty' in vals and 'product_qty' not in vals:
        #     vals['product_qty'] = vals['product_uom_qty']
        return True
    
    @api.model
    def create(self, vals):
        self.update_vals(vals, create=True)
        return super(StockMove, self).create(vals)
    
    @api.multi
    def write(self, vals):
        self.update_vals(vals)
        res = super(StockMove, self).write(vals)
        if 'state' in vals:
            self.calculate_reconcilations()
            self.calculate_move_type()
        return res
    
    @api.multi
    def add_quantity(self, coeff=1):
        loc_stock_obj = self.env['sanitex.product.location.stock']
        part_stock_obj = self.env['sanitex.product.partner.stock']
        for move in self:
            if move.location_id\
                and move.location_dest_id and move.product_id\
            :
                quantity = coeff * move.product_uom_qty
                loc_pos_id = move.location_dest_id.id
                loc_neg_id = move.location_id.id
                product_id = move.product_id.id

                loc_stock_obj.add_quantity(loc_pos_id, product_id, quantity)
                loc_stock_obj.add_quantity(loc_neg_id, product_id, -quantity)
                    
            if move.location_id\
                and move.location_dest_id and move.product_id\
                and move.address_id\
            :
                product_id = move.product_id.id
                partner_id = move.address_id.id
                quantity = move.product_uom_qty * coeff
                if move.picking_id.picking_type_id.code == 'incoming':
                    quantity = quantity * -1
                part_stock_obj.add_quantity(
                    partner_id, product_id,
                    quantity, price=move.price_unit
                )
        return True

    @api.multi
    def check_quantities(self):
        if self.ids:
            check_sql = '''
                SELECT
                    CASE
                        WHEN sl1.driver = True THEN sl1.id
                        WHEN sl2.driver = True THEN sl2.id
                    END,
                    sm.product_id,
                    sm.product_code,
                    sm.product_name,
                    CASE
                        WHEN sl1.driver = True THEN sl1.name
                        WHEN sl2.driver = True THEN sl2.name
                    END,
                    sm.product_uom_qty
                FROM
                    stock_move sm
                    JOIN stock_location sl1 on (sl1.id = sm.location_id)
                    JOIN stock_location sl2 on (sl2.id = sm.location_dest_id)
                WHERE
                    sm.id in %s
                    AND (sl1.driver = True OR sl2.driver=True)
            '''
            check_where = (tuple(self.ids),)
            self.env.cr.execute(check_sql, check_where)
            drivers = self.env.cr.fetchall()
            for driver in drivers:
                qty = self.get_sumed_qty_with_sql(driver[0], driver[1])
                if qty < 0.0:
                    msg = _('After confirming transfer from %s. His debt for produtc \'%s\' will be negatve(%s). Current %s debt for this product is %s') % (
                        driver[4], '[' + driver[2] + '] ' + driver[3], str(qty), driver[4], str(qty + driver[5])
                    )
                    raise UserError(msg)

    @api.multi
    def action_done_bls(self):
        # Perdarytas stock.move patvirtinimas, nes BLS'e svarbu tik būsena
        # nereikia jokio papildomo funkcionalumo, kuris yra standarte
        self.with_context(recompute=False).write({'state': 'done'})
        self.check_quantities()
        self.add_quantity()
        return True

    # @api.multi
    # def action_done(self):
    #     # Nebenaudojama
    #     res = super(StockMove, self).action_done(
    #         cr, uid, ids, context=context
    #     )
    #     for id in ids:
    #         move = self.browse(cr, uid, id, context=context)
    #         if move.state == 'done':
    #             self.add_quantity(cr, uid, [id], context=context)
    #     return res
    
    @api.multi
    def action_return_bls(self):
        self.write({'state': 'draft'})
        return True

    @api.multi
    def cancel_reconciliation(self):
        for move in self:
            if move.state == 'done':
                for reconcile_line in move.reconcile_to_ids:
                    if reconcile_line.move_to_id.state == 'done':
                        raise UserError(_('You cant cancel move(ID: %s) because it is reconciled to move(ID: %s) which is already done. You have to delete reconciliation from move(ID: %s)') % (
                                str(id), str(reconcile_line.move_to_id.id), str(reconcile_line.move_to_id.id)
                            )
                        )
                        
        return True

    @api.multi
    def get_reconciled_qty(self, rec_type):
        qty = 0
        if rec_type == 'to':
            lines = self.reconcile_to_ids
        elif rec_type == 'from':
            lines = self.reconcile_from_ids
        else:
            lines = []
            
        for line in lines:
            qty += line.quantity
        
        return qty 
    
    @api.multi
    def get_reconciled_from_qty(self):
        return self.get_reconciled_qty('from')

    @api.multi
    def get_reconciled_to_qty(self):
        return self.get_reconciled_qty('to')

    @api.multi
    def action_cancel_bls(self):
        context = self.env.context or {}
        do_not_calculate_stocks = self.env['stock.move']
        self.cancel_reconciliation()
        for move in self:
            if move.state == 'draft' and context.get('pick_unlink', False):
                do_not_calculate_stocks += move
            if move.state != 'done':
                do_not_calculate_stocks += move

        self.write({'state': 'cancel'})
        (self - do_not_calculate_stocks).filtered(lambda m: m.state != 'released').add_quantity(-1)
        return True


    @api.multi
    def update_invoice_line_reference(self, invoice_line_id):
        if not self:
            return
        update_sql = '''
            UPDATE
                stock_move
            SET
                invoice_line_id = %s
            WHERE
                id in %s
        '''
        update_where = (invoice_line_id, self._ids)
        self.env.cr.execute(update_sql, update_where)


#     @api.multi
#     def action_cancel(self):
#         # nebenaudojama
#         """ Cancels the moves and if all moves are cancelled it cancels the picking.
#         @return: True
#         """
#         if context is None:
#             context = {}
#
#         procurement_obj = self.env('procurement.order')
#         q_obj = self.env('stock.quant')
#         op_obj = self.env('stock.move.operation.link')
#         context = context or {}
#         ctx_unlink = context.copy()
#         ctx_unlink['force_unlink'] = True
#         procs_to_check = []
#         do_not_calculate_stocks = []
#
#         self.cancel_reconciliation(cr, uid, ids, context=context)
#
#         for move in self.browse(cr, uid, ids, context=context):
#             if move.state == 'draft' and context.get('pick_unlink', False):
#                 do_not_calculate_stocks.append(move.id)
#             if move.state != 'done':
#                 do_not_calculate_stocks.append(move.id)
# #             if move.state == 'done':
# #                 raise osv.except_osv(_('Operation Forbidden!'),
# #                         _('You cannot cancel a stock move that has been set to \'Done\'.'))
#             if move.reserved_quant_ids:
#                 self.env("stock.quant").quants_unreserve(cr, uid, move, context=context)
#             q_ids = q_obj.search(cr, uid, [
#                 ('history_ids','in',[move.id])
#             ], context=context)
#
#             q_obj.unlink(cr, uid, q_ids, context=ctx_unlink)
#             if move.linked_move_operation_ids:
#                 op_obj.unlink(cr, uid, [op.id for op in move.linked_move_operation_ids], context=context)
#             if context.get('cancel_procurement'):
#                 if move.propagate:
#                     procurement_ids = procurement_obj.search(cr, uid, [('move_dest_id', '=', move.id)], context=context)
#                     procurement_obj.cancel(cr, uid, procurement_ids, context=context)
#             else:
#                 if move.move_dest_id:
#                     if move.propagate:
#                         self.action_cancel(cr, uid, [move.move_dest_id.id], context=context)
#                     elif move.move_dest_id.state == 'waiting':
#                         #If waiting, the chain will be broken and we are not sure if we can still wait for it (=> could take from stock instead)
#                         self.write(cr, uid, [move.move_dest_id.id], {'state': 'confirmed'}, context=context)
#                 if move.procurement_id:
#                     # Does the same as procurement check, only eliminating a refresh
#                     procs_to_check.append(move.procurement_id.id)
#
#
#         res = self.write(cr, uid, ids, {'state': 'cancel', 'move_dest_id': False}, context=context)
#         if procs_to_check:
#             procurement_obj.check(cr, uid, procs_to_check, context=context)
#         for id in ids:
#             if id in do_not_calculate_stocks:
#                 continue
#             move = self.browse(cr, uid, id, context=context)
#             if move.state != 'released':
#                 self.add_quantity(cr, uid, [id], -1, context=context)
#         return res

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):

        # context = self.env.context
        # ctx = context.copy()
        # self.with_context(ctx).update_args(args)

        res = super(StockMove, self).search(
            args, offset=offset, limit=limit,
            order=order, count=count
        )
        return res

    @api.multi
    def unlink(self):
        recalculate_moves = self.mapped('reconcile_from_ids').mapped('move_from_id')
        res = super(StockMove, self).unlink()
        recalculate_moves.calculate_reconcilations()
        return res 

class StockPackingCorrection(models.Model):
    _name = 'stock.packing.correction'
    _inherit = 'mail.thread'
    _description = 'Stock Picking Correction'    
    
    @api.model
    def _get_number_for_picking(self, owner_id=None):
        # seq_obj = self.env['ir.sequence']
        # seqs = seq_obj.search([
        #     ('code','=','stock_packing_correction_number'),
        # ], limit=1)
        # if seqs:
        #     return seqs.next_by_id()
        
        warehouse = self.env['stock.warehouse'].browse(self._get_wh())
        if self.env.user.company_id.get_sender_for_loadlist_report():
            return self.env['stock.picking'].get_picking_name('internal_transfer_to_driver',
                warehouse=warehouse, owner=self.env['product.owner'].browse(owner_id)
            )
        else:
            return warehouse and warehouse.sequence_for_corection_id.next_by_id()

    @api.model
    def _get_wh(self):
        usr_obj = self.env['res.users']
        user = usr_obj.browse(self.env.uid)
        wh = user.get_default_warehouse()
        if not wh:
            raise UserError(_('To create correction you need to select a warehouse'))
        return wh

    location_id = fields.Many2one(
        'stock.location', 'Driver', required=True,
        states={'done':[('readonly',True)]},
        track_visibility='onchange'
    )
    driver_name = fields.Char('Driver Name', size=128, readonly=True,
        track_visibility='onchange'
    )
    state = fields.Selection([
        ('draft','Draft'),
        ('done','Done')
    ], 'State', readonly=True, track_visibility='onchange', default='draft')
    number = fields.Char('Number',
        readonly=True,
        track_visibility='onchange',
        size=128
    )
    reason = fields.Selection([
            # ('operator_mistake','Operators Mistake'),
            # ('driver_shortage','Drivers Shortage')
            ('tare_return','Tare Return'),
            ('transfer_to_driver','Transfer to Driver')
        ], 'Operation Type', required=True,
        track_visibility='onchange',
        states={'done':[('readonly',True)]}
    )
    return_to_warehouse_id = fields.Many2one(
        'stock.warehouse', 'Return to Warehouse', readonly=True,
        track_visibility='onchange', default=_get_wh
    )
    line_ids = fields.One2many(
        'stock.packing.correction.line', 'correction_id', 'Lines',
        states={'done':[('readonly',True)]},
        track_visibility='onchange'
    )
    picking_to_warehouse_id = fields.Many2one(
        'stock.picking', 'Transfer To Warehouse',
        states={'done':[('readonly',True)]},
        track_visibility='onchange'
    )
    picking_to_warehouse_ids = fields.One2many('stock.picking', 'picking_to_warehouse_for_packing_id',
        'Transfers To Warehouse', states={'done':[('readonly',True)]},
        track_visibility='onchange', help='Grouped by owner'
    )
    picking_to_driver_id = fields.Many2one(
        'stock.picking', 'Transfer To Driver',
        states={'done':[('readonly',True)]},
        track_visibility='onchange'
    )
    picking_to_driver_ids = fields.One2many('stock.picking', 'picking_to_driver_for_packing_id',
        'Transfers To Driver', states={'done':[('readonly',True)]},
        track_visibility='onchange', help='Grouped by owner'
    )
    date = fields.Datetime('Corection Date, Time',
        readonly=True, required=True,
        track_visibility='onchange', default=lambda self: time.strftime('%Y-%m-%d %H:%M:%S')
    )
    show_all_drivers = fields.Boolean('Allow to Select From All Drivers',
        help='Drivers are filtered by users region. When this checkbox is marked region filter will not be applied'
    )
    stock_source_location_id = fields.Many2one('stock.location', 'Tare will be taken from',
        states={'done':[('readonly',True)]}, track_visibility='onchange',
        help='Location from which tare will be transfered to driver. If left empty default location will be selected from warehouse settings'
    )
    stock_source_location2_id = fields.Many2one('stock.location', 'Tare will be taken from',
        help='Location from which tare will be transfered to driver. If left empty default location will be selected from warehouse settings'
    )
    stock_source_location_readonly = fields.Boolean('Source Location Readonly', default=True)
    stock_return_location_id = fields.Many2one('stock.location', 'Tare will be return to',
        states={'done':[('readonly',True)]}, track_visibility='onchange',
        help='Location where tare will be returned from driver. If left empty default location will be selected from warehouse settings'
    )
    stock_return_location2_id = fields.Many2one('stock.location', 'Tare will be return to',
        states={'done':[('readonly',True)]},
        help='Location where tare will be returned from driver. If left empty default location will be selected from warehouse settings'
    )
    stock_return_location_readonly = fields.Boolean('Return Location Readonly', default=True)
    lines_filled_in = fields.Boolean('Lines Filled In', default=False)
    owner_codes = fields.Char('Own.', size=32, readonly=True)
    owner_ids = fields.Many2many('product.owner', 'correction_owner_rel', 'correction_id', 'owner_id', 'Owners', readonly=True)
    status_name = fields.Char('Status', size=64, readonly=True)
    owner_id = fields.Many2one('product.owner', 'Owner', readonly=True)
    user_confirm_id = fields.Many2one('res.users', 'Confirmed By', readonly=True,
        help='User who confirmed this document.'
    )
    
    _rec_name = 'number'
    
    _order = 'date desc, number desc'

    @api.multi
    def update_name(self):
        for correction in self:
            pickings = correction.picking_to_warehouse_ids + correction.picking_to_driver_ids
            names = pickings.mapped('name')
            correction.write({
                'number': ', '.join(names)
            })

    @api.multi
    def get_document_owners(self):
        return self.line_ids.mapped('product_id').mapped('owner_id')

    @api.multi
    def check_owner(self):
        return True
        # for correction in self:
        #     correction.line_ids.mapped('product_id').check_product_owner(correction)

    # @api.onchange('stock_return_location_id', 'stock_source_location_id')
    # def on_change_location(self):
    #     self.stock_return_location2_id = self.stock_return_location_id
    #     self.stock_source_location2_id = self.stock_source_location_id

    @api.model
    def update_vals(self, vals):
        if vals.get('location_id', False):
            vals['driver_name'] = self.env['stock.location'].browse(vals['location_id']).name
        # vals['stock_source_location_id'] = vals.get('stock_source_location2_id', False)
        # vals['stock_return_location_id'] = vals.get('stock_return_location2_id', False)

    @api.multi
    def name_get(self):
        res = []
        for correction in self:
            name = correction.number or _('New')
            res.append((correction.id, name))
        return res


    @api.multi
    def _export_rows(self, fields):
        if self.env.user.company_id.user_faster_export:
            res = self.env['ir.model'].export_rows_with_psql(fields, self)
        else:
            res = super(StockPackingCorrection, self)._export_rows(fields)
        return res


    @api.onchange('return_to_warehouse_id')
    def on_change_warehouse(self):
        if self.return_to_warehouse_id:
            self.stock_source_location_id = self.return_to_warehouse_id.wh_output_stock_loc_id and \
                self.return_to_warehouse_id.wh_output_stock_loc_id.id or False
            self.stock_return_location_id = self.return_to_warehouse_id.wh_return_stock_loc_id and \
                self.return_to_warehouse_id.wh_return_stock_loc_id.id or False
        else:
            self.stock_source_location_id = False
            self.stock_return_location_id = False

    # @api.onchange('line_ids')
    # def on_change_lines(self):
    #     stock_source_location_readonly = True
    #     stock_return_location_readonly = True
    #     for line in self.line_ids:
    #         if line.correction_qty > 0:
    #             stock_source_location_readonly = False
    #         elif line.correction_qty < 0:
    #             stock_return_location_readonly = False
    #         if stock_source_location_readonly and stock_return_location_readonly:
    #             break
    #     self.stock_source_location_readonly = stock_source_location_readonly
    #     self.stock_return_location_readonly = stock_return_location_readonly

    @api.multi
    def check_warehouse_location(self):
        for correction in self:
            if correction.reason == 'transfer_to_driver':
                loc_type = 'src'
            else:
                loc_type = 'dest'
            location = correction.get_location(loc_type)
            if correction.return_to_warehouse_id != location.get_location_warehouse_id():
                raise UserError(_('Location \'%s\' does not belong to warehouse \'%s\'. Please change location to one of your own warehouse.') % (
                    location.name, correction.return_to_warehouse_id.name
                ))

    @api.model
    def create(self, vals):
        self.update_vals(vals)
        correction = super(StockPackingCorrection, self).create(vals)
        correction.check_owner()
        correction.check_warehouse_location()
        return correction

    @api.multi
    def write(self, vals):
        if vals.get('reason', False):
            for correction in self:
                if correction.reason != vals['reason']:
                    raise UserError(_('It is forbidden to change correction type.'))
        self.update_vals(vals)
        res = super(StockPackingCorrection, self).write(vals)
#         if vals.get('reason', False):
#             self._check_quantities()
        self.check_warehouse_location()
        self.check_owner()
        return res

    @api.model
    def get_search_domain(self, args):
        context = self._context or {}
        if context.get('search_corrections_by_warehouse', False):
            user = self.env['res.users'].browse(self.env.uid)
            if not user.default_warehouse_id:
                raise UserError(_('To open corrections you need to select warehouse'))
            available_wh_id = user.default_warehouse_id.id
            if ('return_to_warehouse_id','=',available_wh_id) not in args:
                args.append(('return_to_warehouse_id','=',available_wh_id))

    @api.model
    def _search(
        self, args, offset=0, limit=None,
        order=None, count=False,
        access_rights_uid=None
    ):
        self.get_search_domain(args)
        return super(StockPackingCorrection, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )
    
    @api.multi
    def create_stock_picking(self, loc_id, dest_loc_id, owner_id, correction_type):
        pick_obj = self.env['stock.picking']

        pick_vals = {}
        pick_vals.update(pick_obj.default_get(pick_obj._fields))
        pick_vals['picking_type_id'] = self.return_to_warehouse_id.int_type_id.id
        pick_vals['location_id'] = loc_id
        pick_vals['location_dest_id'] = dest_loc_id
        pick_vals['owner_id'] = owner_id
        pick_vals['name'] = self.number or self._get_number_for_picking(owner_id=owner_id)
        if correction_type == 'to_wh':
            pick_vals['picking_to_warehouse_for_packing_id'] = self.id
        else:
            pick_vals['picking_to_driver_for_packing_id'] = self.id
        return pick_obj.create(pick_vals)

    @api.model
    def get_move_vals(self, line_id):
        vals = {}
        
        line = self.env['stock.packing.correction.line'].browse(line_id)
        # correction = line.correction_id
        
        # if line.correction_qty > 0.0:
        #     # vals['product_qty'] = line.correction_qty
        #     vals['product_uom_qty'] = line.correction_qty
        #     vals['product_uos_qty'] = line.correction_qty
        #     vals['picking_id'] = line.get_picking().id
            # vals['picking_id'] = correction.picking_to_driver_id and correction.picking_to_driver_id.id \
            #     or correction.create_stock_picking('internal',
            #         loc_id = line.get_source_location().id,
            #         dest_loc_id = line.get_destination_location().id
            #     )
            # vals['location_id'] = line.get_source_location().id
            # vals['location_dest_id'] = line.get_destination_location().id
            # if not correction.picking_to_driver_id:
            #     correction.write({
            #         'picking_to_driver_id': vals['picking_id'],
            #     })
        # else:
            # vals['product_qty'] = abs(line.correction_qty)
        vals['product_uom_qty'] = abs(line.correction_qty)
        vals['product_uos_qty'] = abs(line.correction_qty)
        vals['picking_id'] = line.get_picking().id
            # vals['picking_id'] = correction.picking_to_warehouse_id and correction.picking_to_warehouse_id.id \
            #     or correction.create_stock_picking('internal',
            #         loc_id = line.get_source_location().id,
            #         dest_loc_id = line.get_destination_location().id
            #     )
        vals['location_id'] = line.get_source_location().id
        vals['location_dest_id'] = line.get_destination_location().id
        vals['date'] = line.correction_id.date
        vals['tare_movement'] = True
            # if not correction.picking_to_warehouse_id:
            #     correction.write({
            #         'picking_to_warehouse_id': vals['picking_id'],
            #     })
        return vals 

    @api.multi
    def action_done_and_print(self):
        print_action = self.env.ref('config_sanitex_delivery.action_stock_correction_print_report_osv').read()[0]
        if print_action['context']:
            print_action['context'] = print_action['context'][:-1] + ', \'for_confirmation\':True}'
        return print_action

    @api.multi
    def action_done(self):
        move_obj = self.env['stock.move']
        route_obj = self.env['stock.route']
        rec_obj = self.env['stock.move.reconcile']
        moves_to_reconcile = []
        for correction in self:
            if not correction.line_ids:
                raise UserError(_('You can\'t confirm corection(ID: %s) without lines.') % str(correction.id))
            if not correction.line_ids.filtered(lambda line_rec: line_rec.correction_qty > 0):
                raise UserError(
                    _('You can\'t confirm corection(ID: %s) without any lines with quantity greater than zero. There should be at least one line with quantity filled in.') % str(correction.id)
                )
            for line in correction.line_ids:
                if line.correction_qty == 0:
                    continue
                if correction.reason == 'tare_return':
                    if line.move_id and line.move_id.left_qty < line.correction_qty:
                        raise UserError(
                            _('You are trying to reconcile %s units of %s with stock move \'%s\', but this particular move has only %s units left unreconciled') %(
                                str(line.correction_qty), line.product_id.name, line.move_id.make_name(), str(line.move_id.left_qty)
                            )
                        )
                move_vals = {}
                move_vals['product_id'] = line.product_id.id
                update_vals = self.get_move_vals(line.id)
                temp_move = move_obj.new(move_vals)
                temp_move.onchange_product_id()
                move_vals.update(temp_move._convert_to_write(temp_move._cache))
                move_vals.update(update_vals)
                
                if line.price_unit:
                    move_vals['price_unit'] = line.price_unit

                move_to = move_obj.create(move_vals)

                if correction.reason == 'tare_return':
                    if line.move_id:
                        rec_obj.reconcile(
                            line.move_id.id, move_to.id,
                            qty=line.correction_qty
                        )
                    else:
                        moves_to_reconcile.append(move_to)
            for move_to_id in moves_to_reconcile:
                move_obj.reconciliate_moves(move_to_id.id)

            for picking_to_warehouse in correction.picking_to_warehouse_ids:
                route_obj.with_context(create_invoice_document_for_picking=True).confirm_picking(picking_to_warehouse.id)
                picking_to_warehouse.send_tare_qty_info()
            
            for picking_to_driver in correction.picking_to_driver_ids:
                route_obj.with_context(create_invoice_document_for_picking=True).confirm_picking(picking_to_driver.id)
                picking_to_driver.send_tare_qty_info()
                
            # if correction.picking_to_driver_id:
            #     correction.picking_to_driver_id.send_tare_qty_info()
            #
            # if correction.picking_to_warehouse_id:
            #     correction.picking_to_warehouse_id.send_tare_qty_info()
        self.update_name()
        self.update_owner_info()
        self.update_status_name()
        self.write({'state': 'done', 'user_confirm_id': self.env.uid})
        return True

    @api.multi
    def button_generate_lines(self):
        line_obj = self.env['stock.packing.correction.line']
        for correction in self:
            if correction.state == 'done':
                raise UserError(_('This corection is alredy done'))
            if not correction.location_id:
                raise UserError(_('You have to select driver'))
            if not correction.return_to_warehouse_id:
                raise UserError(_('You have to select warehouse'))
            driver = correction.location_id
            debt_dict = driver.get_drivers_debt_all_with_sql()
            if correction.reason == 'tare_return':
                products = self.env['product.product'].browse(list(debt_dict.keys()))
            else:#if correction.reason == 'transfer_to_driver':
                products = correction.return_to_warehouse_id.product_ids

            for product in sorted(products, key=lambda prod: prod.default_code): #products:
                line_vals = {}
                line_vals['correction_id'] = self.id
                line_vals['correction_qty'] = 0.0
                line_vals['product_id'] = product.id
                line_vals['product_code'] = product.default_code or ''
                line_vals['drivers_debt'] = debt_dict.get(product.id, 0.0)
                line_obj.create(line_vals)
        self.write({'lines_filled_in': True})
        return True

    @api.multi
    def update_owner_info(self):
        for correction in self:
            pickings = correction.picking_to_driver_ids + correction.picking_to_warehouse_ids
            if pickings and pickings.mapped('owner_id'):
                owners = pickings.mapped('owner_id')
                if len(list(set(owners._ids))) > 1: 
                    correction.write({
                        'owner_codes': ', '.join(list(set(owners.mapped('owner_code')))),
                        'owner_ids': [(6, 0, list(set(owners._ids)))]
                    })
                else:
                    correction.write({
                        'owner_codes': ', '.join(list(set(owners.mapped('owner_code')))),
                        'owner_id': owners._ids[0]
                    })
                    
    
    @api.multi
    def update_status_name(self):
        for correction in self:
            correction.write({
                'status_name': correction.reason == 'transfer_to_driver' and correction.stock_source_location_id and correction.stock_source_location_id.name or
                    (correction.reason == 'tare_return' and  correction.stock_return_location_id and correction.stock_return_location_id.name) or ''
            })
#     @api.multi
#     def _check_quantities(self):
#         for correction in self:
#             if correction.reason == 'transfer_to_driver':
#                 for line in correction.line_ids:
#                     if line.correction_qty < 0.0:
#                         raise UserError(
#                             _('\'Transfer to driver\' corrections can only have lines with positive correction quantity. Bad correction(%s, ID: %s), line (%s, ID: %s)') % (
#                                 correction.number, str(correction.id), line.product_id.name, str(line.id)
#                             )
#                         )
#             if correction.reason == 'tare_return':
#                 for line in correction.line_ids:
#                     if line.correction_qty > 0.0:
#                         raise UserError(
#                             _('\'Tare return\' corrections can only have lines with positive correction quantity. Bad correction(%s, ID: %s), line (%s, ID: %s)') % (
#                                 correction.number, str(correction.id), line.product_id.name, str(line.id)
#                             )
#                         )
#         return True

    @api.multi
    def unlink(self):
        context = self.env.context or {}
        if not context.get('allow_to_unlink_correction', False):
            raise UserError(_('You are not allowed to unlink corrections (IDs: %s)') % str(self.mapped('id')))
        return super(StockPackingCorrection, self).unlink()

    @api.model
    def cron_unlink_old_draft_corrections(self, hours=1):
        # Ištrinami juodraštinės vidinės operacijos kurios
        # yra senesnės nei 1 valanda. Tam kad nesimėtytų nereikalingi objektai.

        _logger.info('Removing draft corrections older than %s hours' % str(hours))
        time_domain = datetime.now() - timedelta(hours=hours)
        corrections = self.search([
            ('state','=','draft'),
            ('create_date','<',time_domain.strftime('%Y-%m-%d %H:%M:%S'))
        ])
        _logger.info('Found %s corrections to delete' % str(len(corrections)))
        corrections.with_context(allow_to_unlink_correction=True).unlink()


    @api.multi
    def do_not_print_reports(self, reports=None):
        if reports is None:
            reports = [
                'config_sanitex_delivery.driver_return_act', # Taros grąžinimo aktas (Vidinė op.)
                'config_sanitex_delivery.tare_to_driver_act', # Taros perdavimo aktas vairuotojui (Vidinė op.)	
            ]
        elif isinstance(reports, str):
            reports = [reports]

        report_env = self.env['ir.actions.report']

        for picking in self.mapped('picking_to_driver_ids') + self.mapped('picking_to_warehouse_ids'):
            for report_name in reports:
                report_env.do_not_print_report(picking, report_name)


    @api.multi
    def get_name_for_report(self):
        context = self.env.context
        if context.get('owner_to_print', False):
            return (self.picking_to_warehouse_ids + self.picking_to_driver_ids).filtered(
                lambda picking:
                    picking.owner_id
                    and picking.owner_id.id == context['owner_to_print']
            ).name
        else:
            return self.name

    @api.multi
    def get_location(self, loc_type):
        # if self.correction_id.stock.location_id:
        #     return self.correction_id.stock.location_id
        if self.reason == 'transfer_to_driver':
            if loc_type == 'dest':
                return self.location_id
            else:
                return self.stock_source_location_id and self.stock_source_location_id \
                       or self.return_to_warehouse_id.wh_output_stock_loc_id
        else:
            if loc_type == 'dest':
                return self.stock_return_location_id and self.stock_return_location_id \
                       or self.return_to_warehouse_id.wh_return_stock_loc_id
            else:
                return self.location_id


    
class StockPackingCorrectionLine(models.Model):
    _name = 'stock.packing.correction.line'
    _inherit = 'mail.thread'
    _description = 'Stock Picking Correction Line'    

    correction_id = fields.Many2one(
        'stock.packing.correction', 'Correction', ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product', 'Product', required=True,
        track_visibility='onchange'
    )
    product_code = fields.Char('Product Code', readonly=True,
        track_visibility='onchange'
    )
    correction_qty = fields.Integer('Correction Quantity',
        track_visibility='onchange', ondelete='cascade'
    )
    move_id = fields.Many2one('stock.move', 'Reconcile From')
    drivers_debt = fields.Float('Debt', digits=(16,0), readonly=True)
    price_unit = fields.Float("Price Unit", digits=(16,2))
    
    _order = 'product_code'

    @api.multi
    def get_picking(self):
        owner = self.product_id.owner_id
        if self.correction_id.reason == 'tare_return':
            pickings = self.correction_id.picking_to_warehouse_ids
        else:
            pickings = self.correction_id.picking_to_driver_ids
        owner_picking = pickings.filtered(lambda picking_rec: picking_rec.owner_id == owner)
        if not owner_picking:
            owner_picking = self.correction_id.create_stock_picking(
                self.get_source_location().id, self.get_destination_location().id,
                owner.id, self.correction_id.reason == 'transfer_to_driver' and 'from_wh' or 'to_wh'
            )
        return owner_picking

    @api.multi
    def get_location(self, loc_type):
        # if self.correction_id.stock.location_id:
        #     return self.correction_id.stock.location_id
        if self.correction_id.reason == 'transfer_to_driver':
            if loc_type == 'dest':
                return self.correction_id.location_id
            else:
                return self.correction_id.stock_source_location_id and self.correction_id.stock_source_location_id \
                    or self.correction_id.return_to_warehouse_id.wh_output_stock_loc_id
        else:
            if loc_type == 'dest':

                return self.correction_id.stock_return_location_id and self.correction_id.stock_return_location_id \
                    or self.correction_id.return_to_warehouse_id.wh_return_stock_loc_id
            else:
                return self.correction_id.location_id

    @api.multi
    def get_destination_location(self):
        return self.get_location('dest')

    @api.multi
    def get_source_location(self):
        return self.get_location('src')

    @api.onchange('product_id')
    def on_change_product_id(self):
        if self.product_id:
            if self.product_id.default_code:
                self.product_code = self.product_id.default_code
        self.move_id = False

    @api.onchange('move_id')
    def onchange_move(self):
        if self.move_id:
            if self.correction_qty > self.move_id.left_qty or self.correction_qty==0:
                self.correction_qty = self.move_id.left_qty


    @api.onchange('correction_id')
    def onchange_quantity(self):
        res = {'readonly': {}}
        if self.correction_id.reason == 'transfer_to_driver':
            self.move_id = False
            res['readonly']['move_id'] = True                
        return res
#     @api.onchange('correction_qty')
#     def onchange_quantity(self):
#         res = {'readonly': {}}
#         if self.correction_qty >= 0:
#             self.move_id = False
#             res['readonly']['move_id'] = True                
#         return res
        
    @api.model
    def create(self, vals):
        if vals.get('correction_qty', 0) < 0:
            raise UserError(_('Only positive correction quantity is allowed.'))
        correction_env = self.env['stock.packing.correction']
        if vals.get('correction_id', False):
            correction = correction_env.browse(vals['correction_id'])
            if correction.reason == 'transfer_to_driver':
                vals['move_id'] = False
        if 'product_id' in vals:
            temp_line = self.new(vals)
            temp_line.on_change_product_id()
            vals.update(temp_line._convert_to_write(temp_line._cache))

        line = super(StockPackingCorrectionLine, self).create(vals)

#         if line.correction_id:
#             line.correction_id._check_quantities()
        return line

    @api.multi
    def write(self, vals):
        if vals.get('correction_qty', 0) < 0:
            raise UserError(_('Only positive correction quantity is allowed.'))
        res = super(StockPackingCorrectionLine, self).write(vals)
#         if 'correction_qty' in vals or 'correction_id' in vals:
#             for line in self:
#                 if line.correction_id:
#                     line.correction_id._check_quantities()
        if set(vals.keys()) & {'correction_id', 'product_id'}:
            self.mapped('correction_id').check_owner()
        return res

    @api.model
    def get_search_domain(self, args):
        context = self._context or {}
        if context.get('owner_to_print', False):
            args.append(('correction_qty','!=',0))
            args.append(('product_id.owner_id','=',context['owner_to_print']))

    @api.model
    def _search(
        self, args, offset=0, limit=None,
        order=None, count=False,
        access_rights_uid=None
    ):
        self.get_search_domain(args)
        return super(StockPackingCorrectionLine, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )

class StockTemperature(models.Model):
    _name = 'stock.temperature'
    _description = 'Stock Temperature'

    name = fields.Char('Name', size=256, required=True)
    code = fields.Char('Code', size=256, required=True)
    
    _sql_constraints = [
        ('code_id_uniq', 'unique (code)', 'Temperature with this code already exists')
    ]
    
class StockPackageType(models.Model):
    _name = 'stock.package.type'
    _description = 'Stock Package Type'

    name = fields.Char('Name', size=256, required=True)
    code = fields.Char('Code', size=256, required=True)
    
    _sql_constraints = [
        ('code_id_uniq', 'unique (code)', 'Package type with this code already exists')
    ]

class StockPackage(models.Model):
    _name = 'stock.package'
    _description = 'Stock Package'
    
    _inherit = ['mail.thread']

    external_package_id = fields.Char(
        'External ID', size=64, readonly=True,
        track_visibility='onchange'
    )
    packet_date = fields.Datetime(
        'Date', track_visibility='onchange'
    )
    planned_packet = fields.Boolean(
        'Planned Packet', help='Quantities will be specified after writing out the orders',
        track_visibility='onchange'
    )
    orignal_packet_number = fields.Char(
        'Client Original Packet Number', size=128, track_visibility='onchange'
    )
    sender_id = fields.Many2one(
        'res.partner', 'Sender', track_visibility='onchange'
    )
    sender_address_id = fields.Many2one(
        'res.partner', 'Sender Address', track_visibility='onchange'
    )
    pickup_date = fields.Datetime('Pickup Date', track_visibility='onchange')
    no_collection = fields.Boolean(
        'No Collection', help='Sender will deliver package to BLS warehouse',
        track_visibility='onchange')
    buyer_id = fields.Many2one(
        'res.partner', 'Buyer', required=True, track_visibility='onchange'
    )
    buyer_address_id = fields.Many2one(
        'res.partner', 'Buyer Address', track_visibility='onchange'
    )
    no_delivery = fields.Boolean(
        'No Delivery', help='Packages will be left at BLS warehouse',
        track_visibility='onchange'
    )
    delivery_date = fields.Datetime(
        'Delivery Date', track_visibility='onchange'
    )
    internal_order_number = fields.Char(
        'Internal Order Number', size=128,
        track_visibility='onchange'
    )
    packet_temp_mode_id = fields.Many2one(
        'stock.temperature', 'Packet Temperature Mode',
        track_visibility='onchange'
    )
    comment = fields.Text(
        'Comment', track_visibility='onchange'
    )
    document_ids = fields.One2many(
        'stock.package.document', 'package_id', 'Documents',
        track_visibility='onchange'
    )
    container_ids = fields.One2many(
        'account.invoice.container', 'package_id', 'Containers',
        track_visibility='onchange'
    )
    intermediate_id = fields.Many2one(
        'stock.route.integration.intermediate', 'Created by',
        readobly=True, track_visibility='onchange'
    )
    state = fields.Selection([
        ('template_order','Template (Order)'),
        ('taken_from_supplier','Take from the Supplier'),
        ('in_terminal','In Terminal'),
        ('transported','Being Transported'),
        ('delivered','Delivered'),
        ('returned_to_supplier','Returned to Supplier'),
        ('lost','Lost'),
        ('canceled', 'Canceled'),
    ], 'State', readonly=True, track_visibility='onchange')
    company_id = fields.Many2one('res.company', 'Company')
    collection_route_id = fields.Many2one('stock.route', 'Collection Route')
    delivery_route_ids = fields.Many2many(
        'stock.route', 'delivery_package_route_rel',
        'package_id', 'delivery_route_id', 'Delivery Routes', track_visibility='onchange',
        readonly=True
    )
    parcel_type = fields.Selection([
        ('delivery','Delivery'),
        ('collection','Collection'),
    ], 'Parce Type', track_visibility='onchange')
    planned_collection = fields.Boolean('Planned Collection', default=False)
    returnend = fields.Boolean('Returned', default=False)
    buyer_name = fields.Char('Buyer Name', size=128, readonly=True)
    buyer_posid = fields.Char('Buyer POSID', size=128, readonly=True)
    sender_name = fields.Char('Sender Name', size=128, readonly=True)
    sender_posid = fields.Char('Sender POSID', size=128, readonly=True)
    owner_id = fields.Many2one('product.owner', 'Owner')
    total_weight = fields.Float('Total Weight', digits=(16, 3), readonly=True)
    documents_count = fields.Integer('Documents Count', readonly=True)
    collection_direction = fields.Char('Collection Direction', size=256, track_visibility='onchange')
    delivery_direction = fields.Char('Delivery Direction', size=256, track_visibility='onchange')
    picking_warehouse_id = fields.Many2one('stock.warehouse', 'Picking Warehouse', track_visibility='onchange')
    transport_type_id = fields.Many2one('transport.type', 'Transport Type', track_visibility='onchange')
    task_ids = fields.One2many('sale.order', 'related_package_id', 'Transportation Tasks', track_visibility='onchange')
    location_code = fields.Char('Location Code', size=16, readonly=True)
    
    _sql_constraints = [
        ('external_id_uniq', 'unique (external_package_id)', 'Package with this external id already exists')
    ]
    
    _rec_name = 'internal_order_number'
    
    _order = 'packet_date desc'
    
    @api.multi
    def update_weight(self):
        for package in self:
            weight = self.get_total_weight()
            package.write({'total_weight': weight})
        self.mapped('collection_route_id').update_weight()

    @api.model_cr
    def init(self):
        cr = self.env.cr
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_package_intermediate_id_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX stock_package_intermediate_id_index ON stock_package (intermediate_id)')
    
    @api.multi
    def update_counts(self):
        for package in self:
            package.write({'documents_count': len(package.document_ids)})
    
    @api.multi
    def to_dict_for_report(self):
        return {
            'Date': self.packet_date or '',
            'DocumentNum': self.internal_order_number or '',
            'Route': '', 
            'InvSum': str(self.get_total_sum()),
            'Weight': str(self.get_total_weight()),
            'BoxCount': str(len(self.container_ids)),
            'IsTobacco': '',
            'IsAlco': '',
            'CashSum': str(self.get_total_cash()),
            'OwnerCode': '',
            'PckOrderNo': ''
        }
    
    @api.multi
    def get_total_sum(self):
        total_sum = 0.0
        return total_sum
    
    @api.multi
    def get_total_weight(self):
        weight_sum = 0.0
        for pack in self:
            for container in pack.container_ids:
                weight_sum += container.weight
        return weight_sum
    
    @api.multi
    def get_total_cash(self):
        cash_sum = 0.0
        return cash_sum
    
    @api.multi
    def update_state(self):
        for package in self:
            package_states = package.container_ids.mapped('state')
            if list(set(package_states)) == [u'canceled']:
                package.write({'state': 'canceled'})
            elif u'transported' in package_states:
                if u'in_terminal' in package_states and package.returnend:
                    package.write({'state': 'in_terminal'})
                else:
                    package.write({'state': 'transported'})
            elif list(set(package_states)) == [u'returned_to_supplier']:
                package.write({'state': 'returned_to_supplier'})
            elif list(set(package_states)) == [u'lost']:
                package.write({'state': 'lost'})
            elif set(package_states).issubset({u'lost', u'returned_to_supplier', u'delivered'}):
                package.write({'state': 'delivered'})
            elif set(package_states) == {u'canceled', u'in_terminal'}:
                package.write({'state': 'in_terminal'})
            elif set(package_states) == {u'in_terminal'}:
                package.write({'state': 'in_terminal'})
            elif set(package_states) == {u'registered'}:
                if package.no_collection:
                    package.write({'state': 'template_order'})
                else:
                    container_routes = package.container_ids.get_routes()
                    if not container_routes:
                        package.write({'state': 'template_order'})
                    elif u'closed' in container_routes.mapped('state'):
                        package.write({'state': 'taken_from_supplier'})
                    else:
                        package.write({'state': 'template_order'})                     
            
        return True
                

    @api.model
    def update_vals(self, vals):
        if 'sender_id' in vals.keys():
            if vals['sender_id']:
                vals['sender_name'] = self.env['res.partner'].browse(vals['sender_id']).name or ''
            else:
                vals['sender_name'] = ''
        if 'sender_address_id' in vals.keys():
            if vals['sender_address_id']:
                vals['sender_posid'] = self.env['res.partner'].browse(vals['sender_address_id']).possid_code or ''
            else:
                vals['sender_posid'] = ''
        if 'buyer_id' in vals.keys():
            if vals['buyer_id']:
                vals['buyer_name'] = self.env['res.partner'].browse(vals['buyer_id']).name or ''
            else:
                vals['buyer_name'] = ''
        if 'buyer_address_id' in vals.keys():
            if vals['buyer_address_id']:
                vals['buyer_posid'] = self.env['res.partner'].browse(vals['buyer_address_id']).possid_code or ''
            else:
                vals['buyer_posid'] = ''
    
    @api.multi
    def write(self, vals):
        self.update_vals(vals)
        res = super(StockPackage, self).write(vals)
        if set(vals.keys()) & set(PACKAGE_CONTANER_UPDATE_FIELDS):
            self.update_containers()
        if 'collection_route_id' in vals.keys():
            vals['planned_collection'] = bool(vals['collection_route_id'])
        if 'container_ids' in vals.keys():
            self.update_weight()
        if 'document_ids' in vals.keys():
            self.update_counts()
        return res
    
    @api.multi
    def update_containers(self, containers=None):
        for package in self:
            if not package.container_ids:
                continue
            if containers is None:
                containers_to_update = package.container_ids
            else:
                containers_to_update = containers & package.container_ids
            vals = package.read(PACKAGE_CONTANER_UPDATE_FIELDS[:])[0]
            for key in vals.keys():
                if isinstance(vals[key], tuple):
                    vals[key] = vals[key][0]
            containers_to_update.write(vals)
        return True
    
    @api.model
    def create(self, vals):
        self.update_vals(vals)
        if 'state' not in vals.keys():
            vals['state'] = 'taken_from_supplier'
        package = super(StockPackage, self).create(vals)
        link_obj = self.env['stock.route.integration.intermediate.missing_links']
        link2_env = self.env['stock.route.integration.missing_links.new']
        if vals.get('external_package_id', False):
            link_obj.check_for_missing_links(self._name, 
                vals['external_package_id']
            )
            link2_env.check_for_missing_links(
                vals['external_package_id']
            )
        if vals.get('collection_route_id', False):
            vals['planned_collection'] = True
        package.update_containers()
        if 'container_ids' in vals.keys():
            package.update_weight()
        return package
    
    @api.model
    def create_package(self, package_vals):
        context = self.env.context or {}
        interm_obj = self.env['stock.route.integration.intermediate']
        temp_obj = self.env['stock.temperature']
        type_obj = self.env['stock.package.type']
        
        package = self.search([
            ('external_package_id','=',package_vals['external_package_id'])
        ], limit=1)
        
        pack_vals = {}
        if 'packet_temp_mode' in package_vals.keys():
            temp = temp_obj.search([
                ('code','=',package_vals['packet_temp_mode'])
            ], limit=1)
            if temp:
                package_vals['packet_temp_mode_id'] = temp.id
                del package_vals['packet_temp_mode']
            else:
                raise UserError(_('Temperature with code %s does not exist in the system') %package_vals['packet_temp_mode_id'])
           
        if 'packet_type' in package_vals.keys():
            ptype = type_obj.search([
                ('code','=',package_vals['packet_type'])
            ], limit=1)
            if ptype:
                package_vals['packet_type_id'] = ptype.id
                del package_vals['packet_type']
            else:
                raise UserError(_('Packet type with code %s does not exist in the system') %package_vals['packet_type'])
        
        if package_vals.get('parceltype', '') == 'C':
            package_vals['parcel_type'] = 'collection'
            del package_vals['parceltype']
            
            
        pack_vals.update(package_vals)
        if package:
            interm_obj.remove_same_values(package, pack_vals)
            if pack_vals:
                pack_vals['intermediate_id'] = context.get('intermediate_id', False)
                package.write(pack_vals)
                if 'updated_package_ids' in context:
                    context['updated_package_ids'].append((package_vals['external_package_id'], package.id))
                context['package_message'].append(_('Package was successfully updated'))
            
        else:
            pack_vals['intermediate_id'] = context.get('intermediate_id', False)
            pack_vals['state'] = 'taken_from_supplier'
            package = self.create(pack_vals)
            if 'created_package_ids' in context:
                context['created_package_ids'].append((package_vals['external_package_id'], package.id))
            context['package_message'].append(_('Package was successfully created'))
        self.env.cr.commit()
        return package

    @api.multi
    def copy(self, default=None):
        raise UserError(_('You cannot duplicate a package.'))

    @api.model
    def CreatePackage(self, list_of_package_vals):
        inter_obj = self.env['stock.route.integration.intermediate']
        log_obj = self.env['delivery.integration.log']
        
        create_datetime = time.strftime('%Y-%m-%d %H:%M:%S')
        error = self.check_imported_package_values(list_of_package_vals)
        if error:
            log_vals = {
                'create_date': create_datetime,
                'function': 'CreatePackage',
                'received_information': str(json.dumps(list_of_package_vals, indent=2)),
                'returned_information': str(json.dumps(error, indent=2))
            }
            
            log_obj.create(log_vals)
            return error
        
        itermediate = inter_obj.create({
            'datetime': create_datetime,
            'function': 'CreatePackage',
            'received_values': str(json.dumps(list_of_package_vals, indent=2)),
            'processed': False
        })
        self.env.cr.commit()
        itermediate.process_intermediate_objects_threaded()
        return itermediate.id

    @api.model
    def check_imported_package_values(self, list_of_package_vals):
        inter_obj = self.env['stock.route.integration.intermediate']
        result = {}
        required_values = [
            'external_packet_id', 'packet_date', 'external_sender_id', 
            'external_buyer_id',
            'external_buyer_address_id', 'internal_order_number'
        ]
        inter_obj.check_import_values(list_of_package_vals, required_values, result)
        if result:
            return result
        required_doc_values = ['external_document_id', 'document_number', 'document_type']
        
        required_container_values = ['external_container_id', 'package_nr', 'package_weight']

        selection_values = {
            'packet_temp_mode': inter_obj.get_allowed_selection_values('stock.temperature', 'code'),
            'packet_type': inter_obj.get_allowed_selection_values('stock.package.type', 'code'),
        }
        i = 0
        for package_dict in list_of_package_vals:
            i = i + 1
            index = str(i)
            
            if package_dict.get('documents', False):
                line_results = {}
                inter_obj.check_import_values(
                    package_dict.get('documents', []),
                    required_doc_values, line_results, prefix=_('Document')
                )
                if line_results:
                    if index in result.keys():
                        result[index].append(line_results)
                    else:
                        result[index] = [line_results]
                        
            if package_dict.get('containers', False):
                line_results = {}
                inter_obj.check_import_values(
                    package_dict.get('containers', []),
                    required_container_values, line_results, prefix=_('Container')
                )
                if line_results:
                    if index in result.keys():
                        result[index].append(line_results)
                    else:
                        result[index] = [line_results]
                        
                        
                        
            for selection_key in selection_values.keys():
                if selection_key in package_dict.keys():
                    selection_result = inter_obj.check_selection_values(
                        selection_key, package_dict[selection_key],
                        selection_values[selection_key]
                    )
                    if selection_result:
                        if index in result.keys():
                            result[index].append(selection_result)
                        else:
                            result[index] = [selection_result]
                            
        return result
    
    @api.model
    def get_search_domain(self, args):
        context = self.env.context or {}
        if context.get('search_packages_by_warehouse', False):
            user = self.env['res.users'].browse(self.env.uid)
            available_wh_ids = user.get_current_warehouses().mapped('id')
            args.append(('picking_warehouse_id','in',available_wh_ids))

    
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self.env.context or {}
        if context.get('not_in_route', False):
            self.env.cr.execute('''
                SELECT
                    distinct(package_id)
                FROM
                    delivery_package_route_rel
            ''')
            in_route_ids = [res[0] for res in self.env.cr.fetchall()]
            args.append(('id','not in',in_route_ids))
            args.append(('collection_route_id','=',False))
            
        return super(StockPackage, self).search(
            args, offset=offset, limit=limit,
            order=order, count=count
        )

    @api.model
    def _search(
        self, args, offset=0, limit=None,
        order=None, count=False,
        access_rights_uid=None
    ):
        self.get_search_domain(args)
        return super(StockPackage, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )

    @api.multi
    def check_if_in_route(self):
        self.env.cr.execute('''
            SELECT
                route_id
            FROM
                delivery_package_route_rel
            WHERE
                package_id = %s
        ''' % str(self.id))
        res = self.env.cr.fetchall()
        if res:
            return [result[0] for result in res]
        else:
            return False
    
    @api.multi
    def _get_transportation_task_vals(self, type, shipping_warehouse_id, picking_warehouse_id, stock_number_id, order_number_by_route):
        # iš siuntos ištraukiamos reikšmės transportavimo užduotieskūrimui
        
        loc_env = self.env['stock.location']
         
        ship_wh = loc_env.get_location_warehouse_id_from_code(
            shipping_warehouse_id, create_if_not_exists=True
        ) 
        pick_loc, pick_wh= loc_env.get_location_warehouse_id_from_code(picking_warehouse_id, True, create_if_not_exists=True)
        vals = {
            'order_number_by_route': order_number_by_route,
            'route_number_id': stock_number_id,
            'shipping_warehouse_id': ship_wh.id,
            'warehouse_id': pick_wh.id,
            'picking_location_id': pick_loc.id,
            'company_id': self.env['res.users'].browse(self.env.uid).company_id.id,
            'order_package_type': 'package',
            'total_weight': self.get_total_weight(),
            'state': 'blank',
            'show': True,
            'replanned': False,
            'sequence': 1,
            'related_package_id': self.id,
            'name': self.internal_order_number or '',
            'external_sale_order_id': self.external_package_id or str(self.id),
#             'delivery_container_ids': [(6, 0, self.container_ids.mapped('id'))]
            'container_ids': [(6, 0, self.container_ids.mapped('id'))],
            'transport_type_id': self.transport_type_id and self.transport_type_id.id or False,
            'previous_task_received': True,
            'invoice_number': self.document_ids and ', '.join(self.document_ids.mapped('external_document_id')) \
                or self.internal_order_number or '',
            'has_related_document': True,
            'related_document_indication': 'yes'
        }
        if self.owner_id:
            vals['owner_id'] = self.owner_id.id
        
        if type == 'deliver':
            vals['partner_id'] = self.buyer_id.id
            if not self.buyer_address_id:
                raise UserError(_('Package (%s, ID: %s) has no buyer address filled in') % (
                    self.internal_order_number, str(self.id))
                )
            vals['partner_shipping_id'] = self.buyer_address_id.id
            if self.delivery_date:
                # vals['delivery_date'] = self.delivery_date
                vals['shipping_date'] = self.delivery_date
             
            vals['direction'] = self.delivery_direction
            vals['delivery_type'] = 'delivery'
        else:
            vals['partner_id'] = self.sender_id.id
            if not self.sender_address_id:
                raise UserError(_('Package (%s, ID: %s) has no sender address filled in') % (
                    self.internal_order_number, str(self.id))
                )
            vals['partner_shipping_id'] = self.sender_address_id.id
            if self.pickup_date:
                # vals['delivery_date'] = self.pickup_date
                vals['shipping_date'] = self.pickup_date
             
            vals['direction'] = self.collection_direction
            vals['delivery_type'] = 'collection'
        return vals
        
    @api.multi
    def create_transportation_tasks(self, type, shipping_warehouse_id, picking_warehouse_id, stock_number_id, order_number_by_route):
        # iš siuntos sukuriama transportavimo užduotis.
        so_env = self.env['sale.order']
        for package in self:
            so_vals = package._get_transportation_task_vals(
                type, shipping_warehouse_id, picking_warehouse_id, stock_number_id, order_number_by_route
            )
            domain = [('related_package_id','=',package.id)]
            if type == 'collect':
                domain.append(('delivery_type','=','collection'))
                domain.append(('sequence','=',1))
            if type == 'deliver':
                domain.append(('delivery_type','=','delivery'))
                domain.append(('sequence','=',1))
            existing_tasks = so_env.search(domain)
            existing_placeholder_tasks = False
            if not existing_tasks:
                # Paieškom gal jau yra sukurta šios siuntos užduotis iš maršruto.
                domain.pop(0)
                existing_placeholder_tasks = so_env.search([
                    ('placeholder_for_route_template','=',True),
                    ('name','=',so_vals['name'])
                ] + domain)
            if existing_tasks:
                existing_tasks.filtered(lambda task_rec: not task_rec.route_id).write({
                    'route_number_id': so_vals['route_number_id'],
                    'shipping_warehouse_id': so_vals['shipping_warehouse_id'],
                    'warehouse_id': so_vals['warehouse_id'],
                    'picking_location_id': so_vals['picking_location_id'],
                    'order_number_by_route': so_vals['order_number_by_route']
                })
                existing_tasks.filtered(
                    lambda task_rec: task_rec.route_id and not task_rec.replanned
                ).copy_sale_for_replanning(additional_vals={
                    'route_number_id': so_vals['route_number_id'],
                    'shipping_warehouse_id': so_vals['shipping_warehouse_id'],
                    'warehouse_id': so_vals['warehouse_id'],
                    'picking_location_id': so_vals['picking_location_id'],
                    'order_number_by_route': so_vals['order_number_by_route']
                })
            elif existing_placeholder_tasks:
                del so_vals['order_number_by_route']
                del so_vals['route_number_id']
                del so_vals['shipping_warehouse_id']
                del so_vals['picking_location_id']
                del so_vals['warehouse_id']
                del so_vals['partner_shipping_id']
                del so_vals['partner_id']
                existing_placeholder_tasks.write(so_vals)
                #     'direction': so_vals['direction'],
                #     'shipping_date': so_vals.get('shipping_date',False),
                #     'invoice_number': ['invoice_number'],
                #     'external_sale_order_id': so_vals['external_sale_order_id'],
                #     'total_weight': so_vals['total_weight'],
                # })

            else:
                task = so_env.create(so_vals)
                task.create_container_for_sale()
                task.create_transportation_order_for_sale()

    @api.multi
    def get_document_vals(self):
        doc_sql = '''
            SELECT
                sp.sender_id,
                sp.sender_address_id,
                sp.sender_posid,
                sp.buyer_id,
                sp.buyer_address_id,
                sp.buyer_posid,
                sp.packet_date,
                case 
                    WHEN string_agg(spd.external_document_id, ', ') is not null THEN string_agg(spd.external_document_id, ', ')
                    WHEN string_agg(spd.external_document_id, ', ') is null THEN sp.internal_order_number
                END,
                sl.id,
                sp.external_package_id,
                sp.picking_warehouse_id,
                sp.owner_id
            FROM
                stock_package sp
                LEFT JOIN stock_package_document spd on (spd.package_id = sp.id)
                LEFT JOIN stock_location sl on (sl.code = sp.location_code)
            WHERE
                sp.id = %s
                AND sl.active = True
            GROUP BY
                sp.sender_id,
                sp.sender_address_id,
                sp.sender_posid,
                sp.buyer_id,
                sp.buyer_address_id,
                sp.buyer_posid,
                sp.packet_date,
                sp.internal_order_number,
                sl.id,
                sp.external_package_id,
                sp.picking_warehouse_id,
                sp.owner_id
        '''
        doc_where = (self.id,)
        self.env.cr.execute(doc_sql, doc_where)
        values = self.env.cr.fetchall()[0]
        return {
            'sender_id': values[0],
            'sender_address_id': values[1],
            'sender_posid': values[2],
            'buyer_id': values[3],
            'buyer_address_id': values[4],
            'buyer_posid': values[5],
            'date_invoice': values[6][:10],
            'document_create_datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
            'name': values[7],
            'picking_location_id': values[8],
            'external_invoice_id': 'FROM_PACKAGE_' + values[9],
            'picking_warehouse_id': values[10],
            'document_operation_type': 'invoice',
            'stock_package_id': self.id,
            'state': 'draft',
            'owner_id': values[11]
        }


    @api.multi
    def create_document(self):
        # Iš siuntos sukriamas dokumentas
        inv_env = self.env['account.invoice']

        for package in self:
            invoice_vals = self.get_document_vals()
            if not package.no_collection:
                collection_doc_vals = invoice_vals.copy()
                collection_doc_vals['partner_id'] = invoice_vals['sender_id']
                collection_doc_vals['partner_invoice_id'] = invoice_vals['sender_id']
                collection_doc_vals['partner_shipping_id'] = invoice_vals['sender_address_id']
                collection_doc_vals['posid'] = invoice_vals['sender_posid']
                collection_doc_vals['delivery_type'] = 'collection'
                
                del collection_doc_vals['sender_id']
                del collection_doc_vals['buyer_id']
                del collection_doc_vals['sender_address_id']
                del collection_doc_vals['buyer_address_id']
                del collection_doc_vals['sender_posid']
                del collection_doc_vals['buyer_posid']
                
                existing_collection_document = inv_env.search([
                    ('stock_package_id','=',package.id),
                    ('delivery_type','=','collection')
                ])
                if existing_collection_document:
                    existing_collection_document.write(collection_doc_vals)
                else:
                    inv_env.create(collection_doc_vals)

            if not package.no_delivery:
                delivery_doc_vals = invoice_vals.copy()
                delivery_doc_vals['partner_id'] = invoice_vals['buyer_id']
                delivery_doc_vals['partner_invoice_id'] = invoice_vals['buyer_id']
                delivery_doc_vals['partner_shipping_id'] = invoice_vals['buyer_address_id']
                delivery_doc_vals['posid'] = invoice_vals['buyer_posid']
                delivery_doc_vals['delivery_type'] = 'delivery'
                
                del delivery_doc_vals['sender_id']
                del delivery_doc_vals['buyer_id']
                del delivery_doc_vals['sender_address_id']
                del delivery_doc_vals['buyer_address_id']
                del delivery_doc_vals['sender_posid']
                del delivery_doc_vals['buyer_posid']
                
                existing_delivery_document = inv_env.search([
                    ('stock_package_id','=',package.id),
                    ('delivery_type','=','delivery')
                ])
                if existing_delivery_document:
                    existing_delivery_document.write(delivery_doc_vals)
                else:
                    inv_env.create(delivery_doc_vals)


    @api.multi
    def remove_from_system(self):
        self.sudo().unlink()
    
#     def can_delete_transportation_task(self, date_until=None):
#         if date_until is None:
#             user = self.env['res.users'].browse(self.env.uid)
#             company = user.company_id
#             days_after = company.delete_packages_after
#             today = datetime.datetime.now()
#             date_until = (today - datetime.timedelta(days=days_after)).strftime('%Y-%m-%d %H:%M:%S')        
#         if not self.packet_date < date_until:
#             return False
#         return True
            
    
    @api.model
    def cron_delete_old_packages(self):
        # Krono kviečiama funkcija ištrinanti senas siuntas
        
        user = self.env['res.users'].browse(self.env.uid)
        company = user.company_id
        log = company.log_delete_progress or False
        days_after = company.delete_packages_after
        date_field = company.get_date_field_for_removing_object(self._name)
        _logger.info('Removing old Packages (%s days old) using date field \'%s\'' % (str(days_after), date_field))

        today = datetime.now()
        date_until = today - timedelta(days=days_after)

        packages = self.search([
            (date_field,'<',date_until.strftime('%Y-%m-%d %H:%M:%S')),
        ])
        _logger.info('Removing old Packages: found %s records' % str(len(packages)))
        if log:
            all_package_count = float(len(packages))
            i = 0
            last_log = 0
        ids_to_unlink = packages.mapped('id')
        # for package in packages:
        for package_ids in [ids_to_unlink[ii:ii+50] for ii in range(0, len(ids_to_unlink), 50)]:
            # if not package.exists():
            #     continue
            try:
                # package.remove_from_system()
                # self.env.cr.commit()
                self.browse(package_ids).remove_from_system()
                self.env.cr.commit()
                if log:
                    i += 1
                    if last_log < int((i / all_package_count)*100):
                        last_log = int((i / all_package_count)*100)
                        _logger.info('Packages delete progress: %s / %s' % (str(i), str(int(all_package_count))))
            except Exception as e:
                err_note = 'Failed to delete  package(ID: %s): %s \n\n' % (str(package_ids), tools.ustr(e),)
                trb = traceback.format_exc() + '\n\n'
                _logger.info(err_note + trb)
    
    @api.multi       
    def create_transportation_task_after_package_import(self):
        # Siuntai sukuriama užduotis. Funkcija kviečiama iškart sukūrus siuntą.
        for package in self:
            if package.location_code:
                if not package.no_collection and not \
                    package.task_ids.filtered(
                        lambda task_record: task_record.delivery_type == 'collection'
                    ) \
                :
                    package.create_transportation_tasks(
                        'collect', package.location_code, package.location_code, False, ''
                    )
                if not package.no_delivery and not \
                    package.task_ids.filtered(
                        lambda task_record: task_record.delivery_type == 'delivery'
                    ) \
                :
                    package.create_transportation_tasks(
                        'deliver', package.location_code, package.location_code, False, ''
                    )

    @api.multi
    def create_account_invoice_after_package_import(self):
        # Siuntai sukuriamas dokumentas. Funkcija kviečiama iškart sukūrus siuntą.
        for package in self:
            package.create_document()

                    
class StockPackageDocumentType(models.Model):
    _name = 'stock.package.document.type'
    _description = 'Stock Package Document Type'

    name = fields.Char('Name', size=256, required=True)
    code = fields.Char('Code', size=256, required=True)
    
    _sql_constraints = [
        ('code_id_uniq', 'unique (code)', 'Document type with this code already exists')
    ]

    
class StockPackageDocument(models.Model):
    _name = 'stock.package.document'
    _description = 'Stock Package Document'
    
    _inherit = ['mail.thread']

    @api.model
    def _get_type(self):
        res = False
        type_obj = self.env['stock.package.document.type']
        types = type_obj.search([
            ('code','=',DEFAULT_PACKAGE_DOCUMENT_TYPE)
        ], limit=1)
        if types:
            res = types.id
        return res 

    package_id = fields.Many2one(
        'stock.package', 'Package', readonly=True,
        track_visibility='onchange', index=True,
        ondelete='cascade'
    )
    external_document_id = fields.Char(
        'External ID', size=64, readonly=True,
        track_visibility='onchange'
    )
    document_number = fields.Char(
        'Document Number', size=128, required=True,
        track_visibility='onchange'
    )
    document_type_id = fields.Many2one(
        'stock.package.document.type', 'Document Type',
        required=True, track_visibility='onchange', default=_get_type
    )
    acount_invoice_id = fields.Many2one(
        'account.invoice', 'Invoice', track_visibility='onchange', index=True
    )
    external_invoice_id = fields.Char(
        'External Invoice ID', size=128, readonly=True, track_visibility='onchange'
    )
    owner_id = fields.Many2one(
        'product.owner', 'Owner', readonly=True
    )
    owner_code = fields.Char("Owner Code", size=128, readonly=True)

    _sql_constraints = [
        ('external_id_uniq', 'unique (external_document_id)', 'Document with this external id already exists')
    ]
    
    _rec_name = 'document_number'
    _order = 'id desc'
    
    @api.multi
    def update_owner(self):
        ctx = self._context.copy()
        ctx['skip_owner_update'] = True
        for pack_doc in self:
            owner = pack_doc.package_id and pack_doc.package_id.owner_id or False
            owner_code = owner and owner.owner_code or ""
            if owner_code:
                pack_doc.with_context(ctx).write({
                    'owner_id': owner.id,
                    'owner_code': owner_code
                })
                
        return True
    
    @api.multi
    def write(self, vals):
        res = super(StockPackageDocument, self).write(vals)
        if 'package_id' in vals.keys():
            self.mapped('package_id').update_counts()
        if not self._context.get('skip_owner_update', False):
            self.update_owner()
        return res
    
    @api.model
    def create_document(self, vals):
        interm_obj = self.env['stock.route.integration.intermediate']
        type_obj = self.env['stock.package.document.type']
        ai_obj = self.env['account.invoice']

        document = self.search([
            ('external_document_id','=',vals['external_document_id'])
        ], limit=1)
        
        if document:
            doc_vals = {}
        else:
            doc_vals = self.default_get(self._fields)
        
        doc_vals.update(vals)
        
        if 'document_type' in doc_vals.keys():
            doc_type = type_obj.search([
                ('code','=',doc_vals['document_type'])
            ], limit=1)
            if doc_type:
                doc_vals['document_type_id'] = doc_type.id
                del doc_vals['document_type']
            else:
                raise UserError(_('Document type with code %s does not exist in the system') %doc_vals['document_type'])
        
        if doc_vals.get('external_invoice_id', False):
            invoice = ai_obj.search([
                ('external_invoice_id','=',doc_vals['external_invoice_id'])
            ], limit=1)
            if invoice:
                doc_vals['acount_invoice_id'] = invoice.id
                del doc_vals['external_invoice_id']

#                 raise UserError(_('Invoice with external ID %s does not exist in the system') %doc_vals['external_invoice_id'])
        
        if document:
            interm_obj.remove_same_values(document, doc_vals)
            if doc_vals:
                document.write(doc_vals)
            
        else:
            document = self.create(doc_vals)
        self.env.cr.commit()
        return document
    
    @api.model
    def create(self, vals):
        res = super(StockPackageDocument, self).create(vals)
        res.update_owner()
        return res
    
#Metodas kvieciamas is JS, paduodant netvarkingus domainus, o grazinami skirtingi galimi savininkai
    def get_avail_owners(self, domains, action_domain=False, action_context=False):
        normalized_domain = []
        for domain_ele in domains:
            if isinstance(domain_ele, dict):
                if domain_ele.get('__domains', False):
                    for cmplx_domain_ele in domain_ele['__domains']:
                        if len(cmplx_domain_ele) == 1:
                            normalized_domain.append(cmplx_domain_ele[0])
                        elif len(cmplx_domain_ele) == 3:
                            normalized_domain.append(cmplx_domain_ele)
                        else:
                            continue
            elif isinstance(domain_ele, list):
#                 normalized_domain.append(domain_ele[0])
                normalized_domain += domain_ele
            else:
                continue
            
        if action_domain:
            normalized_domain += action_domain

        query = self._where_calc(normalized_domain)
        from_clause, where_clause, where_clause_params = query.get_sql()
        where_str = where_clause and (" WHERE %s" % where_clause) or ''
        query_str = 'SELECT DISTINCT(owner_id) FROM stock_package_document %s ORDER BY owner_id' % where_str

        self.env.cr.execute(query_str, where_clause_params)
        res = self.env.cr.fetchall()
        owners = []
        
        for owner_id_tuple in res:
            if owner_id_tuple[0]:
                owner_id = owner_id_tuple[0]
                self.env.cr.execute('SELECT owner_code,name FROM product_owner WHERE id = %s' % owner_id)
                owner_code_sql_res = self.env.cr.fetchone()
                
                owner_code, owner_name = owner_code_sql_res
                if owner_name:
                    owner_str = "%s - %s" % (owner_code, owner_name)
                else:
                    owner_str = owner_code
                
                if (owner_code, owner_str) not in owners:
                    owners.append((owner_code, owner_str))
        
        owners = sorted(owners, key=lambda tup: tup[1])
        return owners
    
    
# class stock_package_container(osv.Model):
#     _name = 'stock.package.container'
#     _description = 'Stock Package Container'
#     
#     _inherit = ['mail.thread']
#     
#     _columns = {
#         'package_id': fields.many2one(
#             'stock.package', 'Package', track_visibility='onchange'
#         ),
#         'external_container_id': fields.char(
#             'External ID', size=64, track_visibility='onchange'
#         ),
#         'container_number': fields.char(
#             'Container Number', size=128, required=True, track_visibility='onchange'
#         ),
#         'container_weight': fields.float(
#             'Container Weight', digits=(16,2), track_visibility='onchange'
#         ),
#         'factual_container_weight': fields.float(
#             'Factual Container Weight', digits=(16,2), track_visibility='onchange'
#         ),
#         'intermediate_id': fields.many2one(
#             'stock.route.integration.intermediate', 'Created by', readobly=True
#         ),
#     }
#     
#     _sql_constraints = [
#         ('external_id_uniq', 'unique (external_container_id)', 'Packet with this external id already exists')
#     ]
#     
#     _defaults = {
#         'document_type': lambda *a: 'invoice',
#         'container_weight': lambda *a: 0.0,
#         'factual_container_weight': lambda *a: 0.0
#     }
#     
#     _rec_name = 'container_number'
#     
#     def create_container(self, cr, uid, vals, context=None):
#         interm_obj = self.env('stock.route.integration.intermediate')
#         if context is None:
#             context = {}
# 
#         ids = self.search(cr, uid, [
#             ('external_container_id','=',vals['external_container_id'])
#         ], context=context)
#         
#         if ids:
#             cont_vals = {}
#         else:
#             cont_vals = self.default_get(
#                 cr, uid, self._fields, context=context
#             )
#         
#         cont_vals.update(vals)
#         
#         if ids:
#             id = ids[0]
#             interm_obj.remove_same_values(cr, uid, id, cont_vals, 'stock.package.container', context=context)
#             if cont_vals:
#                 self.write(cr, uid, [id], cont_vals, context=context)
#                 if 'updated_document_ids' in context:
#                     context['updated_document_ids'].append((vals['external_container_id'], id))
#             
#         else:
#             cont_vals['intermediate_id'] = context.get('intermediate_id', False)
#             id = self.create(cr, uid, cont_vals, context=context)
#             if 'created_container_ids' in context:
#                 context['created_container_ids'].append((cont_vals['external_container_id'], id))
#         cr.commit()       
#         return id
#     
#     def create(self, cr, uid, vals, context=None):
#         if 'state' not in vals.keys():
#             vals['state'] = 'draft'
#         return super(stock_package_container, self).create(
#             cr, uid, vals, context=context
#         )
    
class StockRouteIntegrationIntermediateLinkNew(models.Model):
    _name = 'stock.route.integration.missing_links.new'
    _description = 'Missing Links'
    
    @api.model
    def _get_types(self):
        return [
            ('task_creation_from_package','Package/Task'),
            ('task_update_from_route','Route/Task'),
            ('task_for_packing_insert_into_route','Route/Package')
        ]
    
    type = fields.Selection(_get_types, 'Type', readonly=True)
    object_from_external_id = fields.Char('From External ID', size=1024, readonly=True)
    object_to_external_id = fields.Char('To External ID', size=1024, readonly=True)
    stock_number_id = fields.Integer('Stock Number Id')
    delivery_type = fields.Char('Delivery Type', size=32)
    shipping_warehouse = fields.Char('Shipping Warehouse', size=16)
    picking_warehouse = fields.Char('Picking Warehouse', size=16)
    order_number_by_route = fields.Char('Client No in the Route', size=16)
    values = fields.Text('Values')
    order_number = fields.Char('Order Number', size=64, index=True)

    @api.model_cr
    def init(self):
        cr = self.env.cr
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_route_integration_missing_links2_to_index',))
        if not cr.fetchone():
            cr.execute(
                'CREATE INDEX stock_route_integration_missing_links2_to_index ON stock_route_integration_missing_links_new (type, object_to_external_id)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_route_integration_missing_links2_from_index',))
        if not cr.fetchone():
            cr.execute(
                'CREATE INDEX stock_route_integration_missing_links2_from_index ON stock_route_integration_missing_links_new (type, object_from_external_id)')

    @api.model
    def create_missing_task_information(self, id_from=None, id_to=None, vals={}):
        domain = self.get_domain(id_to, 'task_update_from_route')
        links = self.search(domain)
        if links:
            links.write({'values': json.dumps(vals, indent=2)})
        else:
            return self.create({
                'object_to_external_id': id_to,
                'type': 'task_update_from_route',
                'values': json.dumps(vals, indent=2)
            })

    @api.multi
    def remove_external_id(self, external_id, type=''):
        # Pašalina jau apdorotą išorinį ID
        for link in self:
            external_ids = link.object_from_external_id.split(',')
            external_ids.remove(external_id)
            if external_ids:
                link.write({'object_from_external_id': ','.join(external_ids)})
            else:
                link.unlink()
    
    
    @api.model
    def get_domain(self, external_id, type='task_creation_from_package'):
        domain = []
        if type == 'task_creation_from_package':
            domain.append(('type','=','task_creation_from_package'))
            domain.append(('object_from_external_id','like','%'+external_id+'%'))
        elif type == 'task_update_from_route':
            domain.append(('type','=','task_update_from_route'))
            domain.append(('object_to_external_id','=',external_id))

        return domain
    
    
    @api.model
    def create_missing_package_information(self, external_ids, stock_number_id, delivery_type,
        shipping_warehouse_id, picking_warehouse_id, order_number_by_route
    ):
        # Iškviečiama kai importuojamas maršrutas perduoda su siunta susijusią informaciją
        # bet ta siunta dar nėra sukurta. Tada susikuria objektas išsaugantis tą susijusią 
        # informaciją.
        
        same_links = self.search([
            ('type','=','task_creation_from_package'),
            ('stock_number_id','=',stock_number_id),
            ('delivery_type','=',delivery_type),
            ('shipping_warehouse','=',shipping_warehouse_id),
            ('picking_warehouse','=',picking_warehouse_id),
            ('order_number_by_route','=',order_number_by_route)
        ])
        
        for external_id in external_ids:
            domain = self.get_domain(external_id, type='task_creation_from_package')
            if same_links:
                domain.append(('id','!=',same_links[0].id))
            links = self.search(domain)
            if links:
                links.remove_external_id(external_id)
                
        if same_links:
            same_link = same_links[0]
            same_link_external_ids = same_link.object_from_external_id.split(',')
            same_link_external_ids = same_link_external_ids + external_ids
            same_link.write({
                'object_from_external_id': ','.join(list(set(same_link_external_ids)))
            })
            return same_link
        else:
            return self.create({
                'object_from_external_id': ','.join(external_ids),
                'type': 'task_creation_from_package',
                'stock_number_id': stock_number_id,
                'delivery_type': delivery_type,
                'shipping_warehouse': shipping_warehouse_id,
                'picking_warehouse': picking_warehouse_id,
                'order_number_by_route': order_number_by_route
            })

    @api.multi
    def read_json_values(self):
        str_values = self.values
        if not str_values:
            return {}
        try:
            vals_dict = json.loads(str_values)
        except:
            json_acceptable_string = str_values.replace("'", "\"")
            vals_dict = json.loads(json_acceptable_string)
        return vals_dict

    @api.model
    def check_for_missing_links(self, external_id, link_type='task_creation_from_package'):
        # Kai sukuriama siunta reikia patikrinti ar nebuvo jai ankščiau perduota susijusios informacijos
        # jeigu buvo tada susijusi informacija apdorojama
        
        domain = self.get_domain(external_id, type=link_type)
        links = self.search(domain)
        if links:
            link = links[0]
            if link_type == 'task_creation_from_package':
                package_env = self.env['stock.package']
                package = package_env.search([('external_package_id','=',external_id)])[0]
                package.with_context(skip_missing_links=True).create_transportation_tasks(
                    link.delivery_type, link.shipping_warehouse, link.picking_warehouse,
                    link.stock_number_id, link.order_number_by_route
                )
                link.remove_external_id(external_id)
            elif link_type == 'task_update_from_route':

                str_values = link.values
                try:
                    vals_dict = json.loads(str_values)
                except:
                    json_acceptable_string = str_values.replace("'", "\"")
                    vals_dict = json.loads(json_acceptable_string)
                self.env['sale.order'].search([
                    ('external_sale_order_id','=',external_id),
                    ('replanned','=',False)
                ]).write(vals_dict)
                link.unlink()

    @api.model
    def create_or_update_route_packing_transfer_info(self, values, route_number=False):
        order_no = values['order_no']
        active = values.get('active', 'Y') == 'Y'
        link = self.search([
            ('order_number','=',order_no),
            ('type','=','task_for_packing_insert_into_route')
        ], limit=1)
        if link and not active:
            link.unlink()
            return {}
        if 'external_packet_ids' in values.keys():
            if not isinstance(values['external_packet_ids'], list):
                values['external_packet_ids'] = [values['external_packet_ids']]
        if link:
            stock_number_id = route_number and route_number.id or link.stock_number_id
            link_vals = link.read_json_values()
            if 'external_packet_ids' in link_vals.keys():
                if not isinstance(link_vals['external_packet_ids'], list):
                    link_vals['external_packet_ids'] = [link_vals['external_packet_ids']]
                if 'external_packet_ids' in values.keys():
                    for ext_packet_id in link_vals['external_packet_ids']:
                        if ext_packet_id not in values['external_packet_ids']:
                            values['external_packet_ids'].append(ext_packet_id)
                    
            link_vals.update(values)
            link.write({
                'stock_number_id': stock_number_id,
                'order_number': order_no,
                'values': json.dumps(link_vals, indent=2)
            })
        else:
            stock_number_id = route_number and route_number.id or 0
            link_vals = values
            self.create({
                'stock_number_id': stock_number_id,
                'values': json.dumps(link_vals, indent=2),
                'order_number': order_no,
                'type': 'task_for_packing_insert_into_route'
            })
        link_vals['stock_number_id'] = stock_number_id
        return link_vals


class StockRouteIntegrationIntermediateLink(models.Model):
    _name = 'stock.route.integration.intermediate.missing_links'
    _description = 'Intermediate table for importing routes'

    object_from = fields.Selection([
        ('stock.route','Route'),
        ('account.invoice.line','Invoice Line'),
        ('stock.package','Package'),
        ('sale.order','Sale')
    ], 'From Object', readonly=True)
    object_to = fields.Selection([
        ('sale.order','Sale'),
        ('sale.order.line','Sale Line'),
        ('stock.route','Route'),
        ('stock.warehouse','Warehouse'),
        ('stock.location','Location'),
        ('stock.package','Package'),
        ('stock.route.number','Route Number'),
    ], 'To Object', readonly=True)
    field = fields.Char('Field', size=128, readonly=True)
    exernal_id_from = fields.Char('From External ID', size=128, readonly=True)
    exernal_id_to = fields.Char('To External ID', size=128, readonly=True)
    
    @api.model
    def remove_link_if_exists(self, sale_ext_id, route_ext_id, obj='sale.order'):
        self.env.cr.execute("""
            DELETE FROM
                stock_route_integration_intermediate_missing_links
            WHERE
                object_from = 'stock.route'
                and object_to = '%s'
                and exernal_id_to = '%s'
                and exernal_id_from != '%s'
            """ % (obj, sale_ext_id, route_ext_id))
        return True

    @api.model_cr
    def init(self):
        cr = self.env.cr
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_route_integration_intermediate_missing_links_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX stock_route_integration_intermediate_missing_links_index ON stock_route_integration_intermediate_missing_links (object_from, object_to, exernal_id_from, exernal_id_to)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_route_integration_intermediate_missing_links_from_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX stock_route_integration_intermediate_missing_links_from_index ON stock_route_integration_intermediate_missing_links (object_from, exernal_id_from)')
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('stock_route_integration_intermediate_missing_links_to_index',))
        if not cr.fetchone():
            cr.execute('CREATE INDEX stock_route_integration_intermediate_missing_links_to_index ON stock_route_integration_intermediate_missing_links (object_to, exernal_id_to)')

    @api.model
    def get_links(self):
        return {
            ('stock.route', 'sale.order', 'sale_ids'): {
                'type': 'many2many',
                'id_field_to': 'external_sale_order_id',
                'id_field_from': 'external_route_id'
            },
            ('account.invoice.line', 'sale.order.line', 'sale_order_line_ids'): {
                'type': 'many2many',
                'id_field_to': 'external_sale_order_line_id',
                'id_field_from': 'external_invoice_line_id'
            },
            ('stock.package', 'stock.route', 'collection_route_id'): {
                'type': 'many2one',
                'id_field_to': 'external_route_id',
                'id_field_from': 'external_package_id'
            },
            ('stock.route', 'stock.package', 'delivery_package_ids'): {
                'type': 'many2many',
                'id_field_to': 'external_package_id',
                'id_field_from': 'external_route_id'
            },
            ('sale.order', 'stock.warehouse', 'shipping_warehouse_id'): {
                'type': 'many2one',
                'id_field_to': 'id',
                'id_field_from': 'external_sale_order_id',
                'to_int': True,
            },
            ('sale.order', 'stock.warehouse', 'warehouse_id'): {
                'type': 'many2one',
                'id_field_to': 'id',
                'id_field_from': 'external_sale_order_id',
                'to_int': True,
            },
            ('sale.order', 'stock.location', 'picking_location_id'): {
                'type': 'many2one',
                'id_field_to': 'id',
                'id_field_from': 'external_sale_order_id',
                'to_int': True,
            },
            ('sale.order', 'stock.route.number', 'route_number_id'): {
                'type': 'many2one',
                'id_field_to': 'id',
                'id_field_from': 'external_sale_order_id',
                'to_int': True,
            },
        }
    
    @api.multi
    def connect_from_sale_order(self):
        # kai sukuriamas pardavimas, kuriam jau buvo sukurti trukstami ryšiai į sandėlius
        # juos reikia apdoroti kitaip ne paprastus laukus nes atitinkamai nuo sandėliu turi kurtis
        # nauji pardavimai (transporto užduotys)
#         link = self[0]
#         
#             
#         warehouse_id = False
#         ship_sale_wh_link = self.search([
#             ('object_from','=','sale.order'),
#             ('object_to','=','stock.warehouse'),
#             ('exernal_id_from','=',link.exernal_id_from),
#             ('field','=','shipping_warehouse_id')
#         ])
#         shipping_warehouse_id = int(ship_sale_wh_link[0].exernal_id_to)
#         sale_wh_link = self.search([
#             ('object_from','=','sale.order'),
#             ('object_to','=','stock.warehouse'),
#             ('exernal_id_from','=',link.exernal_id_from),
#             ('field','=','warehouse_id')
#         ])
#         if sale_wh_link:
#             warehouse_id = int(sale_wh_link[0].exernal_id_to)
#             ship_sale_wh_link = ship_sale_wh_link + sale_wh_link
#         sale = self.env['sale.order'].search([('external_sale_order_id','=',link.exernal_id_from)])
#         sale.continu e_chain(shipping_warehouse_id, warehouse_id)
        return True

    @api.multi
    def connect(self):
        if not self.exists():
            return True
        context = self.env.context or {}
        ctx = context.copy()
        ctx['remove_sales_old_out_route'] = True
        link_objects = self.get_links()

        to_obj = self.env[self.object_to]
        from_obj = self.env[self.object_from]
        field = self.field
        link_between = (self.object_from, self.object_to, field)
        to = self.exernal_id_to
        if link_objects[link_between].get('to_int', False):
            to = int(to)
        to_record = to_obj.search([
            (link_objects[link_between]['id_field_to'],'=',to)
        ], limit=1)
        if to_record:
            from_records = from_obj.search([
                (link_objects[link_between]['id_field_from'],'=',self.exernal_id_from)
            ])
            if from_records:
                if link_objects[link_between]['type'] == 'many2many':
                    from_records.with_context(ctx).write({
                        field: [(4, to_record.id)]
                    })
                elif link_objects[link_between]['type'] == 'many2one':
                    from_records.write({
                        field: to_record.id
                    })
        return True

    @api.model
    def check_for_missing_links(self, just_created_object, external_id):
        context = self.env.context or {}
        ctx = context.copy()
        ctx2 = context.copy()
        ctx2['removeall_if_bad'] = True
        links = self.search([
            ('object_to','=',just_created_object),
            ('exernal_id_to','=',external_id)
        ])
        links += self.search([
            ('object_from','=',just_created_object),
            ('exernal_id_from','=',external_id)
        ])
        if just_created_object == 'sale.order' and len(links) > 1:
            ctx['do_not_check_route_order'] = True
            ctx['removeall_if_bad'] = True
            
        for link in sorted(links, key=lambda x: x.id):
            link.with_context(ctx).connect()
        self.search([('id','in',links.mapped('id'))]).unlink()
        return True

    @api.model
    def create(self, vals):
        if 'field' not in vals.keys() and 'object_from' in vals.keys() and 'object_to' in vals.keys():
            link_objects = self.get_links()
            for key in link_objects.keys():
                if vals['object_from'] == key[0] and vals['object_to'] == key[1]:
                    vals['field'] = key[2]
                    break
        if 'object_to' not in vals.keys() and 'field' in vals.keys() and 'object_from' in vals.keys():
            link_objects = self.get_links()
            for key in link_objects.keys():
                if vals['object_from'] == key[0] and vals['field'] == key[2]:
                    vals['object_to'] = key[1]
                    break
        return super(StockRouteIntegrationIntermediateLink, self).create(vals)

    
class StockMoveReconcile(models.Model):
    _name = 'stock.move.reconcile'
    _description = 'Stock Move Reconcile'

    _rec_name = 'quantity'

    move_from_id = fields.Many2one(
        'stock.move', 'Reconcile From', required=True,
        ondelete='cascade',
    )
    move_to_id = fields.Many2one(
        'stock.move', 'Reconcile To', required=True,
        ondelete='cascade',
    )
    quantity = fields.Integer('Quantity', required=True)

    _sql_constraints = [
        ('from_to_uniq', 'unique (move_from_id, move_to_id)', 
            'Two stock moves can be reconciled only once.'
        )
    ]

    @api.multi
    def check_reconciliation(self):
        context = self.env.context or {}
        if context.get('dont_check_reconciliation', False):
            return True
        check_context = context.copy()
        check_context['show_constraint_message'] = True
        
        for reconciliation in self:
            if reconciliation.move_from_id.location_dest_id.id != reconciliation.move_to_id.location_id.id:
                raise UserError(
                    _('You can\'t reconcile move(ID: %s) with destination location %s to move(ID: %s) with source location %s') % (
                        str(reconciliation.move_from_id.id), str(reconciliation.move_from_id.location_dest_id.name), 
                        str(reconciliation.move_to_id.id), str(reconciliation.move_to_id.location_id.name)
                    )
                )
            reconciliation.move_to_id.with_context(check_context)._check_reconcile_from()
            reconciliation.move_from_id.with_context(check_context)._check_reconcile_to()
            ctx_dont = context.copy()
            ctx_dont['dont_check_reconciliation'] = True
            reconciliation.move_from_id.with_context(ctx_dont).calculate_reconcilations()
        return True
    
    @api.model
    def create(self, vals):
        reconciliation = super(StockMoveReconcile, self).create(vals)
        reconciliation.check_reconciliation()
        return reconciliation
    
    @api.multi
    def write(self, vals):
        res = super(StockMoveReconcile, self).write(vals)
        self.check_reconciliation()
        return res
    
    @api.multi
    def unlink(self):
        for reconciliation in self:
            reconciliation.move_from_id.calculate_reconcilations()
        return super(StockMoveReconcile, self).unlink()

    @api.model
    def reconcile(self, move_from_id, move_to_id, qty=0):
        move_obj = self.env['stock.move']
        if qty <= 0:
            move_from = move_obj.browse( move_from_id, )
            move_to = move_obj.browse(move_to_id)
            needed_qty = move_to.product_uom_qty - move_to.get_reconciled_from_qty()
            available_qty = move_from.product_uom_qty - move_from.get_reconciled_to_qty()
            qty = min([needed_qty, available_qty])
        vals = {
            'move_from_id': move_from_id,
            'move_to_id': move_to_id,
            'quantity': qty
        }
        reconciliation = self.create(vals)
        return reconciliation

class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'
    
    certificate_id = fields.Many2one('product.certificate', "Certificate")
    expiry_date = fields.Date("Expiry Date")
    serial_ids = fields.One2many('product.stock.serial', 'lot_id', "Serial Numbers")
    
    @api.model
    def create(self, vals):
        context = self._context
        if not context.get('stop_certificate_linking', False):
            certificate_env = self.env['product.certificate']
            res = super(StockProductionLot, self).create(vals)
            if vals.get('certificate_id', False):
                certificate = certificate_env.browse(vals['certificate_id'])
                certificate.write({
                    'prod_lot_ids': [(4,res.id)]
                })
        else:
            res = super(StockProductionLot, self).create(vals)
        return res
    
    @api.multi  
    def write(self, vals):
        context = self._context
        if not context.get('stop_certificate_linking', False):
            for lot in self:
                certificate_env = self.env['product.certificate']
                if vals.get('certificate_id', False):
                    old_certificate = lot.certificate_id
                    old_certificate.write({
                        'prod_lot_ids': [(3,lot.id)]
                    })
                    certificate = certificate_env.browse(vals['certificate_id'])
                    certificate.write({
                        'prod_lot_ids': [(4,lot.id)]
                    })
        return super(StockProductionLot, self).write(vals)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

class StockGate(models.Model):
    _name = 'stock.gate'
    
    name = fields.Char("Gate", size=128)
    
    
class StockGateSettings(models.Model):
    _name = 'stock.gate.settings'
    
    gate_id = fields.Many2one('stock.gate', 'Gate', required=True)
    partner_address_id = fields.Many2one('res.partner', 'POSID')
    location_id = fields.Many2one('stock.location', 'Location')
    transport_type_id = fields.Many2one('transport.type', 'Transport Type', required=True)
    
    @api.model
    def find_suitable_gate(self, transport_type_id=False, location_id=False, partner_address_id=False):
        domain = [('location_id', '=', location_id)]
        setting = self.search(domain, limit=1) or False
        if setting:
            domain.append(('transport_type_id','=',transport_type_id))
            temp_setting = self.search(domain, limit=1)
            if temp_setting:
                setting = temp_setting
                domain.append(('partner_address_id','=',partner_address_id))
                temp_setting = self.search(domain, limit=1)
                if temp_setting:
                    setting = temp_setting
                    
        return setting and setting.gate_id or False
    
    
class StockRouteContainer(models.Model):
    _name = 'stock.route.container'
    _description = 'Container Status for Route'
    
    route_id = fields.Many2one('stock.route', 'Route', ondelete='cascade', readonly=True, index=True)
    container_id = fields.Many2one('account.invoice.container', 'Container', ondelete='cascade', readonly=True, index=True)
    state = fields.Selection([
        ('none','None'),
        ('received','Received'),
        ('not_received','Not Received')
    ], 'State', readonly=True, default='none')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)
    current = fields.Boolean('Currnet', readonly=True, default=False, help='Shows if line is from active Route')
#     transportation_task_id = new_api_fields.Many2one('sale.order', 'Transportation Task', readonly=True)
    
    @api.multi
    def update_current_value(self):
        # Vienu metu gali būti daug eilučių su tuo pačiu konteineriu tik skirtingais maršrutai.
        # Taip atsitinka jeigu konteineris keliauja per daug sandėlių. Bet betkokiu atveju,
        # atliekant skaičiavimus bus reikalinga tik viena eilutė ir jos būsena - t.y. einamojo maršruto eilutė.
        # Laukelis current ir parodys, kuri eilutė priklauso einamąjam maršrutui.
        # Ši funkcija eilutei apskaičiuoja current laukelio reikšmę. 
        
        for line in self:
            current = False
            if line.state in ['none', 'not_received'] and line.route_id.state == 'released':
                current = True
                older_lines = self.search([
                    ('container_id','=',line.container_id.id),
                    ('id','!=',line.id),
                    ('current','=',True)
                ])
                for older_line in older_lines:
                    if older_line.state == 'received':
                        older_line.write({'current': False})
                    elif older_line.get_transportation_task().replanned:
                        older_line.write({'current': False})
                    elif older_line.get_transportation_task().delivery_type == 'collection' \
                        and line.get_transportation_task().delivery_type == 'delivery' \
                    :
                        older_line.write({'current': False})
                    elif line.get_transportation_task().replanned:
                        current = False
                    else:
                        raise UserError('KLAIDA DEL konteineriu eilutės marsrutas %s konteineris %s' % (str(older_line.route_id.id), str(older_line.container_id.id)))
            elif line.route_id.state in ['released', 'closed'] and line.state == 'received':
                if not self.search([
                    ('container_id','=',line.container_id.id),
                    ('id','!=',line.id),
                    ('current','=',True)
                ]):
                    continue
            elif line.route_id.state in ['closed'] and line.state == 'not_received':
                if not self.search([
                    ('container_id','=',line.container_id.id),
                    ('id','!=',line.id),
                    ('current','=',True)
                ]):
                    continue
            if line.current != current:
                line.write({'current': current})
    
    @api.multi
    def write(self, vals):
        if 'state' in vals.keys():
            vals['warehouse_id'] = self.env['res.users'].browse(self.env.uid).default_warehouse_id.id
            
        res = super(StockRouteContainer, self).write(vals)
        if 'state' in vals.keys():
            containers = self.mapped('container_id')
            self.mapped('route_id').mapped('sale_ids').filtered(
                lambda sale_rec: sale_rec.container_ids & containers
            ).with_context(skip_received_wh_calc=True).update_task_receive_status()
            self.env.clear()
            self.mapped('route_id').update_received_warehouse_ids_text()
            self.mapped('container_id').update_not_received_filter()
            self.update_current_value()
            
            self.mapped('route_id').close_route_if_needed()
        return res
    
    @api.multi
    def get_transportation_task(self):
        # Grąžina susijusio maršruto(route_id) tranportavimo užduotį, 
        # kuriai yra priskirtas susijęs konteineris(container_id).

        task = self.route_id.with_context({}).sale_ids.filtered(
            lambda task_record: self.container_id in task_record.container_ids
        )
        return task


class StockFleet(models.Model):
    _name = 'stock.fleet'
    _description = "Trucks and trailers"
    _order = 'number'
    _rec_name = 'number'
    
    def get_type_selection(self):
        return [
            ('truck', _("Truck")),
            ('trailer', _("Trailer")),
        ]
    
    number = fields.Char("Plate Number")
    type = fields.Selection(get_type_selection, "Fleet Type")
    carrier_id = fields.Many2one('res.partner', "Carrier", domain=[('carrier','=',True)])
    active = fields.Boolean('Active', default=True)
    capacity = fields.Integer('Capacity')
    odometer_reading = fields.Integer('Odometer Reading')
    run_hours = fields.Integer('Run Hours')
    id_version = fields.Char('POD Version', size=128, readonly=True)
    id_external = fields.Char("External ID", required=True)

    @api.model
    def get_id_by_number(self, number, fleet_type):
        if not number:
            return None
        fleet = self.search([
            ('type','=',fleet_type),
            ('number','=',number),
            ('id_external','!=',False),
            ('active','=',True)
        ], limit=1)

        return fleet and fleet.id_external or number


    @api.model
    def create(self, vals):
        vals['id_version'] = get_local_time_timestamp()
        return super(StockFleet, self).create(vals)
    
    @api.multi
    def write(self, vals):
        for fleet in self:
            vals['id_version'] = get_local_time_timestamp()
            res = super(StockFleet, fleet).write(vals)
        return res
    
    @api.model
    def get_pod_domain(self, obj):
        return []
    
    
    @api.multi
    def to_dict_for_pod_integration(self, obj):
        vals = {
            'fleetId': self.number or '',
            'fleetType': self.type,
            'registrationPlate': self.number or '',
            'carrierId': self.carrier_id and self.carrier_id.ref or self.carrier_id.id_carrier or self.carrier_id.external_customer_id or '',
            'active': self.active,
            'capacity': self.capacity or 0,
            'runHours': self.run_hours or 0,
            'odometerReading': self.odometer_reading,
            'id_version': self.id_version,
        }
        return vals
    
    @api.model
    def set_iceberg_data(self, data):
        obj = data['obj']
        
        id_external = data.get('truckId', False)\
         or data.get('trailerId', False) or data.get('fleetId', False)
        
        #Jei atsiuncia, kad istrinta, me snetrinam, o padarom neaktyviu 
        if data.get('deleted', False) or ('active' in data.keys() and not data['active']):
            active = False
        else:
            active = True
        
        vals = {
            'type': obj != 'fleet' and obj or data.get('type', 'truck'),
            'active': active,
        }
        if data.get('carrierId', False):
            partner_env = self.env['res.partner']
            carrier = partner_env.get_partner_by_carrier_id(data['carrierId'])
            # carrier = partner_env.search([
            #     ('carrier','=',True),
            #     ('external_customer_id','=',data['carrierId'])
            # ], limit=1)
            vals['carrier_id'] = carrier and carrier.id or False
        if data.get('capacity', False):
            vals['capacity'] = data['capacity']
        if data.get('odometerReading', False):
            vals['odometer_reading'] = data['odometerReading']
        if data.get('runHours', False):
            vals['run_hours'] = data['runHours']
        if data.get('registrationPlate', False):
            vals['number'] = data['registrationPlate']

        fleet = self.search([
            ('id_external','=',id_external),
            ('type','=',vals['type'])
        ])
        if fleet:
            fleet.write(vals)
            res = _("Fleet was updated successfully")
        else:
            vals['id_external'] = id_external
            self.create(vals)    
            res = _("Fleet was created successfully")
            
        return res