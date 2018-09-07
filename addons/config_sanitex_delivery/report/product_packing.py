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
        self._totals = {}
        self._lines = []
        self._loading_lines = []
        self._cash_lines = []
        self.localcontext.update({
            'context': context,
            'get_objects': self._get_objects,
            'get_barcode': self._get_barcode,
            'get_name': self._get_name,
            'get_date': self._get_date,
            'get_current_date': self._get_current_date,
            'get_sheet_number': self._get_sheet_number,
            'get_receiver_code': self._get_receiver_code,
            'get_sender_info': self._get_sender_info,
            'get_carrier_info': self._get_carrier_info,
            'get_weight': self._get_weight,
            'get_loading_time': self._get_loading_time,
            'get_lines': self._get_lines,
            'get_loading_lines': self._get_loading_lines,
            'get_cash_lines': self._get_cash_lines,
            'get_totals': self._get_totals,
            'print_loading_table': self._print_loading_table,
            'duplicate': self._duplicate
        })
    
    
    
    def _duplicate(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        if rep_obj.check_if_dublicate(
            cr, uid, 'config_sanitex_delivery.product_packing',
            'stock.route', route.id, context=context
        ):
            return _('(Duplicate)')
        return ''
    
    def _get_objects(self):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        objects = self.localcontext['objects']
        return rep_obj.get_objects_for_product_packing(
            cr, uid, objects, context=context
        )
    
    def _get_barcode(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_barcode_for_product_packing(
            cr, uid, route, context=context
        )
    
    def _get_name(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_name_for_product_packing(
            cr, uid, route, context=context
        )
    
    def _get_date(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_date_for_product_packing(
            cr, uid, route, context=context
        )
    
    def _get_current_date(self):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_current_date_for_product_packing(
            cr, uid, context=context
        )
    
    def _get_sheet_number(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_sheet_number_for_product_packing(
            cr, uid, route, context=context
        )
    
    def _get_receiver_code(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_receiver_code_for_product_packing(
            cr, uid, route, context=context
        )
    
    def _get_sender_info(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_sender_info_for_product_packing(
            cr, uid, route, context=context
        )
    
    def _get_loading_time(self, object):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_loading_time_for_product_packing(
            cr, uid, object, context=context
        )
    
    def _get_carrier_info(self, object):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_carrier_info_for_product_packing(
            cr, uid, object, context=context
        )
    
    def _get_weight(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_weight_for_product_packing(
            cr, uid, route, context=context
        )
    
    def _get_document_no(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_document_no_for_product_packing(
            cr, uid, packing, context=context
        )
    
    def _get_load_sheet_no(self, packing):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        return rep_obj.get_load_sheet_no_for_product_packing(
            cr, uid, packing, context=context
        )
    
    def _get_lines(self, route):
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
    
    def _get_loading_lines(self, route):
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
    
    def _get_cash_lines(self, route):
        rep_obj = self.env('stock.report')
        cr = self.cr
        uid = self.uid
        context = self.localcontext['context']
        totals = self._totals
        res = rep_obj.get_cash_lines_for_product_packing(
            cr, uid, route, totals, context=context
        )
        self._cash_lines = res
        self._totals = totals
        return res
    
    def _print_loading_table(self, route):
        if self._get_loading_lines(route):
            return True
        return False
    
    def _get_totals(self, route):
        return self._totals