# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################
from odoo.addons.config_sanitex_delivery.tests.test_packages import TestPackages
# from openerp.osv import osv

class TestCorrections(TestPackages):


    def setUp(self):
        super(TestCorrections, self).setUp()
        # self.do_routes = False
        # self.do_owner = True
        # self.do_product = True
        # self.do_sales = True
        # self.do_partner = True
        # self.do_location = True
        # self.do_warehouse = True
        # self.do_packages = False
        # self.do_corrections = True
        # self.do_regions = True

    def create_correction(self, vals, user):
        def_vals = self.correction_env.sudo(user).default_get(self.correction_env._fields)
        self.assertEqual(
            user.default_warehouse_id.id, def_vals['return_to_warehouse_id'],
            'Warehouse in Correction was not set automatically'
        )
        def_vals.update(vals)
        correction = self.correction_env.create(def_vals)
        correction.on_change_warehouse()
        self.assertEqual(correction.stock_source_location_id, user.default_warehouse_id.wh_output_stock_loc_id,
            'Source location in correction was not correctly set'
        )
        self.assertEqual(correction.stock_return_location_id, user.default_warehouse_id.wh_return_stock_loc_id,
            'Return location in correction was not correctly set'
        )
        return correction

    def fill_in_correction_lines(self, correction, line_qty):
        correction.button_generate_lines()
        self.assertEqual(
            correction.location_id.get_drivers_debt_all().mapped('product_id') | correction.return_to_warehouse_id.product_ids,
            correction.line_ids.mapped('product_id'), 'Products are missing after line generation (or too many)'
        )
        correction.line_ids.write({'correction_qty': line_qty})

    def confirm_corerction(self, correction):
        drivers_debt = {}
        for line in correction.line_ids:
            drivers_debt[line.product_id.id] = correction.location_id.get_drivers_debt(line.product_id.id)
        correction.action_done()
        for line in correction.line_ids:
            self.assertEqual(drivers_debt[line.product_id.id] + line.correction_qty,
                correction.location_id.get_drivers_debt(line.product_id.id),
                'Drivers debt does not match'
            )

    def test_6500_stock_correction(self):
        if self.do_corrections:
            self.assign_warehouse_to_user(self.operator_user.id, 'TEST_V')
            driver = self.location_model.sudo(self.operator_user.id).with_context(
                drivers_allowed_in_region=True
            ).search([
                ('driver_code', '=', 'test_code' + self.id_ext)
            ])
            correction_vals = {
                'location_id': driver.id,
                'reason': 'transfer_to_driver'
            }
            # self

            correction = self.create_correction(correction_vals, self.operator_user)
            self.fill_in_correction_lines(correction, 10)
            self.confirm_corerction(correction)

            correction_vals = {
                'location_id': driver.id,
                'reason': 'tare_return'
            }
            # self

            correction = self.create_correction(correction_vals, self.operator_user)
            correction.write({'stock_return_location_id': correction.return_to_warehouse_id.wh_output_stock_loc_id.id})
            self.fill_in_correction_lines(correction, -10)
            for line in correction.line_ids:
                if line.product_id.external_product_id == "test-BL-V517518" + self.id_ext:
                    line.write({'correction_qty': 0})
            self.confirm_corerction(correction)
            self.assertEqual(correction.picking_to_warehouse_ids[0].move_lines[0].location_dest_id,
                correction.return_to_warehouse_id.wh_output_stock_loc_id,
                'Wrong Destination Location'
            )