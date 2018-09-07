# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################
from odoo.addons.config_sanitex_delivery.tests.test_partner import TestPartners

class TestLocations(TestPartners):

    def create_driver(self, vals):
        driver = self.location_model.create(vals)
        self.assertEqual(
            driver.driver, True,
            'Not a driver'
        )
        self.assertEqual(
            driver.usage, 'internal',
            'Not a internal location'
        )
        self.assertEqual(
            driver.owner_code, '38002190141',
            'No owner code'
        )
        return driver

    def test_3000_create_driver(self):
        if self.do_location:
            print('test_3000_create_driver')
            location_vals = self.location_model.default_get(self.location_model._fields)
            location_vals['name'] = 'Testas Testauskas'
            location_vals['driver_code'] = 'test_code' + self.id_ext
            location_vals['license_plate'] = 'ABC789'
            location_vals['driver'] = True
            location_vals['owner_id'] = self.partner_model.search([
                ('external_customer_id','=','Test-901363' + self.id_ext)
            ])[0].id
            self.create_driver(location_vals)

            location2_vals = self.location_model.default_get(self.location_model._fields)
            location2_vals['name'] = 'Jonas Valančiūnas'
            location2_vals['driver_code'] = 'test_code2' + self.id_ext
            location2_vals['license_plate'] = 'JVR789'
            location2_vals['driver'] = True
            location2_vals['owner_id'] = self.partner_model.search([
                ('external_customer_id','=','Test-901363' + self.id_ext)
            ])[0].id
            self.create_driver(location2_vals)

    
    def test_3001_create_locations(self):
        if self.do_location and False:
            default_location_vals = self.location_model.default_get(self.location_model._fields)
            
            location1_vals = default_location_vals.copy()
            location1_vals['name'] = 'TEST_V'
            location1_vals['code'] = 'TEST_V'
            location1_vals['location_id'] = 1
            location1 = self.location_model.create(location1_vals)
            
            location3_vals = default_location_vals.copy()
            location3_vals['name'] = 'TEST_V WH'
            location3_vals['code'] = 'TEST_V1'
            location3_vals['location_id'] = location1.id
            self.location_model.create(location3_vals)
            
            location2_vals = default_location_vals.copy()
            location2_vals['name'] = 'TEST_V RETURN'
            location2_vals['code'] = 'TEST_V_RET'
            location2_vals['location_id'] = location1.id
            self.location_model.create(location2_vals)
            
            
            location12_vals = default_location_vals.copy()
            location12_vals['name'] = 'TEST_K'
            location12_vals['code'] = 'TEST_K'
            location12_vals['location_id'] = 1
            location12 = self.location_model.create(location12_vals)
            
            location32_vals = default_location_vals.copy()
            location32_vals['name'] = 'TEST_K WH'
            location32_vals['code'] = 'TEST_K1'
            location32_vals['location_id'] = location12.id
            self.location_model.create(location32_vals)
            
            location22_vals = default_location_vals.copy()
            location22_vals['name'] = 'TEST_K RETURN'
            location22_vals['code'] = 'TEST_K_RET'
            location22_vals['location_id'] = location12.id
            self.location_model.create(location22_vals)
            