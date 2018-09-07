# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api, SUPERUSER_ID, _
import operator
from .tools.view_validation import valid_view
from lxml import etree
from odoo.tools.safe_eval import safe_eval
import ast
from functools import partial
from odoo.exceptions import ValidationError
from .stock import utc_str_to_local_str
import logging
import time
from pypika.enums import JoinType
from pypika import  Table, Query

_logger = logging.getLogger(__name__)

USE_BLS_REPORT_SERVER_FOR_REPORTS = [
    'config_sanitex_delivery.product_packing',
    'config_sanitex_delivery.stock_packing_report',
    'config_sanitex_delivery.drivers_packing_transfer_act',
    'config_sanitex_delivery.tare_to_driver_act',
    'config_sanitex_delivery.client_packing_from_picking',
    'config_sanitex_delivery.packing_return_act',
    'config_sanitex_delivery.driver_return_act'
]

ATTRS_WITH_FIELD_NAMES = {
    'context',
    'domain',
    'decoration-bf',
    'decoration-it',
    'decoration-danger',
    'decoration-info',
    'decoration-muted',
    'decoration-primary',
    'decoration-success',
    'decoration-warning',
    'background-decoration-success',
}

class IrModel(models.Model):
    _inherit = 'ir.model'

    @api.model
    def get_name_of_model_by_field(self, model_name, field_name, field_name2):
        model = self.search([('model','=',model_name)])
        if not model:
            model = self.search([('model','=',model_name.replace('_','.'))])

        field = self.env['ir.model.fields'].search([
            ('model_id','=',model.id),
            ('name','=',field_name)
        ])
        model_env = self.env[field.relation]
        if model_env._inherits:
            inherit_model = self.search([('model','=',list(model_env._inherits.keys())[0])])

            field2 = self.env['ir.model.fields'].search([
                ('model_id', '=', inherit_model.id),
                ('name', '=', field_name2)
            ])
            if field2 and (inherit_model.model, field_name2) != ('product.template', 'default_code'):
                return inherit_model.model, model_env._inherits[inherit_model.model]
        return self.env[field.relation]._table or field.relation.replace('.','_'), field_name2

    @api.model
    def _is_datetime_field(self, table_name, field_name):
        model_name = table_name.split('"')[1]
        model = self.search([('model','=like',model_name)])
        field = self.env['ir.model.fields'].search([
            ('model_id', '=', model.id),
            ('name', '=', field_name)
        ])
        if field.ttype == 'datetime':
            return True
        return False

    @api.model
    def export_rows_with_psql(self, fields, records):
        main_table = Table(records._name.replace('.','_'), alias='main1table')
        joined_tables = []
        selects = []
        join = Query.from_(main_table)
        i = 0
        datetime_fields = []
        for field_path in fields:
            field_path_copy = field_path[:]
            table_to_join = main_table
            original_table_name = records._name
            if len(field_path_copy) > 1:
                while len(field_path_copy) > 1:
                    i += 1
                    first_field = field_path_copy[0]
                    second_field = field_path_copy[1]
                    table_name, next_field = self.get_name_of_model_by_field(original_table_name, first_field, second_field)
                    if next_field != second_field:
                        field_path_copy.insert(1, next_field)
                        continue
                    alias = first_field
                    new_table = Table(table_name, alias=alias)
                    if alias+'.'+table_name not in joined_tables:
                        join = join.join(new_table, how=JoinType.left).on(new_table.field('id')==table_to_join.field(first_field))
                        joined_tables.append(alias+'.'+table_name)
                    table_to_join = new_table
                    field_path_copy.pop(0)
                    original_table_name = table_name
            select_field = field_path_copy.pop()
            if self._is_datetime_field(str(table_to_join), select_field):
                datetime_fields.append(str(table_to_join).split(' ')[-1] + '."' + select_field + '"')
            selects.append(table_to_join.field(select_field))
        q = join.select(*selects).where(main_table.id.isin(records._ids))
        q = str(q)
        for datetime_field in datetime_fields:
            q = q.replace(datetime_field, datetime_field + " at time zone 'utc' AT TIME ZONE 'Europe/Vilnius'")

        if records._order:
            q = q +  ' order by '
            order_str_list = []
            for order_field in records._order.split(','):
                order_str = '"main1table"."' +  order_field.strip().split(' ')[0] + '"'
                if len(order_field.strip().split(' ')) > 1:
                    order_str = order_str + ' ' + order_field.strip().split(' ')[1]
                order_str_list.append(order_str)
            q = q + ', '.join(order_str_list)
        _logger.info('EXPORT SQL: %s' % q)
        self.env.cr.execute(q)
        result = self.env.cr.fetchall()
        return result


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    def _apply_group(self, model, node, modifiers, fields):
        # užklota funkcija kad naudotojas galėtų matyti grupes naudotojo vaizde.
        # tas kurias jam yra priskirtos.

        off_invisible = False
        on_invisible = False
        if model == 'res.users' and self.env.uid != SUPERUSER_ID:
            if node.tag == 'field' and node.get('name'):
                # groups = node.get('groups')
                # if 'base.group_no_one' in groups.split(',') or True:
                field_name = node.get('name')
                if 'in_group_' in field_name:
                    try:
                        group_id = field_name.split('in_group_')[1]
                        group = self.env['res.groups'].sudo().browse(int(group_id))
                        if self.env.uid in group.users.mapped('id'):
                            off_invisible = True
                        else:
                            on_invisible = True
                    except:
                        raise
                        pass
            # elif node.tag == 'field' and node.get('name'):
            #     field_name = node.get('name')
                elif 'sel_groups_' in field_name:
                    try:
                        group_ids = field_name.split('sel_groups_')[1]
                        for group_id in group_ids.split('_'):
                            group = self.env['res.groups'].sudo().browse(int(group_id))
                            if self.env.uid in group.users.mapped('id'):
                                break
                        else:
                            on_invisible = True
                    except:
                        pass

        res = super(IrUiView, self)._apply_group(model, node, modifiers, fields)
        if off_invisible:
            node.set('invisible', '0')
        if on_invisible:
            node.set('invisible', '1')
        return res
    
    
#    Uzklota, kad imtu view validartion'a is sanitex modulio, o ten butu galima pakeisti view'u taisykles
    @api.constrains('arch_db')
    def _check_xml(self):
        # Sanity checks: the view should not break anything upon rendering!
        # Any exception raised below will cause a transaction rollback.
        self = self.with_context(check_field_names=True)
        for view in self:
            view_arch = etree.fromstring(view.arch.encode('utf-8'))
            view._valid_inheritance(view_arch)
            view_def = view.read_combined(['arch'])
            view_arch_utf8 = view_def['arch']
            if view.type != 'qweb':
                view_doc = etree.fromstring(view_arch_utf8)
                # verify that all fields used are valid, etc.
                self.postprocess_and_fields(view.model, view_doc, view.id)
                # RNG-based validation is not possible anymore with 7.0 forms
                view_docs = [view_doc]
                if view_docs[0].tag == 'data':
                    # A <data> element is a wrapper for multiple root nodes
                    view_docs = view_docs[0]
                for view_arch in view_docs:
                    if not valid_view(view_arch):
                        raise ValidationError(_('Invalid view definition'))
        return True
    
    #perklota, kad butu galima prideti naujus view'o attributus kuriem rgali reiketi paskiaciuoti lauka pagal REF
    def get_attrs_field_names(self, arch):
        """ Retrieve the field names appearing in context, domain and attrs, and
            return a list of triples ``(field_name, attr_name, attr_value)``.
        """
        symbols = self.get_attrs_symbols() | {None}
        result = []

        def get_name(node):
            """ return the name from an AST node, or None """
            if isinstance(node, ast.Name):
                return node.id

        def get_subname(get, node):
            """ return the subfield name from an AST node, or None """
            if isinstance(node, ast.Attribute) and get(node.value) == 'parent':
                return node.attr

        def process_expr(expr, get, key, val):
            """ parse `expr` and collect triples """
            for node in ast.walk(ast.parse(expr.strip(), mode='eval')):
                name = get(node)
                if name not in symbols:
                    result.append((name, key, val))

        def process_attrs(expr, get, key, val):
            """ parse `expr` and collect field names in lhs of conditions. """
            for domain in safe_eval(expr).values():
                if not isinstance(domain, list):
                    continue
                for arg in domain:
                    if isinstance(arg, (tuple, list)):
                        process_expr(str(arg[0]), get, key, expr)

        def process(node, get=get_name):
            """ traverse `node` and collect triples """
            for key, val in node.items():
                if not val:
                    continue
                if key in ATTRS_WITH_FIELD_NAMES:
                    process_expr(val, get, key, val)
                elif key == 'attrs':
                    process_attrs(val, get, key, val)
            if node.tag == 'field':
                # retrieve subfields of 'parent'
                get = partial(get_subname, get)
            for child in node:
                process(child, get)

        process(arch)
        return result


class IrActReport_xml(models.Model):
    _inherit = 'ir.actions.report'
    

    copy_number = fields.Integer('Number of Copies', default=1)
    keep_log = fields.Boolean('Keep Log', default=False)
    include_in_all_reports = fields.Boolean('Include in All Repors', default=False,
        help='If cheked this report will be printed when all reports are being printed'
    )
    all_report_sequence = fields.Integer('Sequence In All Report Printing', default=1,
        help='Used to determine printing order when all reports are printed'
    )


    @api.model
    def create_not_printed_records(self):
        #vienkartinė funkcija
        route_env = self.env['stock.route']
        log_env = self.env['report.print.log']
        correction_env = self.env['stock.packing.correction']
        _logger.info('START')
        draivas_report = self.search([
            ('report_name','=','config_sanitex_delivery.product_packing')
        ], limit=1)
        driver_act_report = self.search([
            ('report_name','=','config_sanitex_delivery.drivers_packing_transfer_act')
        ], limit=1)
        driver_return_act_report = self.search([
            ('report_name','=','config_sanitex_delivery.packing_return_act')
        ], limit=1)
        client_act_report = self.search([
            ('report_name','=','config_sanitex_delivery.stock_packing_report')
        ], limit=1)
        routes = route_env.search([('state','in',['released','closed'])])
        all = len(routes)
        i = 0
        for route in routes:
            i += 1
            if not log_env.search([
                ('object','=','stock.route'),
                ('rec_id','=',route.id),
                ('report_id','=',draivas_report.id)
            ]):
                route.do_not_print_reports(['config_sanitex_delivery.product_packing'])
                log = log_env.search([
                    ('object', '=', 'stock.route'),
                    ('rec_id', '=', route.id),
                    ('report_id', '=', draivas_report.id),
                    ('number_of_copies', '=', 0)
                ])

                utc_datetime = utc_str_to_local_str(route.departure_time)
                utc_datetime_split = utc_datetime.split(' ')
                print_date = utc_datetime_split[0]
                print_time = utc_datetime_split[1]
                log.write({
                    'print_date': print_date,
                    'print_time': print_time,
                    'print_datetime': route.departure_time,
                    'warehouse_id': route.warehouse_id.id,
                    'print_user_id': route.release_user_id.id,
                })
            for picking in route.picking_ids:
                if not log_env.search([
                    ('object','=','stock.picking'),
                    ('rec_id','=',picking.id),
                    ('report_id','=',driver_act_report.id)
                ]):
                    route.do_not_print_reports(['config_sanitex_delivery.drivers_packing_transfer_act'])

                    log = log_env.search([
                        ('object', '=', 'stock.picking'),
                        ('rec_id', 'in', route.picking_ids.mapped('id')),
                        ('report_id', '=', driver_act_report.id),
                        ('number_of_copies', '=', 0)
                    ])
                    utc_datetime = utc_str_to_local_str(picking.create_date)
                    utc_datetime_split = utc_datetime.split(' ')
                    print_date = utc_datetime_split[0]
                    print_time = utc_datetime_split[1]
                    log.write({
                        'print_date': print_date,
                        'print_time': print_time,
                        'print_datetime': picking.create_date,
                        'warehouse_id': route.warehouse_id.id,
                        'print_user_id': route.release_user_id.id,
                    })

                    break
            for picking in route.returned_picking_ids:
                if not log_env.search([
                    ('object','=','stock.picking'),
                    ('rec_id','=',picking.id),
                    ('report_id','=',driver_return_act_report.id)
                ]):
                    route.do_not_print_reports(['config_sanitex_delivery.packing_return_act'])

                    log = log_env.search([
                        ('object', '=', 'stock.picking'),
                        ('rec_id', 'in', route.returned_picking_ids.mapped('id')),
                        ('report_id', '=', driver_return_act_report.id),
                        ('number_of_copies', '=', 0)
                    ])
                    utc_datetime = utc_str_to_local_str(picking.create_date)
                    utc_datetime_split = utc_datetime.split(' ')
                    print_date = utc_datetime_split[0]
                    print_time = utc_datetime_split[1]
                    log.write({
                        'print_date': print_date,
                        'print_time': print_time,
                        'print_datetime': picking.create_date,
                        'warehouse_id': route.warehouse_id.id,
                        'print_user_id': route.create_uid.id,
                    })
                    break
            for packing in route.packing_for_client_ids:
                if not log_env.search([
                    ('object','=','stock.packing'),
                    ('rec_id','=',packing.id),
                    ('report_id','=',client_act_report.id)
                ]):
                    packing.do_not_print_reports(['config_sanitex_delivery.stock_packing_report'])
                    log = log_env.search([
                        ('object', '=', 'stock.packing'),
                        ('rec_id', '=', packing.id),
                        ('report_id', '=', client_act_report.id),
                        ('number_of_copies', '=', 0)
                    ])
                    utc_datetime = utc_str_to_local_str(route.departure_time)
                    utc_datetime_split = utc_datetime.split(' ')
                    print_date = utc_datetime_split[0]
                    print_time = utc_datetime_split[1]
                    log.write({
                        'print_date': print_date,
                        'print_time': print_time,
                        'print_datetime': route.departure_time,
                        'warehouse_id': route.warehouse_id.id,
                        'print_user_id': route.release_user_id.id,
                    })
            _logger.info('ROUTE Progress: %s / %s' % (str(i), str(all)))
            self.env.cr.commit()

        corrections = correction_env.search([('state','=','done')])
        all = len(corrections)
        i = 0

        correction_return = self.search([
            ('report_name','=','config_sanitex_delivery.driver_return_act')
        ], limit=1)
        correction_transfer = self.search([
            ('report_name','=','config_sanitex_delivery.tare_to_driver_act')
        ], limit=1)

        for correction in corrections:
            i += 1
            if correction.reason == 'tare_return':
                correction_report_name = 'config_sanitex_delivery.driver_return_act'
                correction_report = correction_return
            else:
                correction_report_name = 'config_sanitex_delivery.tare_to_driver_act'
                correction_report = correction_transfer
            for picking in correction.picking_to_driver_ids + correction.picking_to_warehouse_ids:
                if not log_env.search([
                    ('object','=','stock.picking'),
                    ('rec_id','=',picking.id),
                    ('report_id','=',correction_report.id)
                ]):
                    correction.do_not_print_reports([correction_report_name])
                    log = log_env.search([
                        ('object', '=', 'stock.picking'),
                        ('rec_id', '=', picking.id),
                        ('report_id', '=', correction_report.id),
                        ('number_of_copies', '=', 0)
                    ])
                    utc_datetime = utc_str_to_local_str(picking.create_date)
                    utc_datetime_split = utc_datetime.split(' ')
                    print_date = utc_datetime_split[0]
                    print_time = utc_datetime_split[1]
                    log.write({
                        'print_date': print_date,
                        'print_time': print_time,
                        'print_datetime': picking.create_date,
                        'warehouse_id': correction.return_to_warehouse_id.id,
                        'print_user_id': route.create_uid.id,
                    })
            _logger.info('Correction Progress: %s / %s' % (str(i), str(all)))
            self.env.cr.commit()



    @api.model
    def do_not_print_report(self, record, report_name):
        self.env['report.print.log'].print_report(
            report_name, record._name, record.mapped('id'),
            False, reason='', copies=0
        )

    @api.model
    def get_copy_count(self, name):
        count = 1
        reports = self.search([('report_name','=',name)])
        if reports:
            return reports[0].copy_number and reports[0].copy_number or count
        return count
    
    @api.model
    def _get_number_of_copies(self):
        report_name = self.report_name
        if not report_name:
            return 1
        user_env = self.env['res.users']
        number_of_copies_env = self.env['number.of.copies']
        
        user = user_env.browse(self._uid)
        if user.default_warehouse_id:
            current_warehouse = user.default_warehouse_id
        elif user.default_region_id and user.default_region_id.location_id:
            current_location = user.default_region_id.location_id
            current_warehouse = current_location.get_location_warehouse_id()
        else:
            current_warehouse = False
        
        domain_part = [('report_id.report_name','=',report_name)]
        if current_warehouse:
            number_of_copies_rec = number_of_copies_env.search(
                domain_part+[('warehouse_ids','in',current_warehouse.id)],
                limit=1
            )
            if number_of_copies_rec:
                return number_of_copies_rec.number_of_copies
        
        number_of_copies_rec = number_of_copies_env.search(
            domain_part+[('warehouse_ids','=',False)], limit=1
        )
        if number_of_copies_rec:
            return number_of_copies_rec.number_of_copies
        return 1

    @api.multi
    def print_report(self, record, printer=None, reprint_reason=None, copies=None, data=None):
        rep_env = self.env['report.print.log']
        context = self.env.context or {}
        language = self.get_report_language()
        ctx_lang = 'lt_LT'
        if language == 'LV':
            ctx_lang = 'lv_LV'
        record = record.with_context(lang=ctx_lang)
        if printer is None:
            printer = self.env['res.users'].browse(self.env.uid).get_default_printer()
#         if copies is None:
#             copies = self.copy_number
        

        if self.report_name == 'config_sanitex_delivery.all_report':
            all_reports = self.search([('include_in_all_reports','=',True)], order='all_report_sequence')
            for all_report in all_reports:
                copies = all_report._get_number_of_copies()
                if record._name == 'stock.route':
                    if all_report.model == 'stock.route':
                        if record.id not in context.get('printed_routes', []):
                            all_report.print_report(record, printer, reprint_reason, copies)
                else:
                    if all_report.model == 'stock.route':
                        if record.route_id.id not in context.get('printed_routes', []):
                            all_report.print_report(record.route_id, printer, reprint_reason, copies)
                    else:
                        all_report.print_report(record, printer, reprint_reason, copies)
            if record._name == 'stock.route':
                context.get('printed_routes', []).append(record.id)
            else:
                context.get('printed_routes', []).append(record.route_id.id)
            return True
        if not record:
            return
        
        if copies is None:
            copies = self._get_number_of_copies()
            

        model_for_log = record._name
        ids_for_log = record.mapped('id')

        if self.use_report_server():
            if record._name == 'stock.route' and self.report_name == 'config_sanitex_delivery.drivers_packing_transfer_act':
                model_for_log = 'stock.picking'
                ids_for_log = record.picking_ids.mapped('id')
            if record._name == 'stock.route' and self.report_name == 'config_sanitex_delivery.packing_return_act':
                model_for_log = 'stock.picking'
                ids_for_log = record.returned_picking_ids.mapped('id')
            logs = rep_env.print_report(self.report_name, model_for_log,
                ids_for_log, printer.id,
                reason=reprint_reason or '', copies=copies
            )
            record = record.with_context(created_report_logs=logs.mapped('id'))
            if self.report_name == 'config_sanitex_delivery.product_packing':
                ctx = context.copy()
                ctx['search_by_user_sale'] = False
                ctx['search_by_user_not_received_sale'] = False
                record.fix_route_for_releasing()
                grouped_by_warehouses = record.with_context(ctx).sale_ids.group_sales_by_warehouses()
                warehouse_ids = [grouped_warehouse[1] for grouped_warehouse in grouped_by_warehouses.keys()]
                for warehouse_id in warehouse_ids:
                    report_file = record.get_pdf_report(self.report_name, warehouse_id=warehouse_id, language=language)
                    printer.linux_print(report_file, copies)
            else:
                if len(record) > 1:
                    for record1 in record:
                        report_file = record1.get_pdf_report(self.report_name, language=language)
                        printer.linux_print(report_file, copies)
                else:
                    if record._name == 'stock.route':
                        for picking in self.env['stock.picking'].browse(ids_for_log):#record.picking_ids:
                            report_file = record.with_context(picking_id_for_tare_act=picking.id).get_pdf_report(
                                self.report_name, language=language
                            )
                            printer.linux_print(report_file, copies)
                    else:
                        report_file = record.get_pdf_report(self.report_name, language=language)
                        printer.linux_print(report_file, copies)
        else:
            if record._name == 'stock.route' and self.report_name == 'config_sanitex_delivery.packing_return_act':
                model_for_log = 'stock.picking'
                ids_for_log = record.returned_picking_ids.mapped('id')
                for picking in record.returned_picking_ids:
                    report_file = printer.with_context(picking_id_for_tare_act=picking.id, lang=ctx_lang).get_report_from_odoo(
                        self.report_name, record.mapped('id'), data=data
                    )
                    printer.linux_print(report_file, copies)
            else:
                report_file = printer.with_context(lang=ctx_lang).get_report_from_odoo(self.report_name, record.mapped('id'), data=data)
                printer.linux_print(report_file, copies)
            rep_env.print_report(self.report_name, model_for_log,
                ids_for_log, printer.id,
                reason=reprint_reason or '', copies=copies
            )

    @api.multi
    def use_report_server(self):
        # Nustato ar ataskaitą spausdint pagal odoo qweb ataskaitas
        # ar reikia naudoti bls pdf formavimo serverį

        if self.report_name in USE_BLS_REPORT_SERVER_FOR_REPORTS:
            return True
        return False

    @api.multi
    def get_report_language(self):
        # lang = 'LT'
        # if self.report_name in [
        #     'config_sanitex_delivery.product_packing',
        #     'config_sanitex_delivery.stock_packing_report',
        #     'config_sanitex_delivery.drivers_packing_transfer_act',
        #     'config_sanitex_delivery.tare_to_driver_act',
        #     'config_sanitex_delivery.client_packing_from_picking'
        # ]:
        lang = self.env.user.company_id.report_language or 'LT'
        return lang

# class IrValues(models.Model):
#     _inherit = 'ir.values'
#
#     def get_actions(
#         self, cr, uid, action_slot, model, res_id=False, context=None
#     ):
#         res = super(IrValues, self).get_actions(
#             cr, uid, action_slot, model, res_id=res_id, context=context
#         )
#         if res:
#             try:
#                 return sorted(res, key=lambda tup: tup[2].get('sequence_no',0))
#             except:
#                 pass
#         return res
    
class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'


    @api.model
    def update_args(self, args):
        context = self.env.context or {}
        if not context.get('get_all_menu', False):
            user = self.env['res.users'].browse(self.env.uid)
            if user.does_user_belong_to_group('base.group_system'):
                args.append(('id', 'not in', self.sudo().env.ref('config_sanitex_delivery.menu_action_bls_limited_res_users').mapped('id')))


    @api.model
    def _search(
            self, args, offset=0, limit=None,
            order=None, count=False,
            access_rights_uid=None
    ):
        self.update_args(args)
        return super(IrUiMenu, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )


    @api.multi
    def read(self, fields=None, load='_classic_read'):

        res = super(IrUiMenu, self).read(fields=fields, load=load)
        data_obj = self.env['ir.model.data']
#         view_obj = self.env('ir.ui.view')
        usr_obj = self.env['res.users']
        route_env = self.env['stock.route']
        pick_env = self.env['stock.picking']

        datas = data_obj.search([
            ('model','=','ir.ui.menu'),
            ('name','in',['menu_account_invoice_containers_not_received'])
        ])
        for data in datas:
            act_id = data.read(fields=['res_id'])[0]['res_id']

            if act_id in self.mapped('id'):
                user = usr_obj.browse(self.env.uid)
                if user.default_warehouse_id:
                    for menu in res:
                        if menu['id'] == act_id and menu.get('name', False):
                            if user.default_warehouse_id.get_not_received_containers():
                                menu['name'] = menu['name'] + ' (' + str(len(user.default_warehouse_id.get_not_received_containers())) + ')'

        datas = data_obj.search([
            ('model','=','ir.ui.menu'),
            ('name','in',['menu_action_stock_routes'])
        ])
        for data in datas:
            act_id = data.read(fields=['res_id'])[0]['res_id']

            if act_id in self.ids:
                routes_counter = route_env.get_number_of_arriving_routes()
                for menu in res:
                    if menu['id'] == act_id and menu.get('name', False):
                        menu['name'] = menu['name'] + ' (' + str(routes_counter) + ')'

        datas = data_obj.search([
            ('model','=','ir.ui.menu'),
            ('name','in',['menu_stock_picking_incoming_movements'])
        ])
        for data in datas:
            act_id = data.read(fields=['res_id'])[0]['res_id']

            if act_id in self.ids:
                picking_counter = pick_env.get_number_of_arriving_movements()
                if picking_counter > 0:
                    for menu in res:
                        if menu['id'] == act_id and menu.get('name', False):
                            menu['name'] = menu['name'] + ' (' + str(picking_counter) + ')'

        # self.env.clear()
        return res



    #Uzklotas standartinis metodas, kad pasalinti loadinima, tik kai pasikeicia DEBUG rezimas, useris arba kalba
    #tam, kad perkrovus langa, atsinaujintu statiski meniu pavadinimai
    @api.model
    def load_menus(self, debug):
        """ Loads all menu items (all applications and their sub-menus).

        :return: the menu root
        :rtype: dict('children': menu_nodes)
        """
        fields = ['name', 'sequence', 'parent_id', 'action', 'web_icon', 'web_icon_data']
        menu_roots = self.get_user_roots()
        menu_roots_data = menu_roots.read(fields) if menu_roots else []
        menu_root = {
            'id': False,
            'name': 'root',
            'parent_id': [-1, ''],
            'children': menu_roots_data,
            'all_menu_ids': menu_roots.ids,
        }

        if not menu_roots_data:
            return menu_root

        # menus are loaded fully unlike a regular tree view, cause there are a
        # limited number of items (752 when all 6.1 addons are installed)
        menus = self.search([('id', 'child_of', menu_roots.ids)])
        menu_items = menus.read(fields)

        # add roots at the end of the sequence, so that they will overwrite
        # equivalent menu items from full menu read when put into id:item
        # mapping, resulting in children being correctly set on the roots.
        menu_items.extend(menu_roots_data)
        menu_root['all_menu_ids'] = menus.ids  # includes menu_roots!

        # make a tree using parent_id
        menu_items_map = {menu_item["id"]: menu_item for menu_item in menu_items}
        for menu_item in menu_items:
            parent = menu_item['parent_id'] and menu_item['parent_id'][0]
            if parent in menu_items_map:
                menu_items_map[parent].setdefault(
                    'children', []).append(menu_item)

        # sort by sequence a tree using parent_id
        for menu_item in menu_items:
            menu_item.setdefault('children', []).sort(key=operator.itemgetter('sequence'))

        (menu_roots + menus)._set_menuitems_xmlids(menu_root)

        return menu_root

class IrActionsServer(models.Model):
    _inherit = 'ir.actions.server'

    sequence_no = fields.Integer('Sequence', default=100)
    
class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'
    
    sequence_no = fields.Integer('Sequence', default=100)
    limit = fields.Integer('Limit', help='Default limit for the list view', default=100)

class IrModelData(models.Model):
    _inherit = 'ir.model.data'

    @api.model
    def get_xml_id_by_database_id(self, model, model_id):
        xml_ids = self.search([
            ('model','=',model),
            ('res_id','=',model_id)
        ])
        if xml_ids:
            return list(map(lambda xml: xml.module + '.' + xml.name, xml_ids))
        return []

class IrTranslation(models.Model):
    _inherit = 'ir.translation'

    last_update_date = fields.Datetime('Synchronisation Date', readonly=True)
    last_synchronisation_datetime = fields.Datetime('Date of Last Synchronisation', readonly=True)
    
    @api.model
    def create(self, vals):
        if 'value' in vals.keys():
            vals['last_update_date'] = time.strftime('%Y-%m-%d %H:%M:%S')
        return super(IrTranslation, self).create(vals)

    @api.multi
    def write(self, vals):
        if 'value' in vals.keys():
            vals['last_update_date'] = time.strftime('%Y-%m-%d %H:%M:%S')
        return super(IrTranslation, self).write(vals)

    @api.multi
    def synchronise_with_all_serves(self):
        return self.synchronise_translations()

    @api.multi
    def synchronise_translations(self, databases=None):
        data_env = self.env['ir.model.data']
        if databases is None:
            databases = self.env.user.company_id.atlas_server_ids.mapped('database_ids')
        all_lines = len(databases)*len(self)
        i = 0
        pi = 0
        for database in databases:
            database_connection = database.server_id.connect_xml_rpc()
            for translation in self:
                i += 1
                if not translation.src:
                    continue
                arguments = [translation.type, translation.name, translation.src,
                    translation.value, translation.lang, translation.module,
                    translation.last_update_date, translation.res_id, translation.comments
                ]
                if translation.type == 'model':
                    xml_ids = data_env.get_xml_id_by_database_id(translation.name.split(',')[0], translation.res_id)
                    arguments.append(xml_ids)
                else:
                    arguments.append([])
                database.call_method(
                    'ir.translation', 'update_tranlsation_if_needed',
                    args=arguments, connection=database_connection
                )
                if round((i / all_lines)*100) != pi:
                    pi = round((i / all_lines)*100)
                    _logger.info('Translation Synchronisation: %s / %s' % (str(i), str(all_lines)))
                translation.write({'last_synchronisation_datetime': time.strftime('%Y-%m-%d %H:%M:%S')})
                self.env.cr.commit()

    @api.model
    def update_tranlsation_if_needed(self, translation_type, translation_name, source, value, lang,
        odoo_module, last_update_date, res_id, comments, xml_ids
    ):
        if not odoo_module:
            odoo_module = ''
        sql = '''
            SELECT
                id, 
                value,
                last_update_date
            FROM
                ir_translation
            WHERE
                type = %s
                AND name = %s
                AND src = %s
                AND lang = %s
                AND module = %s
        '''
        where = [translation_type, translation_name, source, lang, odoo_module]
        if translation_type in ['code']:
            old_sql = sql
            old_where = where[:]
            sql += ' AND res_id = %s'
            where.append(res_id)
        elif translation_type in ['model']:
            ids = []
            for xml_id in xml_ids:
                record = self.env.ref(xml_id, raise_if_not_found=False)
                if record:
                    ids.append(record.id)
            if not ids:
                return False
            old_sql = sql
            old_where = where[:]
            sql += ' AND res_id in %s'
            where.append(tuple(ids))
        where = tuple(where)
        self.env.cr.execute(sql, where)
        translation_results = self.env.cr.fetchall()
        if not translation_results and translation_type in ['code']:
            self.env.cr.execute(old_sql, old_where)
            translation_results = self.env.cr.fetchall()
        if translation_results:
            for translation_result in translation_results:
                if not translation_result[2] or translation_result[2] < last_update_date:
                    sql_edit = '''
                        UPDATE
                            ir_translation
                        SET
                            value = %s,
                            last_synchronisation_datetime = %s
                        WHERE
                            id = %s
                    '''
                    where_edit = (value, time.strftime('%Y-%m-%d %H:%M:%S'), translation_result[0])
                    self.env.cr.execute(sql_edit, where_edit)
        else:
            sql_create_1 = '''
                INSERT INTO
                    ir_translation '''
            sql_create_2 = ''' VALUES
                    %s                    
            '''
            fields = ['type','name', 'src', 'lang', 'module', 'value', 'last_synchronisation_datetime', 'state', 'comments', 'res_id']
            values = [translation_type, translation_name, source, lang, odoo_module, value, time.strftime('%Y-%m-%d %H:%M:%S'), 'translated', comments, res_id]
            if translation_type in ['model']:
                values.pop()
                values.append(ids[0])

            fields_str = '(' + ', '.join(fields) + ')'
            sql_create = sql_create_1 + fields_str + sql_create_2
            where_create = (tuple(values),)
            self.env.cr.execute(sql_create, where_create)
        return True

    @api.model
    def clear_cache_after_syncronisations(self):
        self.clear_caches()
        return False

