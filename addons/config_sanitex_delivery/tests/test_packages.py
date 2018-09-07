# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################
from odoo.addons.config_sanitex_delivery.tests.test_sales import TestSales

class TestPackages(TestSales):
    
    def test_5500_package_import(self):
        if self.do_packages:
            pass
#             #kuriamas pirmas pardavimas
#             package_vals = {
#                 "sender_address_zip": "", 
#                 "external_buyer_address_id": "2021834", 
#                 "delivery_date": "2017-05-26", 
#                 "buyer_name": "UAB \"Arborita\"", 
#                 "container": [
#                   {
#                     "package_nr": "VVSE_70525_610", 
#                     "external_container_id": "102069-VSV1617", 
#                     "package_weight": 30.0
#                   }
#                 ], 
#                 "buyer_address": "Sodų skg.10-34, Mažeikiai", 
#                 "internal_order_number": "VSV1617", 
#                 "packet_date": "2017-05-25", 
#                 "timestamp": "0x00000000E871B95E", 
#                 "external_packet_id": "102069-VSV1617", 
#                 "buyer_address_zip": "", 
#                 "sender_address": "Ąžuolo 2, Veiveriai, Prienų r.", 
#                 "sender_name": "VVS", 
#                 "sender_address_country": "LTU", 
#                 "buyer_address_country": "LTU", 
#                 "orignal_packet_number": "VVSE_70525_610", 
#                 "packet_temp_mode": "termo", 
#                 "owner_id": "75", 
#                 "documents": [
#                   {
#                     "external_document_id": "VSV1617", 
#                     "document_number": "VSV1617", 
#                     "document_type": "Invoice", 
#                     "firm_id": "BL", 
#                     "warehouse_id": "VU1"
#                   }
#                 ], 
#                 "external_buyer_id": "1301235", 
#                 "external_sender_id": "1600069"
#             }
#             
#             
#             
#             intermediate_id = self.sale_model.with_context({'no_commit': True}).CreateOrder([sale_vals])
#             self.intermediate_model.with_context({'no_commit': True}).browse([intermediate_id]).process_intermediate_objects()
#             sales = self.sale_model.search([('intermediate_id','=',intermediate_id)])
#             if not sales:
#                 intermediate = self.intermediate_model.browse(intermediate_id)
#                 self.assertEqual(1, 2, 'No Sale' + intermediate.traceback)
#             self.assertEqual(len(sales.mapped('container_ids')), 1, 'No Containers')
#             self.assertEqual(len(sales.mapped('transportation_order_id')), 1, 'No Transportation Order')