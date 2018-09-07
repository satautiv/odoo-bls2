# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################
from odoo.addons.config_sanitex_delivery.tests.test_corrections import TestCorrections
# from openerp.osv import osv

class TestRoutes(TestCorrections):
    
    
    def setUp(self):
        super(TestRoutes, self).setUp()
        # self.do_routes = True
        self.do_owner = True
        self.do_product = True
        # self.do_sales = True
        self.do_partner = True
        self.do_location = True
        self.do_warehouse = True
        # self.do_packages = False
        # self.do_corrections = True
        self.do_regions = True
        self.ctx = {'no_commit': True, 'do_not_export_to_ivaz': True, 'do_not_export_tare_info': True}
        
        # if self.res_user_model.search([('login','=','op_test')]):
        #     self.operator_user = self.res_user_model.search([('login','=','op_test')])[0]
        # else:
        #     self.operator_user = self.res_user_model.with_context({'no_reset_password': True}).create(dict(
        #         name="Operator",
        #         company_id=self.main_company.id,
        #         login="op_test",
        #         email="op_test@sanitex.lt",
        #         groups_id=[(6, 0, [self.res_users_route_operator.id, self.user_group.id])]
        #     ))
        #
        # if self.res_user_model.search([('login','=','op2_test')]):
        #     self.operator_user_2 = self.res_user_model.search([('login','=','op2_test')])[0]
        # else:
        #     self.operator_user_2 = self.res_user_model.with_context({'no_reset_password': True}).create(dict(
        #         name="Operator2",
        #         company_id=self.main_company.id,
        #         login="op2_test",
        #         email="op2_test@sanitex.lt",
        #         groups_id=[(6, 0, [
        #             self.res_users_route_operator.id, self.user_group.id,
        #             self.env.ref('config_sanitex_delivery.stock_route_region_group').id
        #         ])]
        #     ))
        #
        # if self.res_user_model.search([('login','=','op3_test')]):
        #     self.operator_user_3 = self.res_user_model.search([('login','=','op3_test')])[0]
        # else:
        #     self.operator_user_3 = self.res_user_model.with_context({'no_reset_password': True}).create(dict(
        #         name="Operator3",
        #         company_id=self.main_company.id,
        #         login="op3_test",
        #         email="op3_test@sanitex.lt",
        #         groups_id=[(6, 0, [
        #             self.res_users_route_operator.id, self.user_group.id,
        #             self.env.ref('config_sanitex_delivery.stock_route_region_group').id
        #         ])]
        #     ))

    def import_route(self, vals):
        route_no = vals['receiver']
        # ctx = {'no_commit': True, 'do_not_export_to_ivaz': True, 'do_not_export_tare_info': True}
        intermediate_id = self.route_model.with_context(self.ctx).CreateRoute([vals])
        self.intermediate_model.with_context({'no_commit': True}).browse(
            [intermediate_id]
        ).process_intermediate_objects()
        sales = self.sale_model.search([('route_number', '=', route_no)])
        if len(sales) != 3:
            intermediate = self.intermediate_model.browse(intermediate_id)
            self.assertEqual(1, 2, 'No number on Tasks' + intermediate.traceback_string)

    def assign_region_to_user(self, user_id, region_name):
        user = self.res_user_model.browse(user_id)
        region = self.region_model.sudo(user_id).search([
            ('name','=',region_name),
            ('id','in',[reg_tuple[0] for reg_tuple in self.res_user_model.sudo(user_id).get_available_regions() \
                if isinstance(reg_tuple[0], int)]
            )
        ])
        self.assertEqual(len(region), 1, 'User can\'t find region 1 with name %s' % region_name)
        user.select_region(region.id)
        self.assertEqual(user.default_region_id, region, 'Default region not set')

    def create_route_from_sales(self, sales, user_id, expected_type):
        result = sales.sudo(user_id).create_route()
        self.assertIsInstance(result.get('res_id', False), int, 'No Route Created')
        route = self.route_model.browse(result['res_id'])
        self.assertEqual(len(route.container_line_ids), len(sales), 'No Container Lines in Route')
        self.assertEqual(set(route.container_line_ids.mapped('state')), {'none'}, 'No Container Lines in Route')
        self.assertEqual(route.type, expected_type, 'Wrong Route Type')
        return route

    def assign_driver_to_route(self, route, driver_code, user_id):
        ctx_driver = self.ctx.copy()
        ctx_driver['active_ids'] = [route.id]
        sel_dr_obj = self.env['stock.route.select_driver.osv']
        driver = self.env['stock.location'].sudo(user_id).search([('driver_code','=',driver_code)], limit=1)
        driver_wizard_vals = {'driver_id': driver.id}

        temp_wiz = sel_dr_obj.new(driver_wizard_vals)
        temp_wiz._onchange_driver_id()
        driver_wizard_vals.update(temp_wiz._convert_to_write(temp_wiz._cache))
        sel_dr = sel_dr_obj.with_context(ctx_driver).sudo(user_id).create(driver_wizard_vals)
        sel_dr.select()


        self.assertEqual(driver.id, route.location_id.id, 'No Driver')
        self.assertEqual(driver.owner_id.id, route.driver_company_id.id, 'Driver company did not fill in')
        self.assertEqual(
            driver.license_plate, route.license_plate,
            'Wrong License plate %s %s' % (
                driver.license_plate, route.license_plate
            )
        )
        return driver

    def assign_products_to_route(self, route, user_id, qty_to_add_to_route):
        ctx_product = self.ctx.copy()
        ctx_product['active_ids'] = [route.id]
        sel_pr_obj = self.env['stock.route.select_product.osv']
        osv_vals = sel_pr_obj.with_context(ctx_product).sudo(user_id).default_get(sel_pr_obj._fields)
        sel_pr = sel_pr_obj.with_context(ctx_product).sudo(user_id).create(osv_vals)
        lines = self.env['stock.route.select_product.line.osv'].sudo(user_id).search([('osv_id','=',sel_pr.id)])
        # qty_to_add_to_route = 10
        lines.filtered(lambda line_rec:
            line_rec.product_id.external_product_id != "test-BL-V517518" + self.id_ext
        ).write({'qty': qty_to_add_to_route})
        if route.picking_id:
            self.assertEqual(1, 2, 'Picking should not exist')
        sel_pr.select()

        wh_prod_ids = [p.id for p in sel_pr.warehouse_id.product_ids if p.external_product_id != "test-BL-V517518" + self.id_ext]
        route_prod_ids = [m.product_id.id for m in route.move_ids]
        self.assertEqual(set(wh_prod_ids), set(route_prod_ids), 'Wrong Product Selection')
        if not route.picking_id:
            self.assertEqual(1, 2, 'No picking Created')
        if not route.picking_id.move_lines:
            self.assertEqual(1, 2, 'Picking has no Lines')
        return wh_prod_ids

    def generate_packings_for_route(self, route):
        route.generate_product_act_new()
        self.assertEqual(
            len(route.sale_ids.filtered(
                lambda sale_record:
                    sale_record.warehouse_id == sale_record.shipping_warehouse_id
            )),
            len(route.packing_for_client_ids),
            'No enough or too many packings'
        )

    def print_packings_for_route(self, route):
        self.assertEqual(False, route.packing_for_client_ids[0].printed, 'Printed packing')
        route.packing_for_client_ids.print_packing()
        self.assertEqual(True, route.packing_for_client_ids[0].printed, 'Not printed packing')

    def release_route(self, route, user_id, no_packings=False):
        ctx_release = self.ctx.copy()
        ctx_release['extend_sale_not_in_separate_thread'] = True

        self.assertEqual(route.tasks_extended, False, 'Task Extended')
        route.with_context(ctx_release).sudo(user_id).action_release_confirm()
        self.assertEqual('released', route.state, 'State after release %s' % route.state)
        if not no_packings:
            self.assertEqual(
                len(route.sale_ids.filtered(
                    lambda sale_record:
                        sale_record.warehouse_id == sale_record.shipping_warehouse_id
                )),
                len(route.packing_for_client_ids),
                'No enough or too many packings'
            )
        self.assertEqual(route.tasks_extended, True, 'Task Not Extended')
        for sale in route.sale_ids:
            if sale.warehouse_id != sale.shipping_warehouse_id:
                self.assertEqual(len(sale.get_all_chain().filtered(lambda task: task.sequence >= sale.sequence)), 2, 'Task Not Extended')
            else:
                self.assertEqual(len(sale.get_all_chain().filtered(lambda task: task.sequence >= sale.sequence)), 1, 'Task Extended')

    def confirm_route_packings(self, route, user_id, qty_to_add_to_route, drivers_debt):
        packing = route.packing_for_client_ids[0]
        partner_debt = {}
        posid_debt = {}

        pack_lines = packing.line_ids
        for pack_line in pack_lines:
            partner_debt[pack_line.product_id.id] = packing.partner_id.get_debt(pack_line.product_id.id)
            posid_debt[pack_line.product_id.id] = packing.address_id.get_debt(pack_line.product_id.id)

        pack_lines.write({'give_to_customer_qty': qty_to_add_to_route})
        packing.with_context(self.ctx).sudo(user_id).action_done()
        self.assertEqual('done', packing.state, 'Packing State after confirmation')
        driver = route.location_id
        for pack_line in pack_lines:
            self.assertEqual(
                partner_debt[pack_line.product_id.id] + qty_to_add_to_route,
                packing.partner_id.get_debt(pack_line.product_id.id),
                'Wrong partner debt %s %s' % (
                    partner_debt[pack_line.product_id.id] + qty_to_add_to_route,
                    packing.partner_id.get_debt(pack_line.product_id.id)
                )
            )
            self.assertEqual(
                posid_debt[pack_line.product_id.id] + qty_to_add_to_route,
                packing.address_id.get_debt(pack_line.product_id.id),
                'Wrong partner debt %s %s' % (
                    str(posid_debt[pack_line.product_id.id] + qty_to_add_to_route),
                    str(packing.address_id.get_debt(pack_line.product_id.id))
                )
            )
            if pack_line.product_id.id in drivers_debt.keys():
                self.assertEqual(
                    drivers_debt[pack_line.product_id.id]-qty_to_add_to_route,
                    driver.get_drivers_debt(pack_line.product_id.id),
                    'Wrong driver debt %s %s' % (
                        str(drivers_debt[pack_line.product_id.id]-qty_to_add_to_route),
                        str(driver.get_drivers_debt(pack_line.product_id.id))
                    )
                )

    def close_route(self, route, user_id):
        route.with_context(self.ctx).sudo(user_id).action_close()
        self.assertEqual(route.state, 'closed', 'Route did not closed')


    def test_7000_stock_route_import(self):
        if self.do_routes:
            #Priskirti numatytuosius sandėlius naudotojams
            self.operator_user.select_region(False)
            self.assign_warehouse_to_user(self.operator_user.id, 'TEST_K')
            self.assign_warehouse_to_user(self.operator_user_2.id, 'TEST_V')
            
            
            route_number = "VI WH TEST 01 1" + self.id_ext
            route_vals = {
                "external_route_id": "test-BL-190041" + self.id_ext, 
                "name": route_number, 
                "car_number": "CCA150",
                "firmid": "BL",
                "warehouse_id": "TEST_V1", 
                "car_capacity": 18, 
                "driver_name": "Eduardas Kovalevskis", 
                "driver_code": "Eduardas Kovalevskis", 
                "receiver": route_number, 
                "date": self.today,
                "route_length": 80, 
                "route_no": route_number, 
                "type": "out", 
                "orders": [{
                    "delivery_type": "deliver", 
                    "delivery_number": "2", 
                    "shiping_warehouse_id": "TEST_V1", 
                    "order_no": "VU17242173" + self.id_ext,
                    "order_id": "test-1003-3275690-VU17242173" + self.id_ext, 
                    "active": "Y", 
                    "picking_warehouse_id": "TEST_K1", 
                    "owner_id": "1003"
                },{
                    "delivery_type": "deliver", 
                    "delivery_number": "2", 
                    "shiping_warehouse_id": "TEST_V1", 
                    "order_no": "VU17242173_2" + self.id_ext,
                    "order_id": "test-1003-3275690-VU17242173_2" + self.id_ext, 
                    "active": "Y", 
                    "picking_warehouse_id": "TEST_K1", 
                    "owner_id": "1003"
                },{
                    "delivery_type": "deliver", 
                    "delivery_number": "2", 
                    "shiping_warehouse_id": "TEST_K1", 
                    "order_no": "VU17242173_3" + self.id_ext,
                    "order_id": "test-1003-3275690-VU17242173_3" + self.id_ext, 
                    "active": "Y", 
                    "picking_warehouse_id": "TEST_K1", 
                    "owner_id": "1003"
                },]
            }

            ctx = {'no_commit': True, 'do_not_export_to_ivaz': True, 'do_not_export_tare_info': True}
            self.import_route(route_vals)

            sales = self.sale_model.search([('route_number','=',route_number)])
            route = self.create_route_from_sales(sales, self.operator_user.id, 'mixed')

            #Vairuotojo priskyrimas

            driver = self.assign_driver_to_route(route, 'test_code' + self.id_ext, self.operator_user.id)
            ctx['active_ids'] = [route.id]

            #produktu priskyrimas

            qty_to_add_to_route = 10
            wh_prod_ids = self.assign_products_to_route(route, self.operator_user.id, qty_to_add_to_route)

            primary_drivers_debt = {}
            drivers_debt = {}
            for prod_id in wh_prod_ids:
                primary_drivers_debt[prod_id] = driver.get_drivers_debt(prod_id)
                drivers_debt[prod_id] = driver.get_drivers_debt(prod_id) + qty_to_add_to_route

            #ruosiniu generavimas
            self.generate_packings_for_route(route)

            #ruosinio spausdinimas
            self.print_packings_for_route(route)
            prod_4 = self.product_model.sudo(self.operator_user.id).search([("external_product_id",'=',"test-BL-V517518" + self.id_ext)])
            self.env['stock.packing.line'].with_context(ctx).create({
                'product_id': prod_4.id,
                'product_code': prod_4.default_code,
                'give_to_customer_qty': 10,
                'packing_id': route.packing_for_client_ids[0].id,
                'partner_id': route.packing_for_client_ids[0].partner_id.id,
                'address_id': route.packing_for_client_ids[0].address_id.id,
                'warehouse_id': route.packing_for_client_ids[0].warehouse_id.id,
                # 'customer_posid_qty'] = line_vals['customer_qty']
                # 'final_qty'] = sale.partner_id.with_context(ctx_fast).get_debt(product[0])#.id)

            })
            # route.packing_for_client_ids

            #maršruto išleidimas
            self.release_route(route, self.operator_user.id)
            for prod_id in drivers_debt.keys():
                self.assertEqual(
                    drivers_debt[prod_id], driver.get_drivers_debt(prod_id), 
                    'Driver debt is wrong %s %s %s' % (
                        str(prod_id), str(drivers_debt[prod_id]), 
                        str(driver.get_drivers_debt(prod_id))
                    )
                )

            #ruošinių tvirtinimas
            self.confirm_route_packings(route, self.operator_user.id, qty_to_add_to_route, drivers_debt)
                    
            # Konteinerių gavimas
            route_for_user_2 = self.route_model.sudo(self.operator_user_2.id).browse(route.id)
            self.assertEqual(route_for_user_2.state_receive, 'released', 'Bad Receive State. Should be released')
            receive_result = route_for_user_2.action_receive()
            receive_wiz_env = self.env['stock.route.receive.osv']
            receive_wiz = receive_wiz_env.sudo(self.operator_user_2.id).browse(receive_result['res_id'])
            receive_lines = receive_wiz.line_ids
            self.assertEqual(len(receive_lines), len(route_for_user_2.sale_ids.mapped('shipping_warehouse_id')), 'Not enough or too much of receive wizard lines')
            self.assertEqual(len(receive_lines.filtered('check_all')), 1, 'No line is marked as local warehouse')
            receive_wiz.receive()
            self.assertEqual(route_for_user_2.state_receive, 'closed', 'Bad Receive State. Should be closed')
            self.assertEqual(
                set(route_for_user_2.container_line_ids.mapped('state')),
                {'none', 'received'}, 'Container states are wrong')
            

            #uždaryti maršrutą
            # route.with_context({'no_commit': True, 'do_not_export_to_ivaz': True, 'do_not_export_tare_info': True}).action_close()
            # self.assertEqual(route.state, 'closed', 'Route did not closed')
            self.close_route(route, self.operator_user.id)

            ctx_sale_search = self.ctx.copy()
            ctx_sale_search['search_by_user_sale'] = True

            self.assign_warehouse_to_user(self.operator_user_2.id, 'TEST_P')
            extended_tasks = self.sale_model.sudo(self.operator_user_2.id).with_context(ctx_sale_search).search([
                ('name','in',["VU17242173_2" + self.id_ext,"VU17242173" + self.id_ext])
            ])


            self.assign_warehouse_to_user(self.operator_user_2.id, 'TEST_V')
            extended_tasks = self.sale_model.sudo(self.operator_user_2.id).with_context(ctx_sale_search).search([
                ('name','in',["VU17242173_2" + self.id_ext,"VU17242173" + self.id_ext])
            ])
            self.assertEqual(len(extended_tasks), 2, 'Not enough or too many task found')
            self.assign_region_to_warehouse_by_name('Testinis Regionas 1', 'TEST_V')
            self.assign_region_to_user(self.operator_user_2.id, 'Testinis Regionas 1')
            self.operator_user_2.select_warehouse(False)

            extended_tasks = self.sale_model.sudo(self.operator_user_2.id).with_context(ctx_sale_search).search([
                ('name','in',["VU17242173_2" + self.id_ext,"VU17242173" + self.id_ext])
            ])
            self.assertEqual(len(extended_tasks), 2, 'Not enough or too many task found')

            route2 = self.create_route_from_sales(
                extended_tasks.with_context(search_by_user_sale=False), self.operator_user_2.id, 'out'
            )


            # Tarpinio sandėlio priskyrimas

            wiz_action = route2.with_context(
                search_by_user_sale=False
            ).sudo(
                self.operator_user_2.id
            ).action_assign_intermediate_route()

            self.assertIsInstance(wiz_action.get('res_id', False), int, 'No Wizard Created')
            wizard = self.env['stock.route.release.select_intermediate_warehouse.osv'].browse(wiz_action['res_id'])
            wizard.write({
                'intermediate_warehouse_id': self.warehouse_model.with_context(get_all_warehouses=True).search([
                    ('code','=','TEST_P')
                ], limit=1).id
            })
            wizard2_action = wizard.release()
            self.assertIsInstance(wizard2_action.get('res_id', False), int, 'No Wizard 2 Created')
            wizard2 = self.env['stock.route.release.select_intermediate.step2.osv'].browse(wizard2_action['res_id'])
            wizard2.selected_sale_ids.write({
                'boolean_for_intermediate_wizard': False
            })
            wizard2.selected_sale_ids.filtered(lambda task: task.warehouse_id == task.shipping_warehouse_id)[0].write({
                'boolean_for_intermediate_wizard': True
            })
            wizard2.release_and_quit()
            self.assertEqual(route2.type, 'mixed', 'Wrong Rotue Type')
            self.assertEqual(
                len(route2.sale_ids.filtered(lambda task: task.warehouse_id != task.shipping_warehouse_id)), 1,
                'Warehouse not assigned'
            )

            # Kito Tarpinio sandėlio priskyrimas

            wiz_action = route2.with_context(
                search_by_user_sale=False
            ).sudo(
                self.operator_user_2.id
            ).action_assign_intermediate_route()

            self.assertIsInstance(wiz_action.get('res_id', False), int, 'No Wizard Created')
            wizard = self.env['stock.route.release.select_intermediate_warehouse.osv'].browse(wiz_action['res_id'])
            wizard.write({
                'intermediate_warehouse_id': self.warehouse_model.with_context(get_all_warehouses=True).search([
                    ('code','=','TEST_S')
                ], limit=1).id
            })
            wizard2_action = wizard.release()
            self.assertIsInstance(wizard2_action.get('res_id', False), int, 'No Wizard 3 Created')
            wizard2 = self.env['stock.route.release.select_intermediate.step2.osv'].browse(wizard2_action['res_id'])
            wizard2.selected_sale_ids.write({
                'boolean_for_intermediate_wizard': False
            })
            wizard2.selected_sale_ids.filtered(lambda task: task.warehouse_id == task.shipping_warehouse_id)[0].write({
                'boolean_for_intermediate_wizard': True
            })
            wizard2.release_and_quit()
            self.assertEqual(route2.type, 'mixed', 'Wrong Rotue Type')
            self.assertEqual(
                len(route2.sale_ids.filtered(lambda task: task.warehouse_id != task.shipping_warehouse_id)), 2,
                'Warehouse not assigned'
            )

            # antro maršruto išleidimas
            self.assign_products_to_route(route2, self.operator_user_2.id, qty_to_add_to_route)
            self.assign_driver_to_route(route2, 'test_code' + self.id_ext, self.operator_user_2.id)
            self.release_route(route2, self.operator_user_2.id, True)
            # {'search_default_current': 1, 'search_by_user': True, 'search_by_user_type': 'incoming',
            #  'search_by_user_sale': False}

            # antro maršruto priėmimas
            self.assign_warehouse_to_user(self.operator_user_3.id, 'TEST_K')
            route_to_receive = self.route_model.sudo(self.operator_user_3.id).with_context(
                search_by_user_type='incoming', search_by_user=True
            ).search([('id','=',route2.id)])
            self.assertEqual(route_to_receive, self.route_model.browse([]), 'Wrong Route to Receive')


            self.assign_warehouse_to_user(self.operator_user_3.id, 'TEST_P')
            route_to_receive = self.route_model.sudo(self.operator_user_3.id).with_context(
                search_by_user_type='incoming', search_by_user=True
            ).search([('id','=',route2.id)])
            self.assertEqual(route_to_receive, route2, 'Wrong Route to Receive')

            extended_tasks = self.sale_model.sudo(self.operator_user_3.id).with_context(ctx_sale_search).search([
                ('name', 'in', ["VU17242173_2" + self.id_ext, "VU17242173" + self.id_ext])
            ])
            self.assertEqual(len(extended_tasks), 1, 'Wrong found task count')
            # konteinerių gavimas
            # route_to_receive = self.route_model.sudo(self.operator_user_2.id).browse(route.id)
            self.assertEqual(route_to_receive.state_receive, 'released', 'Bad Receive State. Should be released')
            receive_result = route_to_receive.action_receive()
            receive_wiz_env = self.env['stock.route.receive.osv']
            receive_wiz = receive_wiz_env.sudo(self.operator_user_3.id).browse(receive_result['res_id'])
            receive_lines = receive_wiz.line_ids
            self.assertEqual(len(receive_lines), len(route_to_receive.sale_ids.mapped('shipping_warehouse_id')), 'Not enough or too much of receive wizard lines')
            self.assertEqual(len(receive_lines.filtered('check_all')), 1, 'No line is marked as local warehouse')
            receive_wiz.line_ids.write({'check_all': False})
            not_to_receive = receive_wiz.line_ids.filtered(lambda line: line.shipping_warehouse_id.code == 'TEST_P').mapped('container_ids')
            not_to_receive.action_wizard_not_receive()
            receive_wiz.line_ids.filtered(lambda line: line.shipping_warehouse_id.code != 'TEST_P').mapped('container_ids').action_wizard_receive()
            receive_wiz.receive()
            self.assertEqual(route_to_receive.state_receive, 'closed', 'Bad Receive State. Should be closed')
            self.assertEqual(route_to_receive.state, 'closed', 'Bad Receive State. Should be closed')
            self.assertEqual(
                set(route_to_receive.container_line_ids.mapped('state')),
                {'not_received', 'received'}, 'Container states are wrong')

            extended_tasks = self.sale_model.sudo(self.operator_user_3.id).with_context(ctx_sale_search).search([
                ('name', 'in', ["VU17242173_2" + self.id_ext, "VU17242173" + self.id_ext])
            ])
            self.assertEqual(len(extended_tasks), 1, 'Wrong found task count ' + str(extended_tasks.mapped('name')))
            not_received_containers = self.container_model.sudo(self.operator_user_3.id).with_context(not_received_containers=True).search([])
            self.assertEqual(not_received_containers, not_to_receive, 'Do not see not received container')

            self.assign_warehouse_to_user(self.operator_user_3.id, 'TEST_V')
            not_received_containers = self.container_model.sudo(self.operator_user_3.id).with_context(not_received_containers=True).search([])
            self.assertEqual(not_received_containers, not_to_receive, 'Do not see not received container')

            not_received_containers.sudo(self.operator_user_3.id).action_receive_not_received_container()

            extended_tasks = self.sale_model.sudo(self.operator_user_3.id).with_context(ctx_sale_search).search([
                ('name', 'in', ["VU17242173_2" + self.id_ext, "VU17242173" + self.id_ext])
            ])
            self.assertEqual(len(extended_tasks), 1, 'Wrong found task count')

