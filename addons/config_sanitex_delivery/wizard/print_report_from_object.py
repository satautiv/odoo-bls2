# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api


class PrintReportFromObject(models.TransientModel):
    _name = 'print.report.from.object.osv'
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
        rep_log = self.env['report.print.log']
        context = self.env.context or {}
        report_name = self._get_report()
        model = context.get('active_model', '')
        ids = context.get('active_ids', [0])
        record = self.env[model].browse(ids)
        records_to_print = record.get_records_to_print(self.report)
        already = rep_log.already_printed(records_to_print._name, report_name, records_to_print.mapped('id'))
        return already

    @api.model
    def _get_all_reports(self):
        rep_obj = self.env['ir.actions.report']
        reports = rep_obj.search([
            ('keep_log', '=', True)
        ])
        res = []
        for report in reports:
            rep = report.read(['name', 'report_name'])[0]
            res.append((rep['report_name'], rep['name']))
        return res

    @api.model
    def _get_number_of_copies(self):
        report_name = self._get_report()
        if not report_name:
            return 1
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

        domain_part = [('report_id.report_name', '=', report_name)]
        if current_warehouse:
            number_of_copies_rec = number_of_copies_env.search(
                domain_part + [('warehouse_ids', 'in', current_warehouse.id)],
                limit=1
            )
            if number_of_copies_rec:
                return number_of_copies_rec.number_of_copies

        number_of_copies_rec = number_of_copies_env.search(
            domain_part + [('warehouse_ids', '=', False)], limit=1
        )
        if number_of_copies_rec:
            return number_of_copies_rec.number_of_copies
        return 1

    report = fields.Char('Report Name', size=128, default=_get_report)
    model = fields.Char('Model', size=128, default=lambda self: (self.env.context or {}).get('active_model', ''))
    record_id = fields.Integer('Record ID', default=lambda self: (self.env.context or {}).get('active_ids', [0])[0])
    record_id_str = fields.Char('Record ID', size=128, default=lambda self: str((self.env.context or {}).get('active_ids', [])))
    printer_id = fields.Many2one('printer', 'Printer', default=_get_printer)
    reprint_reason = fields.Char('Reason for Reprinting', size=512)
    file = fields.Binary('File')
    number_of_copies = fields.Integer("Number of Copies", required=True, default=_get_number_of_copies)
    reprint = fields.Boolean('Reprinting', default=_get_reprint)
    confirmation = fields.Boolean('Confirmation', default=lambda self: (self.env.context or {}).get('for_confirmation', False))

    @api.multi
    def print_report(self):
        rep_obj = self.env['ir.actions.report']
        report = rep_obj.search([
            ('report_name','=',self.report)
        ])
        record = self.env[self.model].browse(self.record_id)
        records_to_print = record.get_records_to_print(self.report)
        report.print_report(records_to_print, printer=self.printer_id, reprint_reason=self.reprint_reason, copies=self.number_of_copies)
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def confirm(self):
        context = self.env.context or {}
        record = self.env[self.model].browse(self.record_id)
        record.action_done()
        if not context.get('will_be_printed', False):
            record.do_not_print_reports(self.report)

    @api.multi
    def print_report_and_confirm(self):
        self.with_context(will_be_printed=True).confirm()
        self.print_report()