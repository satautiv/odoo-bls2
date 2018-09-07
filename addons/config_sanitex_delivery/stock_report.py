# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, api, _
# from operator import itemgetter
from odoo.exceptions import UserError


import time
import logging
import datetime
_logger = logging.getLogger(__name__)

from .stock import utc_str_to_local_str


class ReportPrintLog(models.Model):
    _name = 'report.print.log'
    _description = 'Printed Report Log'

    print_datetime = fields.Datetime('Printed', readonly=True)
    print_user_id = fields.Many2one('res.users', 'User', readonly=True)
    number_of_copies = fields.Integer('Number Of Copies', readonly=True)
    report_id = fields.Many2one('ir.actions.report', 'Report', readonly=True)
    report_number = fields.Char('Report Number', size=128, readonly=True)
    reason_for_reprinting = fields.Char('Reason for Reprinting', size=512, readonly=True)
    printer_id = fields.Many2one('printer', 'Printer', readonly=True)
    object = fields.Char('Model', size=256, readonly=True)
    rec_id = fields.Integer('Object ID', readonly=True)
    reprint = fields.Boolean('Reprint', readonly=True, default=False)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)
    printed_record_name = fields.Char('Document Number', readonly=True)
    print_date = fields.Date('Date', readonly=True)
    print_time = fields.Char('Time', readonly=True)
    not_printed = fields.Boolean('Not Printed', default=False)
    receiver = fields.Char('Receiver', size=128, readonly=True)
    
    _order = 'print_datetime DESC'

    @api.multi
    def open_object(self):
        return {
            'name': _('Printed Object'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': self.object,
            'type': 'ir.actions.act_window',
            'res_id': self.rec_id
        }

    @api.model
    def get_printed_record_name(self, obj, rec_id):
        res = ''
        names = self.env[obj].browse(rec_id).name_get()
        for name in names:
            if name[0] == rec_id:
                res = name[1]
        return res

    @api.model
    def already_printed(self, model, report_name, object_ids):
        rep_obj = self.env['ir.actions.report']
        report = rep_obj.search([
            ('report_name','=',report_name)
        ], limit=1)
        if report:
            if self.search([
                ('object','=',model),
                ('report_id','=',report.id),
                ('rec_id','in',object_ids),
                ('number_of_copies','>',0)
            ]):
                return True
        return False

    @api.model
    def print_report(
        self, report_name, model, object_ids,
        printer_id, reason='', copies=1, receiver=None
    ):
        rep_obj = self.env['ir.actions.report']
        res = self.env['report.print.log']
        user_env = self.env['res.users']

        report = rep_obj.search([
            ('report_name','=',report_name)
        ], limit=1)
        
        user = user_env.browse(self._uid)
        if user.default_warehouse_id:
            warehouse_id = user.default_warehouse_id.id
        elif user.default_region_id:
            location = user.default_region_id.get_main_location()
            warehouse = location.get_location_warehouse_id()
            warehouse_id = warehouse and warehouse.id or False
        else:
            warehouse_id = False
        
        
        utc_datetime = utc_str_to_local_str()
        utc_datetime_split = utc_datetime.split(' ')
        print_date = utc_datetime_split[0]
        print_time = utc_datetime_split[1]
        not_printed = False
        if copies == 0:
            not_printed = True
        if report:
            if not report.keep_log:
                return res
            for id in object_ids:
                if receiver is None:
                    try:
                        receiver_for_this_line = self.env[model].browse(id).get_receiver_for_report_log(report_name)
                    except:
                        receiver_for_this_line = ''
                        _logger.info('Object %s does not have method get_receiver_for_report_log. Report - %s ' % (model, report_name))
                else:
                    receiver_for_this_line = receiver

                log_vals = {
                    'object': model,
                    'rec_id': id,
                    'report_id': report.id,
                    'printer_id': printer_id,
                    'number_of_copies': copies,
                    'print_datetime': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'print_user_id': self.env.uid,
                    'printed_record_name': self.get_printed_record_name(model, id),
                    'warehouse_id': warehouse_id,
                    'print_date': print_date,
                    'print_time': print_time,
                    'not_printed': not_printed,
                    'receiver': receiver_for_this_line
                }
                if self.already_printed(model, report_name, [id]):
                    log_vals['reprint'] = True
                    log_vals['reason_for_reprinting'] = reason
                res += self.create(log_vals)
        else:
            raise UserError(
                _('Report %s doesn\'t exist') % report_name
            )
        return res
    
    @api.model
    def remove_old_report_history_cron(self):
        company = self.env['res.users'].browse(self.env.uid).company_id
        days_after = company.delete_report_history_after or 90
        _logger.info('Removing old Report History (%s days old)' % str(days_after))
        
        today = datetime.datetime.now()
        date_intil = today - datetime.timedelta(days=days_after)
        history = self.search([('print_datetime','<',date_intil.strftime('%Y-%m-%d %H:%M:%S'))])
        _logger.info('Removing old Report History: found %s records' % str(len(history)))
        history.with_context(allow_to_unlink_report_log=True).unlink()
        return True

    @api.multi
    def unlink(self):
        context = self.env.context or {}
        if not context.get('allow_to_unlink_report_log', False):
            raise UserError(_('You are not allowed to unlink Report Log (IDs: %s)') % str(self.mapped('id')))
        return super(ReportPrintLog, self).unlink()

    @api.multi
    def name_get(self):
        res = []
        for log in self:
            name = log.report_id.name + ' (' + log.print_user_id.name + ')'
            res.append((log.id, name))
        return res


    @api.multi
    def _export_rows(self, fields):
        if self.env.user.company_id.user_faster_export:
            res = self.env['ir.model'].export_rows_with_psql(fields, self)
        else:
            res = super(ReportPrintLog, self)._export_rows(fields)
        return res

class ReportPrintLogExtended(models.Model):
    _name = 'report.print.log.extended'
    _description = 'Printed Report Log Extended'
    _inherits = {'report.print.log': 'main_log_id'}

    main_log_id = fields.Many2one(
        'report.print.log', 'Log',
        auto_join=True, index=True, ondelete="cascade", required=True)
    sent_xml = fields.Text('Sent XML', readonly=True)
    report_server = fields.Char('Report Server', size=128, readonly=True)


    @api.multi
    def name_get(self):
        res = []
        for log in self:
            name = log.main_log_id.name_get()[0][1]
            res.append((log.id, name))
        return res