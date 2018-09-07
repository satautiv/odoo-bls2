# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################
from odoo.addons.config_sanitex_delivery.tests.test_products import TestProducts

class TestWarehouses(TestProducts):


    def assign_warehouse_to_user(self, user_id, wh_code):
        user = self.res_user_model.browse(user_id)
        wh_k = self.warehouse_model.sudo(user_id).search([
            ('code','=',wh_code),
            ('id','in',[wh_tuple[0] for wh_tuple in self.res_user_model.sudo(user_id).get_available_warehouses() \
                if isinstance(wh_tuple[0], int)]
            )
        ])
        self.assertEqual(len(wh_k), 1, 'User can\'t find warehouse 1 with code %s' % wh_code)
        user.select_warehouse(wh_k.id)
        self.assertEqual(user.default_warehouse_id, wh_k, 'Default warehouse not set')
        if user.default_region_id:
            self.assertEqual(1, 2, 'Priskiriant sandėlį turi nusiimti regionas')

    def create_warehouse(self, vals):
        warehouse = self.warehouse_model.create(vals)
        self.assertEqual(
            vals['code'] + '1', warehouse.wh_output_stock_loc_id.code,
            'Turejo susikurti isleidimo vieta su kodu %s' %vals['code'] + '1'
        )
        self.assertEqual(
            vals['code'] + '6', warehouse.wh_return_stock_loc_id.code,
            'Turejo susikurti grazinimo vieta su kodu %s' %vals['code'] + '6'
        )
        self.assertEqual(
            vals['code'], warehouse.lot_stock_id.code,
            'Turejo susikurti sandeliavimo vieta su kodu %s' %vals['code']
        )
        self.assertEqual(
            'Q' + vals['code'], warehouse.sequence_for_route_id.prefix,
            'Turejo susikurti marsruto serija su prefixu %s' %('Q' + vals['code'])
        )
        self.assertEqual(
            'T' + vals['code'], warehouse.sequence_for_driver_picking_id.prefix,
            'Turejo susikurti taros akto serija su prefixu %s' %('T' + vals['code'])
        )
        self.assertEqual(
            'TK' + vals['code'][-1:], warehouse.sequence_for_client_packing_id.prefix,
            'Turejo susikurti sandeliavimo vieta su prefixu %s' %('TK' + vals['code'][:1])
        )
        self.assertEqual(
            vals['code'], warehouse.sequence_for_corection_id.prefix,
            'Turejo susikurti vidinės operacijos numeracija su prefixu %s' %vals['code']
        )
        return warehouse

    # def assign_products_to_warehouse(self, warehouse, products):
    #     warehouse.write({
    #         'product_ids': [(6, 0, [prod.id for prod in products])],
    #         'responsible_user_ids': [
    #             (6, 0, [self.operator_user.id, self.operator_user_2.id, self.admin_id, self.operator_user_3.id])]
    #     })


    def test_5000_create_warehouse(self):
        if self.do_warehouse:
            print('test_5000_create_warehouse')
            default_region_vals = self.region_model.default_get(self.region_model._fields)
            default_region_vals['name'] = 'Testinis Regionas 1'
            region1 = self.region_model.create(default_region_vals)


            default_warehouse_vals = self.warehouse_model.default_get(self.warehouse_model._fields)

            warehouse1_vals = default_warehouse_vals.copy()
            warehouse1_vals['name'] = 'TEST_V'
            warehouse1_vals['code'] = 'TEST_V'
            warehouse1_vals['region_id'] = region1.id
            warehouse1 = self.create_warehouse(warehouse1_vals)

            prods1 = self.product_model.search([
                ('external_product_id','in',[
                    "test-BL-V501J28" + self.id_ext,
                    "test-BL-V501J58" + self.id_ext,
                    "test-BL-V517518" + self.id_ext
                ])
            ])

            warehouse1.write({
                'product_ids': [(6, 0, [prod.id for prod in prods1])],
                'responsible_user_ids': [(6, 0, [self.operator_user.id, self.operator_user_2.id, self.admin_id, self.operator_user_3.id])]
            })

            self.assertEqual(warehouse1.product_ids, region1.product_ids, 'Products did not filled in region')
            self.assertEqual(warehouse1.responsible_user_ids, region1.responsible_user_ids, 'Users did not filled in region')
            region1.write({
                'location_id': warehouse1.wh_output_stock_loc_id.id
            })
            warehouse2_vals = default_warehouse_vals.copy()
            warehouse2_vals['name'] = 'TEST_K'
            warehouse2_vals['code'] = 'TEST_K'
            warehouse2 = self.create_warehouse(warehouse2_vals)

            prods2 = self.product_model.search([
                ('external_product_id','in',[
                    "test-BL-V511608" + self.id_ext,
                    "test-BL-V517518" + self.id_ext
                ])
            ])
            warehouse2.write({
                'product_ids': [(6, 0, [prod.id for prod in prods2])],
                'responsible_user_ids': [(6, 0, [self.operator_user.id, self.admin_id, self.operator_user_3.id])]
            })
            warehouse3_vals = default_warehouse_vals.copy()
            warehouse3_vals['name'] = 'TEST_P'
            warehouse3_vals['code'] = 'TEST_P'
            warehouse3 = self.create_warehouse(warehouse3_vals)

            prods3 = self.product_model.search([
                ('external_product_id','in',[
                    "test-BL-V511608" + self.id_ext
                ])
            ])
            warehouse3.write({
                'product_ids': [(6, 0, [prod.id for prod in prods3])],
                'responsible_user_ids': [(6, 0, [self.operator_user_2.id, self.admin_id, self.operator_user_3.id])]
            })

            warehouse4_vals = default_warehouse_vals.copy()
            warehouse4_vals['name'] = 'TEST_S'
            warehouse4_vals['code'] = 'TEST_S'
            warehouse4 = self.create_warehouse(warehouse4_vals)

            prods4 = self.product_model.search([
                ('external_product_id','in',[
                    "test-BL-V511608" + self.id_ext
                ])
            ])
            warehouse4.write({
                'product_ids': [(6, 0, [prod.id for prod in prods4])],
                'responsible_user_ids': [(6, 0, [self.operator_user_2.id, self.admin_id, self.operator_user_3.id])]
            })