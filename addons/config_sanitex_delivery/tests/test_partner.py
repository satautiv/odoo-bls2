# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################
from odoo.addons.config_sanitex_delivery.tests.test_owners import TestOwners

class TestPartners(TestOwners):

    def create_client(self, list_of_vals):
        intermediate_id = self.partner_model.with_context({'no_commit': True}).CreateClient(list_of_vals)
        self.intermediate_model.with_context({'no_commit': True}).browse([intermediate_id]).process_intermediate_objects()
        clients = self.partner_model.search([('intermediate_id','=',intermediate_id)])
        if not clients:
            intermediate = self.intermediate_model.browse(intermediate_id)
            self.assertEqual(1, 2, 'No Drivers Org' + intermediate.traceback_string)

    def create_posid(self, list_of_vals):
        intermediate_id = self.partner_model.with_context({'no_commit': True}).CreatePOSID(list_of_vals)
        self.intermediate_model.with_context({'no_commit': True}).browse([intermediate_id]).process_intermediate_objects()
        posids = self.partner_model.search([('intermediate_id','=',intermediate_id)])
        if not posids:
            intermediate = self.intermediate_model.browse(intermediate_id)
            self.assertEqual(1, 2, 'No Drivers Org' + intermediate.traceback_string)


    def test_2000_drivers_company(self):
        if self.do_partner:
            print('test_2000_drivers_company')
            driver_comp_vals = {
                "customer_vat": "GB906606626", 
                "address_phone": "", 
                "address_city": "", 
                "type": "1", 
                "address_street": "", 
                "external_customer_id": "Test-901363" + self.id_ext, 
                "customer_active": "Y", 
                "address_zipcode": "", 
                "company_id": "BL", 
                "address_region": "", 
                "address_fax": "",
                "address": "7&8 Walkers Green, Marden, Hereford", 
                "customer_ref": "38002190141", 
                "address_country": "LTU", 
                "customer_name": "Vežėjų įmonė"
            }
            self.create_client([driver_comp_vals])
                
    
    def test_2001_client_import(self):
        if self.do_partner:
            print('test_2001_client_import')
            client_1_vals = {
                "customer_vat": "614185515", 
                "address_phone": "8347-519570", 
                "address_city": "", 
                "type": "1", 
                "address_street": "", 
                "external_customer_id": "test-5464" + self.id_ext, 
                "customer_active": "Y", 
                "address_zipcode": "", 
                "company_id": "BL", 
                "address_region": "", 
                "address_fax": "8347-54281",
                "address": "J.Basanavičiaus g. 95, Kėdainiai", 
                "customer_ref": "161418556", 
                "address_country": "LTU", 
                "customer_name": 'UAB "SIBENA"'
            }
            client_2_vals = {
                "customer_vat": "648098113", 
                "address_phone": "8 459 44186", 
                "address_city": "", 
                "type": "1", 
                "address_street": "", 
                "external_customer_id": "test-18960" + self.id_ext, 
                "customer_active": "Y", 
                "address_zipcode": "", 
                "company_id": "BL", 
                "address_region": "", 
                "address_fax": "8681-39662", 
                "address": "Skapiškio g.2,Šimonių k.Kupiškis", 
                "customer_ref": "264809810", 
                "address_country": "LTU", 
                "customer_name": 'M.Vilnonienės įmonė"Dainorita"'
            }
            client_3_vals = {
                "customer_vat": "648098114",
                "address_phone": "8 459 44187",
                "address_city": "",
                "type": "1",
                "address_street": "",
                "external_customer_id": "test-18961" + self.id_ext,
                "customer_active": "Y",
                "address_zipcode": "",
                "company_id": "BL",
                "address_region": "",
                "address_fax": "8681-39663",
                "address": "Skapiškio g.3,Šimonių k.Kupiškis",
                "customer_ref": "264809811",
                "address_country": "LTU",
                "customer_name": 'M.Vilnonienės įmonė"Dainorita"'
            }
            supplier_1_vals = {
                "partner_active": "Y",
                "type": "1",
                "partner_ref": "test-744754",
                "owners": [],
                "supplier_code": "TST",
                "address_country": "LTU",
                "partner_type": "supplier",
                "partner_vat": "LT856541265",
                "partner_name": 'AB "TEST Tiekėjas"',
                "company_id": "BL",
                "address": "Registracijos: Metalo g.5, LT-28216, Utena Faktinis adresas: Narkūnai, Utena LT-28104  Lietuva",
                "external_partner_id": "TESTTIEK",
                "timestamp": "0x0000A881009B96DC"
            }
            self.create_client([client_1_vals,client_2_vals, client_3_vals, supplier_1_vals])
                
                
    def test_2002_posid_import(self):
        if self.do_partner:
            print('test_2002_posid_import')
            posid_1_vals = {
                "buyer_address_name": "", 
                "external_buyer_address_id": "test-1665701" + self.id_ext, 
                "owners": [],
                "buyer_address_district": "", 
                "buyer_address": "Palaukės g 6-0, Vilniaus rajonas, Vilniaus raj.", 
                "buyer_address_fax": "", 
                "buyer_address_zip": "14168", 
                "buyer_address_active": "Y", 
                "buyer_address_possid_code": "test-1665701" + self.id_ext, 
                "buyer_address_city": "Vilniaus rajona", 
                "buyer_address_phone": "", 
                "buyer_address_contact": "", 
                "buyer_address_region": ".", 
                "external_customer_id": "test-5464" + self.id_ext, 
                "buyer_address_street": ""
            }
            posid_2_vals = {
                "buyer_address_name": "", 
                "external_buyer_address_id": "test-1665700" + self.id_ext, 
                "owners": [], 
                "buyer_address_district": "", 
                "buyer_address": "Fabijoniškių g 2-15, Vilnius", 
                "buyer_address_fax": "", 
                "buyer_address_zip": "07109", 
                "buyer_address_active": "Y", 
                "buyer_address_possid_code": "test-1665700" + self.id_ext, 
                "buyer_address_city": "Vilnius", 
                "buyer_address_phone": "", 
                "buyer_address_contact": "", 
                "buyer_address_region": ".", 
                "external_customer_id": "test-18960" + self.id_ext, 
                "buyer_address_street": ""
            }
            posid_3_vals = {
                "buyer_address_name": "", 
                "external_buyer_address_id": "test-1665702" + self.id_ext, 
                "owners": [], 
                "buyer_address_district": "", 
                "buyer_address": "Fabijoniškių g 3-16, Vilnius", 
                "buyer_address_fax": "", 
                "buyer_address_zip": "07110", 
                "buyer_address_active": "Y", 
                "buyer_address_possid_code": "test-1665702" + self.id_ext, 
                "buyer_address_city": "Vilnius", 
                "buyer_address_phone": "", 
                "buyer_address_contact": "", 
                "buyer_address_region": ".", 
                "external_customer_id": "test-18961" + self.id_ext, 
                "buyer_address_street": ""
            }
            self.create_posid([posid_1_vals,posid_2_vals,posid_3_vals])
            