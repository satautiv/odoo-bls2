# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import api, models, fields, _
from odoo.exceptions import UserError

class StockRoutePrintPackingReport(models.TransientModel):
    _name = 'stock.route.print_packing_report.osv'
    _description = 'Print Packing Report for Route' 

    @api.model
    def _get_route(self):
        context = self.env.context or {}
        return context.get('active_ids', [False])[0]

    @api.model
    def _get_report(self):
        context = self.env.context or {}
        return context.get('report_to_print', False)

    @api.model
    def _get_printer(self):
        usr_obj = self.env['res.users']
        return usr_obj.browse(self.env.uid).get_default_printer()

    @api.model
    def _get_reprint(self):
        context = self.env.context or {}
        rep_log = self.env['report.print.log']
        rep_env = self.env['ir.actions.report']
        report_name = self._get_report()
        reprint = False
        if report_name and report_name == 'config_sanitex_delivery.all_report':
            reports_in_all_reports = rep_env.search([('include_in_all_reports','=',True)])
            for report_name2 in reports_in_all_reports.mapped('report_name'):
                model = 'stock.route'
                ids = context.get('active_ids', [])
                routes = self.env['stock.route'].browse(ids)
                if report_name2 == 'config_sanitex_delivery.packing_return_act':
                    model = 'stock.picking'
                    ids = routes.mapped('returned_picking_ids').mapped('id')
                if report_name2 == 'config_sanitex_delivery.drivers_packing_transfer_act':
                    model = 'stock.picking'
                    ids = routes.mapped('picking_ids').mapped('id')
                if rep_log.already_printed(model, report_name2, ids):
                    reprint = True
                    break
            return reprint
        else:
            return rep_log.already_printed('stock.packing',
                self._get_report(), context.get('active_ids', [])
            )
            
    @api.model
    def _get_number_of_copies(self):
        report_name = self._get_report()
        if not report_name:
            return "1"
        elif report_name == 'config_sanitex_delivery.all_report':
            return _('From settings')
        
        user_env = self.env['res.users']
        number_of_copies_env = self.env['number.of.copies']
        
        user = user_env.browse(self._uid)
        if user.default_warehouse_id:
            current_warehouse = user.default_warehouse_id
        elif user.default_region_id and user.default_region_id.location_id:
            current_location = user.default_region_id.location_id
            current_warehouse = current_location.get_location_warehouse_id()
        else:
            current_warehouse = False
        
        domain_part = [('report_id.report_name','=',report_name)]
        if current_warehouse:
            number_of_copies_rec = number_of_copies_env.search(
                domain_part+[('warehouse_ids','in',current_warehouse.id)],
                limit=1
            )
            if number_of_copies_rec:
                return number_of_copies_rec.number_of_copies
        
        number_of_copies_rec = number_of_copies_env.search(
            domain_part+[('warehouse_ids','=',False)], limit=1
        )
        if number_of_copies_rec:
            return str(number_of_copies_rec.number_of_copies)
        return "1"

    report = fields.Selection([
        ('config_sanitex_delivery.customer_transfer_return_act','Customer Transfer/Return Act'),
        ('config_sanitex_delivery.all_report', 'All Reports'),
        ('config_sanitex_delivery.stock_packing_report', 'Packing Transfer-Return Act')
    ], 'Report', default=_get_report)
    parent_route_id = fields.Many2one(
        'stock.route', 'Route', readonly=True, default=_get_route
    )
    packing_ids = fields.Many2many(
        'stock.packing', 'stock_packing_print_osv_rel',
        'osv_id', 'packing_id', 'Packings To Print',
        help='If none is selected all packings will be printed'
    )
    reprint = fields.Boolean('Reprinting', default=_get_reprint)
    printer_id = fields.Many2one('printer', 'Printer', default=_get_printer)
    reprint_reason = fields.Char('Reason for Reprinting', size=512)
    number_of_copies = fields.Char("Number of Copies", size=64, default=_get_number_of_copies, required=True)
    confirmation = fields.Boolean('Confirmation', default=lambda self: (self.env.context or {}).get('for_confirmation', False))

    @api.onchange('packing_ids')
    def _onchange_packing_ids(self):
        rep_env = self.env['ir.actions.report']
        if self._get_reprint():
            self.reprint = True
            return
        packings = self.packing_ids# or self.parent_route_id.packing_for_client_ids
        if self.report == 'config_sanitex_delivery.all_report':
            reports_in_all_reports = rep_env.search([('include_in_all_reports','=',True)])
            reports = reports_in_all_reports.mapped('report_name')
        else:
            reports = [self.report]
        for report in reports:
            for packing in packings:
                if self.env['report.print.log'].already_printed(
                    'stock.packing', report, [packing.id]
                ):
                    self.reprint = True
                    return
        self.reprint = False

    @api.multi
    def print_report(self):
        try:
            number_of_copies = int(self.number_of_copies)
        except:
            if self.report == 'config_sanitex_delivery.all_report':
                number_of_copies = 0
            else:
                raise UserError(_('Wrong number of copies input. Number is expected.'))
        if self.report in ['config_sanitex_delivery.all_report', 'config_sanitex_delivery.stock_packing_report']:
            # if self.packing_ids:
            #     packs = self.packing_ids
            # else:
            #     packs = self.parent_route_id.packing_for_client_ids
            packs = self.packing_ids
            if not packs and self.report == 'config_sanitex_delivery.stock_packing_report':
                if not self.parent_route_id.packing_for_client_ids:
                    raise UserError(_('There are no client packings generated for this route.(%s)') % self.parent_route_id.name)
                else:
                    raise UserError(_('You have to select at least one client packing.'))

            packs.print_packing()
            packs.with_context(printed_routes=[]).print_report(
                self.report, printer=self.printer_id, reprint_reason=self.reprint_reason,
                route=self.parent_route_id, copies=number_of_copies
            )
        else:
            self.parent_route_id.print_report(
                self.report, printer=self.printer_id, reprint_reason=self.reprint_reason, copies=number_of_copies
            )
        return {'type': 'ir.actions.act_window_close'}
    
    
    @api.multi
    def insert_lines_with_debt(self, qty_field_name):
        self._cr.execute('''
            SELECT 
                DISTINCT(sp.id)
            FROM 
                stock_packing AS sp
                JOIN stock_packing_line AS spl ON (sp.id = spl.packing_id)
            WHERE 
                sp.route_id  = %s
                AND spl.''' + qty_field_name + ''' > 0
        ''',
            (self.parent_route_id.id,)
        )
        
        packing_ids = [sql_res_tuple[0] for sql_res_tuple in self._cr.fetchall()]
        
        self.write({
            'packing_ids': [(6, 0, packing_ids)]
        })
        
        return {
            "type": "reload",
        }
    
    
    @api.multi
    def insert_lines_with_company_debt(self):
        return self.insert_lines_with_debt('final_qty')
        
        
    @api.multi
    def insert_lines_with_posid_debt(self):
        return self.insert_lines_with_debt('customer_posid_qty')

    @api.multi
    def release_route(self):
        context = self.env.context or {}
        if self.parent_route_id:
            if self.packing_ids:
                packs = self.packing_ids
#             else:
#                 packs = self.parent_route_id.packing_for_client_ids
                packs.print_packing()
            self.parent_route_id.action_release_confirm()
            if not context.get('will_be_printed', False):
                self.parent_route_id.do_not_print_reports([
                    'config_sanitex_delivery.drivers_packing_transfer_act', # taros perdavimo aktas vairuotojui
                    'config_sanitex_delivery.product_packing', # draivas
                ])
                if self.packing_ids:
                    self.packing_ids.do_not_print_reports()

    @api.multi
    def release_and_print_report(self):
        self.with_context(will_be_printed=True).release_route()
        self.print_report()
