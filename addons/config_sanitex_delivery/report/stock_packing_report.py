# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from openerp.report import report_sxw
from openerp.tools.translate import _

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self._total = {}
        self.localcontext.update({
            'context': context,
            'get_objects': self._get_objects,
            'get_number': self._get_number,
            'get_route_receiver': self._get_route_receiver,
            'get_packing_index': self._get_packing_index,
            'get_date': self._get_date,
            'get_pos': self._get_pos,
            'get_buyer': self._get_buyer,
            'get_unload_place': self._get_unload_place,
            'get_company_code': self._get_company_code,
            'get_vat_code': self._get_vat_code,
            'get_tel': self._get_tel,
            'get_fax': self._get_fax,
            'get_address': self._get_address,
            'get_seller': self._get_seller,
            'get_s_tel': self._get_s_tel,
            'get_s_fax': self._get_s_fax,
            'get_bank': self._get_bank,
            'get_lines': self._get_lines,
            'get_driver': self._get_driver,
            'duplicate': self._duplicate,
        })
    
    def _duplicate(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        if rep_obj.check_if_dublicate(
            cr, uid, 'config_sanitex_delivery.stock_packing_report',
            'stock.packing', packing.id, context=context
        ):
            return _('(Duplicate)')
        return ''
    
    def _get_objects(self, data=None):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        objects = self.localcontext['objects']
        return rep_obj.get_objects_for_packing_report(
            cr, uid, objects, data, context=context
        )
        
    def _get_number(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_number_for_packing_report(
            cr, uid, packing, context=context
        )
    
    def _get_route_receiver(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_route_receiver_for_packing_report(
            cr, uid, packing, context=context
        )
    
    def _get_packing_index(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_packing_index_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _get_date(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_date_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _get_pos(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_pos_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _get_buyer(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_buyer_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _get_unload_place(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_unload_place_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _get_company_code(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_company_code_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _get_vat_code(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_vat_code_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _get_tel(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_tel_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _get_fax(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_fax_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _get_address(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_address_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _get_seller(self, packing, comp):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_seller_for_packing_report(
            cr, uid, packing, comp, context=context
        )
        
    def _get_s_tel(self, packing, comp):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_s_tel_for_packing_report(
            cr, uid, packing, comp, context=context
        )
        
    def _get_s_fax(self, packing, comp):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_s_fax_for_packing_report(
            cr, uid, packing, comp, context=context
        )
        
    def _get_bank(self, packing, comp):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_bank_for_packing_report(
            cr, uid, packing, comp, context=context
        )
        
    def _get_lines(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_lines_for_packing_report(
            cr, uid, packing, context=context
        )
        
    def _get_driver(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_driver_for_packing_report(
            cr, uid, packing, context=context
        )