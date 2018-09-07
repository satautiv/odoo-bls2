# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################
from odoo.addons.config_sanitex_delivery.tests.test_location import TestLocations

class TestProducts(TestLocations):

    def create_product(self, list_of_vals):
        a = self.product_model.with_context({'no_commit': True}).create_packing(list_of_vals)
        self.intermediate_model.with_context({'no_commit': True}).browse([a]).process_intermediate_objects()
        products = self.product_model.search([('intermediate_id','=',a)])
        if not products:
            intermediate = self.intermediate_model.browse(a)
            self.assertEqual(1, 2, 'No Product Created' + intermediate.traceback_string)
        for vals in list_of_vals:
            if vals.get('external_supplier_id', False):
                product = products.filtered(lambda prod_rec: prod_rec.external_product_id == vals['external_product_id'])
                self.assertEqual(vals['external_supplier_id'], product.supplier_id.external_customer_id,
                    'Sukurtam produktui užsidėjo blogas tiekėjas'
                )

    def test_4000_product_import(self):
        if self.do_product:
            print('test_4000_product_import')
            product_vals = {
                "product_type": "pakuotė",
                "product_standart_price": 2.6, 
                "external_owner_id": 'unit-test-' + self.id_ext, 
                "product_default_code": "test-V501J28" + self.id_ext, 
                "firm_id": "BL", 
                "external_product_id": "test-BL-V501J28" + self.id_ext, 
                "owner_code": 'UTEST' + self.id_ext, 
                "active": "Y", 
                "product_name": "Dėžė Eur 01", 
                "product_weight": 0.51,
                "external_supplier_id": "TESTTIEK",
            } 
            product_vals2 = {
                "product_type": "pakuotė",
                "product_standart_price": 0.0, 
                "external_owner_id": 'unit-test-' + self.id_ext, 
                "product_default_code": "test-V501J58" + self.id_ext, 
                "firm_id": "BL", 
                "external_product_id": "test-BL-V501J58" + self.id_ext, 
                "owner_code": 'UTEST' + self.id_ext, 
                "active": "Y", 
                "product_name": "Dėžė Eur 02", 
                "product_weight": 0.55
            }
            product_vals3 = {
                "product_type": "pakuotė",
                "product_standart_price": 0.0, 
                "external_owner_id": 'unit-test-' + self.id_ext, 
                "product_default_code": "test-V511608" + self.id_ext, 
                "firm_id": "BL", 
                "external_product_id": "test-BL-V511608" + self.id_ext, 
                "owner_code": 'UTEST' + self.id_ext, 
                "active": "Y", 
                "product_name": "Kibinai su mėsos įdaru, šaldyti, kepti, 7 vnt.", 
                "product_weight": 0.86
            }
            product_vals4 = {
                "product_type": "pakuotė",
                "product_standart_price": 0.0,
                "external_owner_id": 'unit-test-' + self.id_ext,
                "product_default_code": "test-V517518" + self.id_ext,
                "firm_id": "BL",
                "external_product_id": "test-BL-V517518" + self.id_ext,
                "owner_code": 'UTEST' + self.id_ext,
                "active": "Y",
                "product_name": "Tara kurioje laikomas auksas.",
                "product_weight": 1.86
            }
            self.create_product([product_vals, product_vals2, product_vals3, product_vals4])