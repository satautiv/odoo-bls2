# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################
from odoo.addons.config_sanitex_delivery.tests.test_region import TestRegions

class TestSales(TestRegions):
    
    def test_6000_sale_import(self):
        if self.do_sales:
            #kuriamas pirmas pardavimas
            sale_vals = {
                "customer_region": "VIL",
                "transport_types": "P", 
                "order_lines": [{
                    "sale_order_line_qty": 40.0, 
                    "sale_order_line_uom": "vnt.", 
                    "external_product_id": "test-BL-V501J28" + self.id_ext, 
                    "external_sale_order_line_id": "test-BL-VUS-7242173-V44721L" + self.id_ext,
                    "product_code": "test-V501J28" + self.id_ext, 
                    "product_name": "Dėžė Eur 01"
                }, 
                {
                    "sale_order_line_qty": 0.3, 
                    "sale_order_line_uom": "kg", 
                    "external_product_id": "test-BL-V501J58" + self.id_ext, 
                    "external_sale_order_line_id": "test-BL-VUS-7242173-V50A971" + self.id_ext,
                    "product_code": "test-V501J58" + self.id_ext, 
                    "product_name": "Dėžė Eur 02"
                }, 
                {
                    "sale_order_line_qty": 2.0, 
                    "sale_order_line_uom": "kg", 
                    "external_product_id": "test-BL-V511608" + self.id_ext, 
                    "external_sale_order_line_id": "test-BL-VUS-7242173-V50H55N" + self.id_ext,
                    "product_code": "test-V511608" + self.id_ext, 
                    "product_name": "Kibinai su mėsos įdaru, šaldyti, kepti, 7 vnt."
                }
                ],
                "external_buyer_address_id": "test-1665701" + self.id_ext, 
                "alcohol": False,
                "state": "open",
                "shiping_date": self.today,
                "owner_id": 'unit-test-' + self.id_ext,
                "direction": "VITR-9_VILNIUS_SIAURE-ZIRMUNAI",
                "firm_id": "BL",
                "external_customer_id": "test-5464" + self.id_ext,
                "document_name": "VU17242173" + self.id_ext,
                "order_type": "order",
                "tobacco": False,
                "external_customer_address_id": "test-1665701" + self.id_ext,
                "cash": False,
                "external_sale_order_id": "test-1003-3275690-VU17242173" + self.id_ext, 
                "picking_warehouse_id": "TEST_K1"
            }
            intermediate_id = self.sale_model.with_context({'no_commit': True}).CreateOrder([sale_vals])
            self.intermediate_model.with_context({'no_commit': True}).browse([intermediate_id]).process_intermediate_objects()
            sales = self.sale_model.search([('intermediate_id','=',intermediate_id)])
            if not sales:
                intermediate = self.intermediate_model.browse(intermediate_id)
                self.assertEqual(1, 2, 'No Sale' + intermediate.traceback_string)
            self.assertEqual(len(sales.mapped('container_ids')), 1, 'No Containers')
            self.assertEqual(len(sales.mapped('transportation_order_id')), 1, 'No Transportation Order')
                
                
            #kuriamas antras pardavimas
            sale_vals = {
                "customer_region": "VIL",
                "transport_types": "P", 
                "order_lines": [{
                    "sale_order_line_qty": 1.0, 
                    "sale_order_line_uom": "vnt.", 
                    "external_product_id": "test-BL-V501J28" + self.id_ext, 
                    "external_sale_order_line_id": "test-BL-VUS-7242173-V44721L_2" + self.id_ext,
                    "product_code": "test-V501J28" + self.id_ext, 
                    "product_name": "Dėžė Eur 01"
                }, 
                {
                    "sale_order_line_qty": 3.0, 
                    "sale_order_line_uom": "kg", 
                    "external_product_id": "test-BL-V501J58" + self.id_ext, 
                    "external_sale_order_line_id": "test-BL-VUS-7242173-V50A971_2" + self.id_ext,
                    "product_code": "test-V501J58" + self.id_ext, 
                    "product_name": "Dėžė Eur 02"
                }, 
                {
                    "sale_order_line_qty": 52.0, 
                    "sale_order_line_uom": "kg", 
                    "external_product_id": "test-BL-V511608" + self.id_ext, 
                    "external_sale_order_line_id": "test-BL-VUS-7242173-V50H55N_2" + self.id_ext,
                    "product_code": "test-V511608" + self.id_ext, 
                    "product_name": "Kibinai su mėsos įdaru, šaldyti, kepti, 7 vnt."
                }
                ],
                "external_buyer_address_id": "test-1665700" + self.id_ext, 
                "alcohol": False,
                "state": "open",
                "shiping_date": self.today,
                "owner_id": 'unit-test-' + self.id_ext,
                "direction": "VITR-9_VILNIUS_SIAURE-ZIRMUNAI",
                "firm_id": "BL",
                "external_customer_id": "test-18960" + self.id_ext,
                "document_name": "VU17242173_2" + self.id_ext,
                "order_type": "order",
                "tobacco": False,
                "external_customer_address_id": "test-1665700" + self.id_ext,
                "cash": False,
                "external_sale_order_id": "test-1003-3275690-VU17242173_2" + self.id_ext, 
                "picking_warehouse_id": "TEST_K1"
            }
            intermediate_id = self.sale_model.with_context({'no_commit': True}).CreateOrder([sale_vals])
            self.intermediate_model.with_context({'no_commit': True}).browse([intermediate_id]).process_intermediate_objects()
            sales = self.sale_model.search([('intermediate_id','=',intermediate_id)])
            if not sales:
                intermediate = self.intermediate_model.browse(intermediate_id)
                self.assertEqual(1, 2, 'No Sale 2' + intermediate.traceback_string)
            self.assertEqual(len(sales.mapped('container_ids')), 1, 'No Containers')
            self.assertEqual(len(sales.mapped('transportation_order_id')), 1, 'No Transportation Order')
                
                
            #kuriamas trečias pardavimas
            sale_vals = {
                "customer_region": "VIL",
                "transport_types": "P", 
                "order_lines": [{
                    "sale_order_line_qty": 1.0, 
                    "sale_order_line_uom": "vnt.", 
                    "external_product_id": "test-BL-V501J28" + self.id_ext, 
                    "external_sale_order_line_id": "test-BL-VUS-7242173-V44721L_3" + self.id_ext,
                    "product_code": "test-V501J28" + self.id_ext, 
                    "product_name": "Dėžė Eur 01"
                }, 
                {
                    "sale_order_line_qty": 3.0, 
                    "sale_order_line_uom": "kg", 
                    "external_product_id": "test-BL-V501J58" + self.id_ext, 
                    "external_sale_order_line_id": "test-BL-VUS-7242173-V50A971_3" + self.id_ext,
                    "product_code": "test-V501J58" + self.id_ext, 
                    "product_name": "Dėžė Eur 02"
                }, 
                {
                    "sale_order_line_qty": 52.0, 
                    "sale_order_line_uom": "kg", 
                    "external_product_id": "test-BL-V511608" + self.id_ext, 
                    "external_sale_order_line_id": "test-BL-VUS-7242173-V50H55N_3" + self.id_ext,
                    "product_code": "test-V511608" + self.id_ext, 
                    "product_name": "Kibinai su mėsos įdaru, šaldyti, kepti, 7 vnt."
                }
                ],
                "external_buyer_address_id": "test-1665702" + self.id_ext, 
                "alcohol": False,
                "state": "open",
                "shiping_date": self.today,
                "owner_id": 'unit-test-' + self.id_ext,
                "direction": "VITR-9_VILNIUS_SIAURE-ZIRMUNAI",
                "firm_id": "BL",
                "external_customer_id": "test-18961" + self.id_ext,
                "document_name": "VU17242173_3" + self.id_ext,
                "order_type": "order",
                "tobacco": False,
                "external_customer_address_id": "test-1665702" + self.id_ext,
                "cash": False,
                "external_sale_order_id": "test-1003-3275690-VU17242173_3" + self.id_ext, 
                "picking_warehouse_id": "TEST_K1"
            }
            intermediate_id = self.sale_model.with_context({'no_commit': True}).CreateOrder([sale_vals])
            self.intermediate_model.with_context({'no_commit': True}).browse([intermediate_id]).process_intermediate_objects()
            sales = self.sale_model.search([('intermediate_id','=',intermediate_id)])
            if not sales:
                intermediate = self.intermediate_model.browse(intermediate_id)
                self.assertEqual(1, 2, 'No Sale 3' + intermediate.traceback_string)
            self.assertEqual(len(sales.mapped('container_ids')), 1, 'No Containers')
            self.assertEqual(len(sales.mapped('transportation_order_id')), 1, 'No Transportation Order')