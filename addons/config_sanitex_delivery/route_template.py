# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################
#
from odoo import fields, models, _, api
import time
from odoo.exceptions import UserError

from datetime import datetime, timedelta

class StockRouteTemplate(models.Model):
    _name = 'stock.route.template'
    _description = 'Template of Tasks and Routes'

    @api.one
    @api.depends('route_no_id')
    def _compute_qty(self):
        qty_in_warehouse = 0
        qty_not_received = 0
        qty_in_route = 0
        qty_planned = 0
        cancelled = 0
        fully_released = False
        if self.route_no_id:
            qty_planned = self.route_no_id.get_total_planned_tasks()
            qty_in_warehouse = self.route_no_id.get_in_warehouse_tasks()
            qty_in_route = self.route_no_id.get_in_route_tasks()
            # qty_not_received = self.route_no_id.get_total_not_received_tasks()
            cancelled = self.route_no_id.get_qty_cancelled()
            fully_released = self.route_no_id.get_if_fully_released(qty_planned, cancelled)
            qty_not_received = qty_planned - qty_in_warehouse - qty_in_route - fully_released - cancelled
        self.qty_in_warehouse = qty_in_warehouse > 0 and str(qty_in_warehouse) or '-'
        self.qty_not_received = qty_not_received > 0 and str(qty_not_received) or '-'
        self.qty_in_route = qty_in_route > 0 and str(qty_in_route) or '-'
        self.qty_planned = qty_planned > 0 and str(qty_planned) or '-'
        self.qty_cancelled = cancelled > 0 and str(cancelled) or '-'
        self.fully_released = fully_released
        
    @api.one
    @api.depends('route_no_id')
    def _compute_weight(self):
        weight_in_warehouse = 0
        if self.route_no_id:
            weight_in_warehouse = self.route_no_id.get_in_warehouse_tasks_weight()
        self.weight_in_warehouse = weight_in_warehouse    

    @api.one
    def _compute_shipping_warehouse(self):
        user = self.env['res.users'].browse(self.env.uid)
        wh_ids = user.get_current_warehouses().mapped('id')
        if not wh_ids:
            return 0
        if user.default_region_id:
            sql = '''
                SELECT 
                    distinct(sw.name)
                FROM (SELECT
                        so.transportation_order_id as transportation_order_id, max(so.sequence)
                        FROM
                            sale_order so
                        WHERE
                            so.route_number_id = %s
                            AND (so.warehouse_id in %s or so.shipping_warehouse_id in %s) 
                        GROUP BY 
                            so.transportation_order_id
                    ) as x 
                INNER JOIN 
                    sale_order as so2 on (so2.transportation_order_id = x.transportation_order_id and x.max = so2.sequence)
                LEFT JOIN 
                    stock_warehouse sw on (sw.id = so2.warehouse_next_to_id)
                WHERE
                    so2.route_number_id = %s
            '''
            where = (self.route_no_id.id, tuple(wh_ids), tuple(wh_ids), self.route_no_id.id)
        else:
            sql = '''
                SELECT
                    distinct(sw.name)
                FROM
                    sale_order so
                    left join stock_warehouse sw on (sw.id = so.warehouse_next_to_id)
                WHERE
                    so.route_number_id = %s
                    AND so.warehouse_id in %s
            '''
            where = (self.route_no_id.id, tuple(wh_ids))
        sql2 = '''
            SELECT
                distinct(sw.name)
            FROM
                sale_order so
                left join stock_warehouse sw on (sw.id = so.warehouse_next_to_id)
            WHERE
                so.route_number_id = %s
                AND so.shipping_warehouse_id in %s
                AND so.warehouse_id not in %s
        '''


        self.env.cr.execute(sql, where)
        sql_result = self.env.cr.fetchall()

        self.env.cr.execute(sql2, (self.route_no_id.id, tuple(wh_ids), tuple(wh_ids)))
        sql_result2 = self.env.cr.fetchall()
        for r in sql_result2:
            if r not in sql_result:
                sql_result.append(r)
        names = [tpl[0] for tpl in sql_result if tpl[0]]
        if user.default_region_id:
            main_wh_name, all_wh_names = user.default_region_id.get_all_warehouses_by_name()
            names2 = []
            for name in names:
                if name in all_wh_names:
                    names2.append(main_wh_name)
                else:
                    names2.append(name)
            names = list(set(names2))
        # print('sql_result', sql_result)
        result = ', '.join([name for name in names if isinstance(name, str)])
        self.shipping_warehouses_recalc = result

    @api.model
    def _search_shipping_warehouse(self, operator, operand):
        user = self.env['res.users'].browse(self.env.uid)
        wh_ids = user.get_current_warehouses().mapped('id')
        if operator == 'ilike':
            operand = '%'+operand+'%'
        if not wh_ids:
            return 0
        if not operand:
            sql = '''
                SELECT
                    srn.id
                FROM
                    stock_route_number srn
                WHERE
                    (select count(id) 
                        from sale_order 
                        where route_number_id = srn.id) = 0
            '''
            # where = (tuple(wh_ids),)
            self.env.cr.execute(sql)
            sql_result = self.env.cr.fetchall()
            ids = [res[0] for res in sql_result]
            # t = time.time()
            # self.env.cr.execute(sql, where)
            # print('SQL %.5f' % (time.time() - t))
            # sql_result = self.env.cr.fetchall()
            # ids = [res[0] for res in sql_result]
            # return [('route_no_id','in',ids)]

        elif user.default_region_id:
            # sql = '''
            #     SELECT
            #         so.route_number_id
            #     FROM
            #         sale_order so
            #         left join stock_warehouse sw on (sw.id = so.shipping_warehouse_id)
            #         left join stock_region sr on (sr.id = sw.region_id)
            #     WHERE
            #         so.warehouse_id in %s
            #         AND (sr.main_warehouse_name ''' + operator + ''' %s
            #             OR sw.name ''' + operator + ''' %s
            #         )
            # '''
            sql = '''
                SELECT 
                    so2.route_number_id 
                FROM (
                        SELECT 
                            so.transportation_order_id as transportation_order_id, 
                            max(so.sequence) 
                        FROM 
                            sale_order so 
                        WHERE 
                            (so.warehouse_id in %s or so.shipping_warehouse_id in %s)
                        GROUP BY 
                            so.transportation_order_id
                    ) as x INNER JOIN sale_order as so2 on (so2.transportation_order_id = x.transportation_order_id and x.max = so2.sequence)  
                    LEFT JOIN stock_warehouse sw2 on (sw2.id = so2.warehouse_next_to_id) 
                WHERE 
                    sw2.name ''' + operator + ''' %s 
                    AND so2.transportation_order_id is not null
            '''


            where = (tuple(wh_ids), tuple(wh_ids), operand)
            # print('SEARCH', sql % where)
            self.env.cr.execute(sql, where)
            sql_result = self.env.cr.fetchall()
            ids = [res[0] for res in sql_result]
        else:
            sql = '''
                SELECT
                    so.route_number_id
                FROM
                    sale_order so
                    left join stock_warehouse sw on (sw.id = so.warehouse_next_to_id)
                WHERE
                    so.warehouse_id in %s
                    AND sw.name ''' + operator + ''' %s
            '''
            where = (tuple(wh_ids), operand)
            sql2 = '''
                SELECT
                    so.route_number_id
                FROM
                    sale_order so
                    left join stock_warehouse sw on (sw.id = so.warehouse_next_to_id)
                WHERE
                    so.shipping_warehouse_id in %s
                    AND so.warehouse_id not in %s
                    AND sw.name ''' + operator + ''' %s
            '''

            self.env.cr.execute(sql, where)
            sql_result = self.env.cr.fetchall()
            ids = [res[0] for res in sql_result]
            self.env.cr.execute(sql2, (tuple(wh_ids), tuple(wh_ids), operand))
            sql_result2 = self.env.cr.fetchall()
            ids += [res[0] for res in sql_result2 if res[0] not in ids]
        return [('route_no_id','in',ids)]


    id_route_external = fields.Char('Route ID', readonly=True)
    route_no_id = fields.Many2one('stock.route.number', 'Route Number', readonly=True, index=True)
    route_no = fields.Char('Route Number', readonly=True)
    qty_in_warehouse = fields.Char('In Warehouse', size=16, readonly=True, compute='_compute_qty')
    qty_not_received = fields.Char('Not Received', size=16, readonly=True, compute='_compute_qty')
    qty_cancelled = fields.Char('Cancelled', size=16, readonly=True, compute='_compute_qty')
    qty_in_route = fields.Char('In Route', size=16, readonly=True, compute='_compute_qty')
    qty_planned = fields.Char('Planned Qty', size=16, readonly=True, compute='_compute_qty')
    source = fields.Char('Source', readonly=True, size=64)
    picking_warehouse_id_filter = fields.Char('Field to filter by Sales Picking Warehouse', readonly=True, size=256)
    shipping_warehouse_id_filter = fields.Char('Field to filter by Sales Shipping Warehouse', readonly=True, size=256)
    date = fields.Date('Date', readonly=True)
    task_ids = fields.One2many('sale.order', 'route_template_id', 'Tasks')
    fully_released = fields.Boolean('Fully released', readonly=True, compute='_compute_qty')
    driver = fields.Char('Driver', readonly=True, size=128)
    driver_show = fields.Char('Driver', readonly=True, size=256)
    shipping_warehouses = fields.Char('Shipping Warehouses', size=128, readonly=True)
    shipping_warehouses_recalc = fields.Char(
        'Shipping Warehouses', size=128, readonly=True, compute='_compute_shipping_warehouse',
        search='_search_shipping_warehouse'
    )
    weight = fields.Float('Weight, kg', digits=(16,0), readonly=True)
    distance = fields.Integer('Distance', readonly=True)
    posid_search = fields.Char('POSID', readonly=True) # Nesipildo. Idetas del searcho
    weight_in_warehouse =  fields.Float('Weight, kg', digits=(16,0), readonly=True, compute='_compute_weight')
    estimated_start = fields.Datetime('Estimated Start')
    estimated_finish = fields.Datetime('Estimated Finish')

    _rec_name = 'route_no'
    _order = 'date desc, route_no'

    @api.multi
    def assign_tasks(self, tasks):
        task_vals = {
            'route_number_id': self.route_no_id.id
        }

        if self.driver:
            location = self.env['stock.location'].search([
                ('name', '=', self.driver)
            ], limit=1)
            if location:
                task_vals['driver_id'] = location.id
                task_vals['license_plate'] = location.license_plate
            task_vals['driver_name'] = self.driver
        task_vals['added_manually'] = True
        task_vals['order_number_by_route'] = 'MANUAL'
        task_vals['order_number_by_route_int'] = 999
        task_vals['delivering_goods_by_routing_program'] = ''
        tasks.write(task_vals)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if not args:
            recs = self.search(['|',('route_no', operator, name),'|',('driver', operator, name),('date', operator, name)] + args, limit=limit)

        return recs.name_get()

    @api.multi
    def name_get(self):
        if not self:
            return []
        res = []
        for template in self.read([
            'route_no', 'driver', 'date', 'shipping_warehouses_recalc'
        ]):
            name = ''
            if template.get('route_no', False):
                name = template['route_no']
            if template.get('date', False):
                name += ' [' + template['date'] + ']'
            if template.get('driver', False):
                name += ' - ' + template['driver']
            if template.get('shipping_warehouses_recalc', False):
                name += ' (' + template['shipping_warehouses_recalc'] + ')'
            res.append((template['id'], name))

        return res

    @api.model
    def create_route_template(self, route_number):
        vals = {
            'route_no_id': route_number.id,
            'route_no': route_number.name,
            'id_route_external': route_number.external_route_id,
            'date': route_number.date,
            'driver': route_number.driver,
            'weight': route_number.weight,
            'distance': route_number.distance,
            'source': route_number.source,
            'driver_show': route_number.driver,
            'estimated_start': route_number.estimated_start,
            'estimated_finish': route_number.estimated_finish
        }

        return self.create(vals)

    @api.multi
    def update_picking_warehouse_id_filter(self):
        # sudaromas tekstas kuriame yra visi susijusių pardavimų išleidimų sandėlių id
        # kad būtų galima greičiau atlikti maršrutų paiešką pagal naudotoją
        context = self.env.context or {}
        ctx = context.copy()
        ctx['search_by_user_sale'] = False
        for template in self:
            template = template.with_context(ctx)
            template.write({
                'picking_warehouse_id_filter': template.route_no_id.get_all_sale_ids().get_picking_warehouse_id_filter()
            })

        return True

    @api.multi
    def update_shipping_warehouse_id_filter(self):
        # sudaromas tekstas kuriame yra visi susijusių pardavimų išleidimų sandėlių id
        # kad būtų galima greičiau atlikti maršrutų paiešką pagal naudotoją
        wh_env = self.env['stock.warehouse']
        context = self.env.context or {}
        ctx = context.copy()
        ctx['search_by_user_sale'] = False
        for template in self:
            template = template.with_context(ctx)
            wh_filter = template.route_no_id.get_all_sale_ids().get_shipping_warehouse_id_filter()
            # task_env.browse(template.route_no_id.get_task_to_put_in_route())
            # warehouses = template.route_no_id.get_task_to_put_in_route().mapped('shipping_warehouse_id')
            warehouses = wh_env.browse([int(wh_id) for wh_id in wh_filter.split('id') if wh_id])
            template.write({
                'shipping_warehouse_id_filter': wh_filter,
                'shipping_warehouses': ', '.join(set(warehouses.mapped('name')))
            })


        return True
    @api.model
    def update_args(self, args):
        context = self.env.context or {}
        usr_obj = self.env['res.users']
        if context.get('get_current_routes', False):
            tomorrow = datetime.now() + timedelta(days=1)
            args.append(('date', '<=', tomorrow))
            args.append(('date', '>=', time.strftime('%Y-%m-%d')))
        if context.get('search_by_user', False):  # and uid!= 1:
            user = usr_obj.browse(self.env.uid)
            allowed_wh_ids = user.get_current_warehouses().mapped('id')
            for allowed_wh_id in allowed_wh_ids:
                args.append('|')
                args.append(('picking_warehouse_id_filter', 'like', '%id' + str(allowed_wh_id) + 'id%'))
                args.append('|')
                args.append(('shipping_warehouse_id_filter', 'like', '%id' + str(allowed_wh_id) + 'id%'))
            if allowed_wh_ids:
                args.pop(-2)



    @api.model
    def get_route_template_ids_by_posid(self, posid, operation='='):
        sql_sentence = "SELECT DISTINCT(route_template_id) FROM sale_order WHERE posid"
        if operation == 'like':
            posid = "%" + posid + "%"
        sql_sentence += " " + operation + " '%s'" % (posid)
        
        self._cr.execute(sql_sentence)
        return [tpl[0] for tpl in self._cr.fetchall() if tpl[0] is not None]

    @api.model
    def _search(
            self, args, offset=0, limit=None,
            order=None, count=False,
            access_rights_uid=None
    ):
        new_args = []
        for arg in args:
            if len(arg) != 3 or arg[0] != 'posid_search':
                new_args.append(arg)
            else:
                route_tmpl_ids = self.get_route_template_ids_by_posid(arg[2])
                new_args.append(('id','in',route_tmpl_ids))
        args = new_args
        self.update_args(args)
        return super(StockRouteTemplate, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )

    @api.multi
    def action_create_route_confirm(self):
        msg = []

        if sum([int(qty) for qty in self.mapped('qty_in_warehouse') if qty != '-']) <= 0:
            raise UserError(_('There are no tasks in warehouse.'))
        for route in self:
            if route.qty_not_received and route.qty_not_received != '-':
                msg.append(_('Route \'%s\' still has %s task not received in warehouse.') %(route.route_no, str(route.qty_not_received)))
        if msg:
            message_to_show = '\n'.join(msg)
            message_to_show += '\n' + _('Do not forget to release theese task with additional route!')
            context = self.env.context or {}
            ctx = context.copy()
            ctx['active_ids'] = self.mapped('id')
            ctx['action_model'] = self._name
            ctx['action_function'] = 'action_create_route'
            ctx['warning'] = message_to_show

            form_view = self.env.ref('config_sanitex_delivery.object_action_warning_osv_form', False)[0]
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'object.confirm.action.osv',
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': ctx,
                'nodestroy': True,
                'views': [(form_view.id,'form')],
            }
        else:
            return self.action_create_route()

    @api.multi
    def action_open_sales(self):
        return self.route_no_id.action_open_sales()

    @api.multi
    def action_create_route(self):
        so_env = self.env['sale.order']
        route_env = self.env['stock.route']
        tasks = so_env.browse([])
        tasks_in_route = so_env.browse([])


        user = self.env['res.users'].browse(self.env.uid)
        wh_ids = user.get_current_warehouses().mapped('id')
        for template in self:
            tasks += template.route_no_id.get_task_to_put_in_route()
            tasks_in_route = template.route_no_id.get_tasks_in_route()
        if not tasks:
            raise UserError(_('There are no tasks in warehouse.'))
        route_type = tasks.get_type_for_route()
        if route_type in ('internal', 'mixed') and len(wh_ids) > 1:
            raise UserError(_('You cant create internal route from region, please select one warehouse.'))
        routes = tasks_in_route.mapped('route_id').filtered(
            lambda route_rec: not route_rec.name
                and route_rec.sale_ids.mapped('warehouse_id') == tasks.mapped('warehouse_id')
        )
        if not routes:
            res = tasks.create_route()
            route = route_env.browse(res['res_id'])
            route_vals = {'route_length': sum(self.mapped('distance'))}
            estimated_start = self.filtered('estimated_start').mapped('estimated_start')
            if estimated_start:
                route_vals['estimated_start'] = min(estimated_start)
            estimated_finish = self.filtered('estimated_finish').mapped('estimated_finish')
            if estimated_finish:
                route_vals['estimated_finish'] = min(estimated_finish)
            route.write(route_vals)
            drivers = list(set(self.mapped('driver')))
            if len(drivers) == 1 and route.type == 'out' and drivers[0] != '':
                route = route_env.browse(res['res_id'])
                if route.location_id.name != drivers[0]:
                    driver = self.env['stock.location'].search([('name','=',drivers[0])], limit=1)
                    if driver:
                        wiz = self.env['stock.route.select_driver.osv'].create({'driver_id': driver.id})
                        wiz._onchange_driver_id()
                        wiz.with_context(active_ids=[route.id], active_model='stock.route').select()
            else:
                route = route_env.browse(res['res_id'])
                route.write({
                    'location_id': False,
                    'license_plate': '',
                    'trailer': '',
                    'driver_picked': False,
                    'driver_company_id': False
                })
            return res
        else:
            tasks.write({'route_id': routes[0].id})
            domain = [('id','=',routes[0].id)]
            form_view = self.env.ref('config_sanitex_delivery.view_stock_routes_form', False)[0]
            view = self.env.ref('config_sanitex_delivery.view_stock_routes_tree', False)[0]
            return {
                'name': _('Created Route'),
                'view_type': 'form',
                'view_mode': 'form,tree',
                'res_model': 'stock.route',
                'views': [(form_view.id,'form'),(view.id,'tree')],
                'type': 'ir.actions.act_window',
                'res_id': routes[0].id,
                'domain': domain,
                'context': {'search_by_user_sale': False, 'remove_task_from_route': True}
            }

    @api.multi
    def remove_if_empty(self):
        # Kartais per integraciją išmaršruto ruošinio išimami visi užsakymai ir perdedami
        # į naują ruošinį su tokiu pačiu numeriu, tai Atlase atrodo kad susidubliavo ruošiniai.
        # Ši funkcija ištrina tokius ruošinius, kurie yra tušti.
        templates_to_delete = self.browse([])
        for template in self:
            sql_search = '''
                SELECT
                    id
                FROM
                    sale_order
                WHERE
                    route_template_id = %s
                '''
            where_search = (str(template.id),)
            self.env.cr.execute(sql_search, where_search)
            if not self.env.cr.fetchall():
                templates_to_delete |= template
        templates_to_delete.unlink()



    @api.multi
    def action_open_routes(self):
        so_env = self.env['sale.order']
        tasks = so_env.with_context(search_by_user_sale=False, search_for_template_view=True).search([
            ('route_template_id','in',self.mapped('id'))
        ])
        routes = tasks.mapped('route_id')
        if not routes:
            raise UserError(_('No routes are created from this template'))
        # routes_action = self.env.ref('config_sanitex_delivery.action_outgoing_stock_routes').read([])[0]
        # routes_action['domain'] = [('id','in',routes.mapped('id'))]
        # routes_action['context'] = {'search_by_user_sale': False, 'remove_task_from_route': True}
        form_view = self.env.ref('config_sanitex_delivery.view_stock_routes_form', False)[0]
        view = self.env.ref('config_sanitex_delivery.view_stock_routes_tree', False)[0]
        domain = [('id','in',routes.mapped('id'))]
        routes_action = {
            'name': _('Created Route'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.route',
            # 'views': [(form_view.id,'form'),(view.id,'tree')],
            'type': 'ir.actions.act_window',
            'domain': domain,
            'context': {'search_by_user_sale': False, 'remove_task_from_route': True}
        }
        if len(routes) == 1:
            routes_action['view_mode'] = 'form,tree'
            routes_action['res_id'] = routes.id
            routes_action['views'] = [(form_view.id,'form'),(view.id,'tree')]
            return routes_action
        else:
            routes_action['views'] = [(view.id,'tree'),(form_view.id,'form')]
            return routes_action
        
    #Metodas kvieciamas is JS, paduodant netvarkingus domainus, o grazinami skirtingi galimi pristatymo sandeliai
    def get_avail_shipping_warehouses(self, domains, action_domain=False, action_context=False):
        context = action_context or {}
        normalized_domain = []       
        self.with_context(context).update_args(normalized_domain)
        user = self.env['res.users'].browse(self.env.uid)
        wh_ids = user.get_current_warehouses().mapped('id')
        
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
        query_str = 'SELECT route_no_id FROM stock_route_template %s ORDER BY shipping_warehouses' % where_str

        self.env.cr.execute(query_str, where_clause_params)
        res = self.env.cr.fetchall()

        ids = [tpl[0] for tpl in res]
        if user.default_region_id:
            sql = '''
                SELECT 
                    distinct(sw.name)
                FROM (SELECT
                        so.transportation_order_id as transportation_order_id, max(so.sequence)
                        FROM
                            sale_order so
                        WHERE
                            so.warehouse_id in %s or so.shipping_warehouse_id in %s 
                        GROUP BY 
                            so.transportation_order_id
                    ) as x 
                INNER JOIN 
                    sale_order as so2 on (so2.transportation_order_id = x.transportation_order_id and x.max = so2.sequence)
                LEFT JOIN 
                    stock_warehouse sw on (sw.id = so2.warehouse_next_to_id)
                LEFT JOIN
                    stock_route_template on (route_no_id = so2.route_number_id)''' +\
                  (''' %s
            ''' % where_str)
            where = tuple([tuple(wh_ids), tuple(wh_ids)] + where_clause_params)
            # print('LIST', sql % where)
        else:
            sql = '''
                SELECT
                    distinct(sw.name)
                FROM
                    sale_order so
                    left join stock_warehouse sw on (sw.id = so.warehouse_next_to_id)
                WHERE
                    so.route_number_id in %s
                    and (so.shipping_warehouse_id = so.warehouse_id and so.shipping_warehouse_id in %s
                       or (so.shipping_warehouse_id != so.warehouse_id
                            and so.warehouse_id in %s))
                    
            '''
            where = (tuple(ids), tuple(wh_ids), tuple(wh_ids))
        sql2 = '''
            SELECT
                distinct(sw.name)
            FROM
                sale_order so
                left join stock_warehouse sw on (sw.id = so.warehouse_next_to_id)
            WHERE
                so.route_number_id in %s
                and so.shipping_warehouse_id != so.warehouse_id
                and so.shipping_warehouse_id in %s
                and so.warehouse_id not in %s
        '''
        self.env.cr.execute(sql, where)
        res = self.env.cr.fetchall()

        names = [tpl[0] for tpl in res if tpl[0]]
        # print('names1', names)
        self.env.cr.execute(sql2, (tuple(ids), tuple(wh_ids), tuple(wh_ids)))
        res = self.env.cr.fetchall()
        # print('names2', res)
        names += [tpl[0] for tpl in res if tpl[0] and tpl[0] not in names]
        if user.default_region_id:
            main_wh_name, all_wh_names = user.default_region_id.get_all_warehouses_by_name()
            names2 = []
            for name in names:
                if name in all_wh_names:
                    names2.append(main_wh_name)
                else:
                    names2.append(name)
            names = list(set(names2))

        names.sort()
        return names

    #Metodas kvieciamas is JS, paduodant netvarkingus domainus, o grazinamos skirtingos galimos datos
    def get_avail_dates(self, domains, action_domain=False, action_context=False):
        context = action_context or {}
        normalized_domain = []       
        self.with_context(context).update_args(normalized_domain)
        
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
        query_str = 'SELECT DISTINCT(date) FROM stock_route_template %s ORDER BY date DESC' % where_str

        self.env.cr.execute(query_str, where_clause_params)
        res = self.env.cr.fetchall()
        dates = [tpl[0] for tpl in res]
        return dates


# class StockRouteTemplateTransfer(models.Model):
#     _name = 'stock.route.template.tranfer'
# 
#     number_id = fields.Many2one('stock.route.number', 'Number', readonly=True, index=True)
#     warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True, index=True)