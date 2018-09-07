# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError

import csv
import base64
import time
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class StockLocationImportDriverQty(models.TransientModel):
    _name = 'stock.location.import_driver_qty'
    _description = 'Import Driver' 

    csv_file = fields.Binary(string='CSV File', required=True)
    
    @api.multi
    def import_file(self):
        loc_env = self.env['stock.location']
        warehouse_env = self.env['stock.warehouse']
        prod_env = self.env['product.product']
        spc_env = self.env['stock.packing.correction']
        spcl_env = self.env['stock.packing.correction.line']
        
        file_splited = base64.decodestring(self.csv_file).decode('utf-8').split('\n')
        csvreader = csv.reader(file_splited, delimiter = ',')
        csvreader.__next__()
        
        now_created_spcs = self.env['stock.packing.correction']
        now_created_spcls = self.env['stock.packing.correction.line']
        _PREFIX = "PRAD_LIK"
        
        _logger.info("------- Starting driver return import --------")
        for row in csvreader:
            if not row:
                continue
            driver_name = row[0]
            loc_or_wh_code = row[1]
            prod_code = row[2]
            try:
                qty = int(row[3])
            except:
                 _logger.info("Invalid quantity '%s'. CSV line:\n%s\n is skipped." % (row[3], ", ".join(row)))
                 continue
            
            date = row[4] and (row[4].replace('.','-')) or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            price = row[5]
            try:
                price = float(price)
            except:
                price = 0.0
                
            doc_number = row[6]
            
            driver_company_code = row[9]
            
            if qty < 0:
                type = 'tare_return'
#                 loc_field_name = 'stock_return_location_id'
            else:
                type = 'transfer_to_driver'
#                 loc_field_name = 'stock_source_location_id'
            
            driver = False
            if driver_name:
                driver = loc_env.search([
                    ('name','=',driver_name),
                    ('driver','=',True),
                    ('owner_id.ref','=',driver_company_code)
                ], limit=1)
            if not driver:
                _logger.info("Driver %s not found. CSV line:\n%s\n is skipped." % (driver_name, ", ".join(row)))
                continue
            
            loc = False
            warehouse = False
            if loc_or_wh_code:
                loc = loc_env.search([
                    ('code','=',loc_or_wh_code),
                    ('driver','!=',True)
                ], limit=1)
                if loc:
                    warehouse = loc.get_location_warehouse_id()
                    if qty < 0:
                        stock_return_location = loc
                        stock_source_location = self.env['stock.location']
                    else:
                        stock_return_location = self.env['stock.location']
                        stock_source_location = loc
                    
                else:
                    warehouse = warehouse_env.search([
                        ('code','=',loc_or_wh_code),
                    ], limit=1)
                    if warehouse:
                        stock_return_location = warehouse.wh_return_stock_loc_id or self.env['stock.location']
                        stock_source_location = warehouse.wh_output_stock_loc_id or self.env['stock.location']
                
            if not warehouse:
                _logger.info("Warehouse not found. CSV line:\n%s\n is skipped." % (", ".join(row)))
                continue
#             if not loc:
#                 _logger.info("Location not found. CSV line:\n%s\n is skipped." % (", ".join(row)))
            
            product = False
            if prod_code:
                product = prod_env.search([
                    ('default_code','=',prod_code),
                ], limit=1)
            if not product:
                _logger.info("Product %s not found. CSV line:\n%s\n is skipped." % (prod_code, ", ".join(row)))
                continue
            
            if doc_number:
                tmpl_spc = spc_env.search([
                    ('number','=',doc_number),
                    ('state','=','done')
                ], limit=1)
                if tmpl_spc:
                    doc_number += '_2'
            else:
                tmpl_spc = spc_env.search([
                    ('number','like',_PREFIX),
                    ('state','=','done')
                ], limit=1, order='number DESC')
                if not tmpl_spc:
                    doc_number = _PREFIX+"1"
                else:
                    last_number = tmpl_spc.number
                    last_number_digits_str = last_number[len(_PREFIX):]
                    try:
                        last_number_digits = int(last_number_digits_str)
                        doc_number = _PREFIX+ str(last_number_digits+1)
                    except:
                        doc_number = last_number + '_2'

            spc = now_created_spcs.filtered(
                lambda now_created_spc: \
                    now_created_spc.reason == type\
                    and now_created_spc.number == doc_number\
                    and now_created_spc.location_id.id == driver.id\
                    and now_created_spc.return_to_warehouse_id.id == warehouse.id\
                    and now_created_spc.stock_return_location_id == stock_return_location\
                    and now_created_spc.stock_source_location_id == stock_source_location\
                    and now_created_spc.date[:10] == date\
            )
            if not spc:
                spc = spc_env.create({
                    'reason': type,
                    'number': doc_number,
                    'location_id': driver.id,
                    'return_to_warehouse_id': warehouse.id,
                    'stock_return_location_id': stock_return_location\
                        and stock_return_location.id or False,
                    'stock_source_location_id': stock_source_location\
                        and stock_source_location.id or False,
                    'state': 'draft',
                    'date': date,
                })
                now_created_spcs += spc
            spcl = now_created_spcls.filtered(
                lambda now_created_spcl: \
                now_created_spcl.correction_id.id == spc.id\
                and now_created_spcl.product_id.id == product.id\
                and now_created_spcl.price_unit == price
            )
            if not spcl:
                spcl = spcl_env.create({
                    'correction_id': spc.id,
                    'product_id': product.id,
                    'drivers_debt': driver.get_drivers_debt(product.id),
                    'correction_qty': 0.0,
                    'price_unit': price,
                })
            spcl.write({
                'correction_qty': spcl.correction_qty + qty
            })

        now_created_spcs.action_done()
        
        _logger.info("------- Ending driver return import --------")
        return True
    
    @api.multi
    def import_file2(self):
        for osv in self:
            file_splited = base64.decodestring(osv.csv_file).decode('utf-8').split('\n')
            csvreader = csv.reader(file_splited, delimiter = ',')

            csvreader.__next__()
            data = {}
            errors = []
            for row in csvreader:
                if not row:
                    continue
                driver_company_code = row[0]
                driver_name = row[1]
                if len(row) > 2:
                    contract_no = row[2]
                else:
                    contract_no = ''
                if contract_no == 'NULL':
                    contract_no = ''
                if len(row) > 3:
                    quantity = row[3]
                    product_code = row[4]
                    wh_code = row[5]
                    skip_product_debt = False
                else:
                    skip_product_debt = True


                drivers = self.env['stock.location'].search([('name','=',driver_name),('owner_code','=',driver_company_code)])
                if not drivers:
                    partners = self.env['res.partner'].search([('ref','=',driver_company_code)])
                    if not partners:
                        msg = 'No partner with code %s' % driver_company_code
                        # raise UserError(msg)
                        _logger.info(msg)
                        errors.append((driver_company_code, driver_name))
                        continue

                    driver_vals = {
                        'name': driver_name,
                        'driver': True,
                        'owner_id': partners[0].id,
                        'active': True,
                        'contract_no': contract_no
                    }
                    driver = self.env['stock.location'].create(driver_vals)
                    self.env.cr.commit()
                else:
                    drivers.write({'contract_no': contract_no})

                if skip_product_debt:
                    # praleidžia tuomet kai importuojami tik vairuotojai, be jokių skolų
                    continue

                warehouses = self.env['stock.warehouse'].search([('code','=',wh_code)])
                if not warehouses:
                    raise UserError(_('No warehouse with code %s') % wh_code)

                products = self.env['product.product'].search([('default_code','=',product_code)])
                if not products:
                    raise UserError(_('No Product with code %s') % product_code)

                key = (warehouses[0].id, driver.id)

                if key not in data.keys():
                    data[key] = {}

                if products[0].id not in data[key].keys():
                    data[key][products[0].id] = 0
                data[key][products[0].id] += int(quantity)
            _logger.info(str(errors))
            for key in data.keys():
                correction_vals = {
                    'number': self.env['stock.packing.correction'].default_get(['number'])['number'],
                    'location_id': key[1],
                    'reason': 'operator_mistake',
                    'return_to_warehouse_id': key[0],
                    'date': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                correction = self.env['stock.packing.correction'].create(correction_vals)
                for prod_key in data[key].keys():
                    correction_line_vals = {
                        'product_id': prod_key,
                        'correction_qty': data[key][prod_key],
                        'correction_id': correction.id
                    }
                    self.env['stock.packing.correction.line'].create(correction_line_vals)
                correction.action_done()

    @api.multi
    def assign_id(self):
        for osv in self:
            file_splited = base64.decodestring(osv.csv_file).decode('utf-8').split('\n')
            csvreader = csv.reader(file_splited, delimiter = ',')

            csvreader.__next__()
            for row in csvreader:
                if not row:
                    continue
                if len(row) > 8:
                    driver_name = row[0]
                    driver_company_code = row[2]
                    driver_id = row[8]


                    driver = self.env['stock.location'].search([('name','=',driver_name),('owner_code','=',driver_company_code)], limit=1)
                    if driver:
                        driver.write({'external_driver_id': str(driver_id)})

        return {'type': 'ir.actions.act_window_close'}