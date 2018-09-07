# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################
from odoo.addons.config_sanitex_delivery.tests.test_warehouse import TestWarehouses

class TestRegions(TestWarehouses):

    def create_region(self, vals):
        return self.region_env.create(vals)

    def assign_region_to_user2(self, user_id, region_name):
        user = self.res_user_model.browse(user_id)
        reg = self.region_env.sudo(user_id).search([
            ('name','=',region_name),
            ('id','in',[reg_tuple[0] for reg_tuple in self.res_user_model.sudo(user_id).get_available_regions() \
                if isinstance(reg_tuple[0], int)]
            )
        ])
        self.assertEqual(len(reg), 1, 'User can\'t find region with name %s' % region_name)
        user.select_region(reg.id)
        self.assertEqual(user.default_region_id, reg, 'Default region not set')
        if user.default_warehouse_id:
            self.assertEqual(1, 2, 'Priskiriant regioną turi nusiimti sandėlis')
            # self.assertEqual(user.default_warehouse_id, reg.warehouse_of_region_ids & user.default_warehouse_id,
            #                  'Warehouse does not belong to region')


    def assign_location_to_warehouse(self, driver_code, region_name):
        driver = self.location_model.search([('driver_code','=',driver_code)])
        reg = self.region_env.search([
            ('name','=',region_name),
        ])
        reg.write({'driver_ids': [(4, driver.id)]})

    def assign_region_to_warehouse(self, region, wh_code):
        warehouse = self.warehouse_model.search([('code','=',wh_code)], limit=1)
        region.write({'warehouse_of_region_ids': [(4, warehouse.id)]})
        self.assertEqual(warehouse.product_ids, region.product_ids & warehouse.product_ids, 'Wrong Products in Region')
        self.assertEqual(warehouse.responsible_user_ids, region.responsible_user_ids & warehouse.responsible_user_ids, 'Wrong Users in Region')
        if not region.location_id:
            region.write({'location_id': warehouse.wh_output_stock_loc_id.id})

    def assign_region_to_warehouse_by_name(self, region_name, wh_code):
        reg = self.region_env.search([
            ('name', '=', region_name),
        ])
        return self.assign_region_to_warehouse(reg, wh_code)

    def test_5700_region(self):
        if self.do_regions:
            print('test_5700_region')
            region = self.create_region({'name': 'TEST_REG_V'})
            self.assign_region_to_warehouse(region, 'TEST_V')

            self.assign_warehouse_to_user(self.operator_user.id, 'TEST_V')
            self.assign_region_to_user2(self.operator_user.id, 'TEST_REG_V')

            self.operator_user.select_region(False)
            self.assign_warehouse_to_user(self.operator_user.id, 'TEST_K')
            self.assign_region_to_user2(self.operator_user.id, 'TEST_REG_V')

            self.assign_location_to_warehouse('test_code' + self.id_ext, 'Testinis Regionas 1')
            no_driver = self.location_model.sudo(self.operator_user.id).with_context(drivers_allowed_in_region=True).search([
                ('driver_code', '=', 'test_code' + self.id_ext)
            ])
            self.assertEqual(len(no_driver), 0, 'Driver should be invisible')
            self.assign_location_to_warehouse('test_code' + self.id_ext, 'TEST_REG_V')
            driver = self.location_model.sudo(self.operator_user.id).with_context(drivers_allowed_in_region=True).search([
                ('driver_code', '=', 'test_code' + self.id_ext)
            ])
            self.assertEqual(len(driver), 1, 'Driver should visible')

