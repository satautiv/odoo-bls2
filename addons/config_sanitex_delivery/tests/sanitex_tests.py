# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################
from odoo.tests.common import SingleTransactionCase
from odoo import SUPERUSER_ID

import time


class SanitexTesting(SingleTransactionCase):

    """Tests for different type of user 'Accountant/Adviser' and added groups"""

    post_install = True
    at_install = False
    
    def setUp(self):
        super(SanitexTesting, self).setUp()
        self.res_user_model = self.env['res.users']
        self.product_owner_model = self.env['product.owner']
        self.product_model = self.env['product.product']
        self.company_model = self.env['res.company']
        self.sale_model = self.env['sale.order']
        self.sale_line_model = self.env['sale.order.line']
        self.intermediate_model = self.env['stock.route.integration.intermediate']
        self.route_model = self.env['stock.route']
        self.location_model = self.env['stock.location']
        self.partner_model = self.env['res.partner']
        self.warehouse_model = self.env['stock.warehouse']
        self.region_model = self.env['stock.region']
        self.container_model = self.env['account.invoice.container']
        self.correction_env = self.env['stock.packing.correction']
        self.correction_Line_env = self.env['stock.packing.correction.line']
        self.region_env = self.env['stock.region']
        
        self.do_warehouse = False
        self.do_owner = False
        self.do_product = False
        self.do_sales = False
        self.do_routes = False
        self.do_location = False
        self.do_partner = False
        self.do_packages = False
        self.do_corrections = False
        self.do_regions = False
        
        self.id_ext = '7'
        
        self.main_company = self.env.ref('base.main_company')
        
        self.res_users_route_operator = self.env.ref('config_sanitex_delivery.stock_route_operator_group')
        self.user_group = self.env.ref('base.group_user')
        self.region_group = self.env.ref('config_sanitex_delivery.stock_route_region_group')
        
        
        self.admin_id = SUPERUSER_ID
        self.operator_user = False

        self.warehouse_1 = False
        self.warehouse_2 = False
        self.today = time.strftime('%Y-%m-%d')

        if self.res_user_model.search([('login', '=', 'op_test')]):
            self.operator_user = self.res_user_model.search([('login', '=', 'op_test')])[0]
        else:
            self.operator_user = self.res_user_model.with_context({'no_reset_password': True}).create(dict(
                name="Operator",
                company_id=self.main_company.id,
                login="op_test",
                email="op_test@sanitex.lt",
                groups_id=[(6, 0, [self.res_users_route_operator.id, self.user_group.id, self.region_group.id])]
            ))

        if self.res_user_model.search([('login', '=', 'op2_test')]):
            self.operator_user_2 = self.res_user_model.search([('login', '=', 'op2_test')])[0]
        else:
            self.operator_user_2 = self.res_user_model.with_context({'no_reset_password': True}).create(dict(
                name="Operator2",
                company_id=self.main_company.id,
                login="op2_test",
                email="op2_test@sanitex.lt",
                groups_id=[(6, 0, [
                    self.res_users_route_operator.id, self.user_group.id,
                    self.env.ref('config_sanitex_delivery.stock_route_region_group').id
                ])]
            ))

        if self.res_user_model.search([('login', '=', 'op3_test')]):
            self.operator_user_3 = self.res_user_model.search([('login', '=', 'op3_test')])[0]
        else:
            self.operator_user_3 = self.res_user_model.with_context({'no_reset_password': True}).create(dict(
                name="Operator3",
                company_id=self.main_company.id,
                login="op3_test",
                email="op3_test@sanitex.lt",
                groups_id=[(6, 0, [
                    self.res_users_route_operator.id, self.user_group.id,
                    self.env.ref('config_sanitex_delivery.stock_route_region_group').id
                ])]
            ))