# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from openerp.report import report_sxw

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self._totals = {}
        self._total = {}
        self._lines = []
        self._loading_lines = []
        self.localcontext.update({
            'rep1_get_objects': self._rep1__get_objects,
            'rep1_get_current_time': self._rep1__get_current_time,
            'rep1_get_record_name': self._rep1__get_record_name,
            'rep1_get_receiver': self._rep1__get_receiver,
            'rep1_get_company_address': self._rep1__get_company_address,
            'rep1_get_lines': self._rep1__get_lines,
            'rep1_get_total': self._rep1__get_total,
            'rep1_get_lines_to_return': self._rep1__get_lines_to_return,
            
            'rep2_get_objects': self._rep2__get_objects,
            'rep2_get_loading_place': self._rep2__get_loading_place,
            'rep2_get_unloading_place': self._rep2__get_unloading_place,
            'rep2_get_lines': self._rep2__get_lines,
            'rep2_get_number': self._rep2__get_name,
            
            'rep3_get_objects': self._rep3__get_objects,
            'rep3_get_barcode': self._rep3__get_barcode,
            'rep3_get_name': self._rep3__get_name,
            'rep3_get_date': self._rep3__get_date,
            'rep3_get_current_date': self._rep3__get_current_date,
            'rep3_get_sheet_number': self._rep3__get_sheet_number,
            'rep3_get_receiver_code': self._rep3__get_receiver_code,
            'rep3_get_sender_info': self._rep3__get_sender_info,
            'rep3_get_carrier_info': self._rep3__get_carrier_info,
            'rep3_get_weight': self._rep3__get_weight,
            'rep3__get_document_no': self._rep3__get_document_no,
            'rep3__get_load_sheet_no': self._rep3__get_load_sheet_no,
            'rep3_get_loading_time': self._rep3__get_loading_time,
            'rep3_get_lines': self._rep3__get_lines,
            'rep3_get_loading_lines': self._rep3__get_loading_lines,
            'rep3_get_cash_lines': self._rep3__get_cash_lines,
            'rep3_get_totals': self._rep3__get_totals,
            'rep3_print_loading_table': self._rep3__print_loading_table,
            
            'rep4_get_objects': self._rep4__get_objects,
            'rep4_get_number': self._rep4__get_number,
            'rep4_get_route_receiver': self._rep4__get_route_receiver,
            'rep4_get_packing_index': self._rep4__get_packing_index,
            'rep4_get_date': self._rep4__get_date,
            'rep4_get_pos': self._rep4__get_pos,
            'rep4_get_buyer': self._rep4__get_buyer,
            'rep4_get_unload_place': self._rep4__get_unload_place,
            'rep4_get_company_code': self._rep4__get_company_code,
            'rep4_get_vat_code': self._rep4__get_vat_code,
            'rep4_get_tel': self._rep4__get_tel,
            'rep4_get_fax': self._rep4__get_fax,
            'rep4_get_address': self._rep4__get_address,
            'rep4_get_seller': self._rep4__get_seller,
            'rep4_get_s_tel': self._rep4__get_s_tel,
            'rep4_get_s_fax': self._rep4__get_s_fax,
            'rep4_get_bank': self._rep4__get_bank,
            'rep4_get_lines': self._rep4__get_lines,
            'rep4_get_driver': self._rep4__get_driver,
            
            'context': context
        })
        
    def _rep2__get_objects(self, data=None):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        objects = self.localcontext['objects']
        return rep_obj.get_objects_for_customer_transfer_return(
            cr, uid, objects, data=data, all=True, context=context
        )
    
    def _rep2__get_loading_place(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_loading_place_for_customer_transfer_return(
            cr, uid, packing, context=context
        )
        
    def _rep2__get_unloading_place(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_unloading_place_for_customer_transfer_return(
            cr, uid, packing, context=context
        )
    
    def _rep2__get_name(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_name_for_customer_transfer_return(
            cr, uid, packing, context=context
        )
    
    def _rep2__get_lines(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_lines_for_customer_transfer_return(
            cr, uid, packing, context=context
        )
    
    
    def _rep1__get_objects(self, data=None):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        objects = self.localcontext['objects']
        return rep_obj.get_objects_for_driver_packing_transfer(
            cr, uid, objects, data=data, all=True, context=context
        )
    
    def _rep1__get_current_time(self):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_current_time_for_driver_packing_transfer(
            cr, uid, context=context
        )
    
    def _rep1__get_record_name(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_record_name_for_driver_packing_transfer(
            cr, uid, route, context=context
        )
    
    def _rep1__get_receiver(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_receiver_for_driver_packing_transfer(
            cr, uid, route, context=context
        )
    
    def _rep1__get_company_address(self, company):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_company_address_for_driver_packing_transfer(
            cr, uid, company, context=context
        )
    
    def _rep1__get_lines(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        totals = self._total
        res = rep_obj.get_lines_for_driver_packing_transfer(
            cr, uid, route, totals, context=context
        )
        self._total = totals
        return res
    
    def _rep1__get_total(self, route):
        return self._total
    
    def _rep1__get_lines_to_return(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_lines_to_return_for_driver_packing_transfer(
            cr, uid, route, context=context
        )
    
    def _rep3__get_objects(self, data=None):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        objects = self.localcontext['objects']
        return rep_obj.get_objects_for_product_packing(
            cr, uid, objects, data=data, all=True, context=context
        )
    
    def _rep3__get_barcode(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_barcode_for_product_packing(
            cr, uid, route, context=context
        )
    
    def _rep3__get_name(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_name_for_product_packing(
            cr, uid, route, context=context
        )
        
    def _rep3__get_date(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_date_for_product_packing(
            cr, uid, route, context=context
        )
    
    def _rep3__get_current_date(self):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_current_date_for_product_packing(
            cr, uid, context=context
        )
    
    def _rep3__get_sheet_number(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_sheet_number_for_product_packing(
            cr, uid, route, context=context
        )
    
    def _rep3__get_receiver_code(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_receiver_code_for_product_packing(
            cr, uid, route, context=context
        )
    
    def _rep3__get_sender_info(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_sender_info_for_product_packing(
            cr, uid, route, context=context
        )
    
    def _rep3__get_loading_time(self, object):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_loading_time_for_product_packing(
            cr, uid, object, context=context
        )
        
    def _rep3__get_carrier_info(self, object):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_carrier_info_for_product_packing(
            cr, uid, object, context=context
        )
    
    def _rep3__get_weight(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_weight_for_product_packing(
            cr, uid, route, context=context
        )
        
    def _rep3__get_document_no(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_document_no_for_product_packing(
            cr, uid, packing, context=context
        )
    
    def _rep3__get_load_sheet_no(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_load_sheet_no_for_product_packing(
            cr, uid, packing, context=context
        )
        
    def _rep3__get_lines(self, route):
        if self._lines:
            return self._lines
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        totals = self._totals
        res = rep_obj.get_lines_for_product_packing(
            cr, uid, route, totals, context=context
        )
        self._lines = res
        self._totals = totals
        return res    
    
    def _rep3__get_loading_lines(self, route):
        if self._loading_lines:
            return self._loading_lines
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        totals = self._totals
        res = rep_obj.get_loading_lines_for_product_packing(
            cr, uid, route, totals, context=context
        )
        self._loading_lines = res
        self._totals = totals
        return res
    
    def _rep3__get_cash_lines(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        totals = self._totals
        res = rep_obj.get_cash_lines_for_product_packing(
            cr, uid, route, totals, context=context
        )
        self._loading_lines = res
        self._totals = totals
        return res
    
    def _rep3__print_loading_table(self, route):
        if self._rep3__get_loading_lines(route):
            return True
        return False
    
    def _rep3__get_totals(self, route):
        return self._totals
    
    def _rep4__get_objects(self, data=None):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        objects = self.localcontext['objects']
        return rep_obj.get_objects_for_packing_report(
            cr, uid, objects, data, context=context
        )
        
    def _rep4__get_number(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_number_for_packing_report(
            cr, uid, packing, context=context
        )
    
    def _rep4__get_route_receiver(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_route_receiver_for_packing_report(
            cr, uid, packing, context=context
        )
    
    def _rep4__get_packing_index(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_packing_index_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _rep4__get_date(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_date_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _rep4__get_pos(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_pos_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _rep4__get_buyer(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_buyer_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _rep4__get_unload_place(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_unload_place_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _rep4__get_company_code(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_company_code_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _rep4__get_vat_code(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_vat_code_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _rep4__get_tel(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_tel_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _rep4__get_fax(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_fax_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _rep4__get_address(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_address_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _rep4__get_seller(self, packing, comp):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_seller_for_packing_report(
            cr, uid, packing, comp, context=context
        )
        
    def _rep4__get_s_tel(self, packing, comp):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_s_tel_for_packing_report(
            cr, uid, packing, comp, context=context
        )
        
    def _rep4__get_s_fax(self, packing, comp):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_s_fax_for_packing_report(
            cr, uid, packing, comp, context=context
        )
        
    def _rep4__get_bank(self, packing, comp):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_bank_for_packing_report(
            cr, uid, packing, comp, context=context
        )
        
    def _rep4__get_lines(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_lines_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _rep4__get_driver(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_driver_for_packing_report(
            cr, uid, packing, context=context
        )