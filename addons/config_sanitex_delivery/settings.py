# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import api, models, _, fields
from odoo.exceptions import UserError


import xml.dom.minidom
import time
import subprocess
import requests
import datetime

from os import listdir
from os.path import isfile, join, getatime
import os

import logging
_logger = logging.getLogger(__name__)

class printer(models.Model):
    _name = 'printer'
    _description = 'Printer'

    @api.model
    def _get_drivers(self):
        res = subprocess.Popen("ls /etc/cups/ppd", stdout=subprocess.PIPE, shell=True)
        res_terminal = res.communicate()
        if res_terminal and res_terminal[0]:
            return [(ppd,ppd[:-4]) for ppd in res_terminal[0].decode('utf-8').split('\n') if ppd]
        else:
            return []
        
    
    @api.model
    def _get_default_drivers(self):
        context = self.env.context or {}
        drivers = self.env['res.users'].browse(self.env.uid).company_id.get_allowed_printer_drivers()
        if context.get('additional_driver', False):
            drivers += [(context['additional_driver'],context['additional_driver'])]
        return drivers

    @api.model
    def _get_default_driver(self):
        comp = self.env['res.users'].browse(self.env.uid).company_id
        if comp and comp.default_driver:
            return comp.default_driver
        return False

    name = fields.Char('Name', size=128, required=True,
        help='Printer name in Windows system'
    )
    ip_address = fields.Char('IP', size=128),
    printer = fields.Char('Printer ID', size=128, required=True,
        help='Unique printer name in Odoo system'
    )
    port = fields.Char('Printer Port', size=16)

    driver = fields.Selection(_get_default_drivers, 'Printer Driver', default=_get_default_driver)
    registered = fields.Boolean('Registered', readonly=True, default=False)
    options = fields.Text('Options', readonly=True)
    staple = fields.Boolean('Staple', default=False)
    ip_address = fields.Char('IP', size=128, required=True)
    driver_string = fields.Char('Printer Driver', size=128, readonly=True)
    warehouse_ids = fields.Many2many('stock.warehouse', 'warehouse_printer_rel', 'printer_id', 'warehouse_id', 'Warehouses')
    a4 = fields.Boolean('Format A4', default=False)


    _sql_constraints = [
        ('printer_id_uniq', 'unique (printer)', 'Printer with this ID already exists')
    ]

    @api.model
    def update_args(self, args):
        context = self.env.context or {}
        if context.get('search_printer_by_wh', False):
            # Ieškomi tik tie spausdintuvai, kurie priskirti prie naudotojo sandėlio arba regiono.
            user = self.env['res.users'].browse(self.env.uid)
            if user.default_warehouse_id:
                args.append(('id','in',user.default_warehouse_id.printer_ids.mapped('id')))
            elif user.default_region_id:
                args.append(('id','in',user.default_region_id.warehouse_of_region_ids.mapped('printer_ids').mapped('id')))

    @api.model
    def _search(
        self, args, offset=0, limit=None,
        order=None, count=False,
        access_rights_uid=None
    ):
        self.update_args(args)
        return super(printer, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )

    @api.multi
    def update_options(self):
        for printer_obj in self:
            command = 'lpoptions -p %s -l' % printer_obj.printer
            try:
                op = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
                options = op.communicate()
                if options and options[0]:
                    printer_obj.write({'options': options[0]})
            except:
                pass

        return True

    @api.multi
    def add_printer(self):
        context = self.env.context or {}
        for printer in self:
            if not printer.driver:
                raise UserError(_('Printer(%s, ID: %s) has to have driver filled in') %(printer.name or '', str(printer.id)))
            if not printer.printer:
                raise UserError(_('Printer(%s, ID: %s) has to have Printer ID filled in') %(printer.name or '', str(printer.id)))
            if not printer.ip_address:
                raise UserError(_('Printer(%s, ID: %s) has to have IP filled in') %(printer.name or '', str(printer.id)))

            company = self.env['res.users'].browse(self.env.uid).company_id
            password = company.ssh_password or '@dm1nroot'

            printer_names = []
            printer_list_command = 'lpstat -p'
            system_printer_list_res = subprocess.Popen(printer_list_command, stdout=subprocess.PIPE, shell=True)
            system_printer_list = system_printer_list_res.communicate()
            for printer_name in system_printer_list[0].decode('utf-8').split('\n'):
                if printer_name.split(' ')[0] == 'printer':
                    printer_names.append(printer_name.split(' ')[1])

            if printer.printer not in printer_names:

                #"""sudo /usr/sbin/lpadmin -p Xeron-xeron-a -E -v socket://192.168.21.171:9100 -P /etc/cups/ppd/Xerox_HP_COLOR.ppd"""
                if printer.port:
                    command = '/usr/sbin/lpadmin -p %s -E -v socket://%s:%s -P /etc/cups/ppd/%s' % (
                        printer.printer, printer.ip_address, printer.port, printer.driver
                    )
                else:
                    command = '/usr/sbin/lpadmin -p %s -E -v socket://%s -P /etc/cups/ppd/%s' % (
                        printer.printer, printer.ip_address, printer.driver
                    )

                operation = subprocess.Popen(["sudo -S %s"%(command)], stdin=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                operation.communicate((password + '\n').encode('utf-8'))
            else:
                ctx = context.copy()
                ctx['additional_driver'] = printer.printer

                printer.sudo().with_context(ctx).write({'driver': printer.printer})
            printer.sudo().write({'registered': True})
            printer.sudo().update_options()
        return True
        
    @api.multi
    def linux_print(self, file, copies=1):
        if not file:
            return False
        if not self.name:
            raise UserError(_('Printer(ID: %s) has to have name filled in') % str(self.id))
        if not self.registered:
            self.add_printer()
        if self.staple:
            command = 'lp -d %s %s -n %s -o collate=true -o stapleoption=one' %(self.printer, file, str(copies))
        else:
            command = 'lp -d %s %s' %(self.printer, file)
        if self.a4:
            command = command + ' -o PageSize=A4'
            
        # command += ' -o fit-to-page'
        for i in range(copies):
            _logger.info('Printing Command: %s' % command)
            subprocess.call(command, shell=True)
            if self.staple:
                break
        return True

    @api.model
    def write_file_to_server(self, file_content, file_name):
        # Išsaugo failą serveryje ir grąžina to failo vietą

        company = self.env['res.users'].browse(self.env.uid).company_id
        location = company.report_location
        if not location:
            raise UserError(_('You have to fill in report store location in %s company settings') % company.name)
        report_internal_name = file_name
        report_name = datetime.datetime.now().strftime('%Y%m%d%H%M%S_%f') + '_' + report_internal_name + '.pdf'
        full_report_name = location + '/' + report_name
        report_file = open(full_report_name, 'wb')
        report_file.write(file_content)
        report_file.close()
        return full_report_name


    @api.model
    def get_report(self, xml_sting, report):
        # Gautą xmlą nusiunčia į ataskaitų serverį iš kurio gauna pdf ataskaitą
        # ją išsaugo serveryje ir grąžiną pilną kelią iki išsaugotos pdf ataskaitos
        # Ataskaitų serverio linkas ir katalogas kur išsisaugo 
        # ataskaitos turi būti suvesti įmonės nustatymuose

        company = self.env['res.users'].browse(self.env.uid).company_id
        server = company.report_server
        if not server:
            raise UserError(_('You have to fill in report server in %s company settings') % company.name)
        headers = {
            'Content-type': 'application/xml',
        }
        if company.log_report_xml:
            context = self.env.context or {}
            ext_log_env = self.env['report.print.log.extended']

            pretty_xml = xml.dom.minidom.parseString(xml_sting).toprettyxml()
            _logger.info('Printing report: %s. Sending xml to %s with headers %s. XML: \n %s' % (
                report, server, str(headers), pretty_xml
            ))
            if context.get('created_report_logs', []):
                log_extended_values = {
                    'sent_xml': pretty_xml,
                    'report_server': server
                }
                for log_id in context['created_report_logs']:
                    log_extended_values['main_log_id'] = log_id
                    ext_log_env.sudo().create(log_extended_values)


        response = requests.post(server, data=xml_sting, headers=headers)
        return self.write_file_to_server(response.content, report)

    @api.model
    def get_report_from_odoo(self, report_name, ids, data=None):
        # Sugeneruoja pdf failą iš Odoo Qweb ataskaitų

        rep_obj = self.env['ir.actions.report']
        report = rep_obj.search([('report_name','=',report_name)], limit=1)
        if not report:
            raise UserError(_('Report %s does not exsist') % report_name)
        pdf_content, report_type = report.sudo().render_qweb_pdf(ids, data=data)
        return self.write_file_to_server(pdf_content, report_name)


    @api.model
    def cron_remove_reports(self): 
        company = self.env['res.users'].browse(self.env.uid).company_id
        days_after = company.delete_reports_after
        _logger.info('Removing old Reports (%s days old)' % str(days_after))
        location = company.report_location
        onlyfiles = [f for f in listdir(location) if isfile(join(location, f))]
        
        today = datetime.datetime.now()
        date_intil = today - datetime.timedelta(days=days_after)
        
        for filename in onlyfiles:
            date_str = filename.split('_')[0]
            try:
                file_datetime = datetime.datetime.strptime(date_str, '%Y%m%d%H%M%S')
                if file_datetime < date_intil:
                    os.remove(location + '/' + filename)
            except:
                pass
        return True

    @api.model
    def cron_remove_files_from_tmp(self):
        _logger.info('Removing files from tmp')
        location = '/tmp'
        onlyfiles = [f for f in listdir(location) if isfile(join(location, f))]
        now = time.time()
        removed = 0
        _logger.info('Found %s files in tmp' %str(len(onlyfiles)))
        for filename in onlyfiles:
            try:
                if filename.split('.')[-1] in ['odt', 'pdf']:
                    if (now - getatime(join(location, filename))) / 60 / 60 / 24 > 5.0:
                        os.remove(join(location, filename))
                        removed += 1
            except:
                pass
        _logger.info('Removed %s files from tmp' %str(removed))

    @api.model
    def update_vals(self, vals):
        if 'driver' in vals.keys():
            vals['driver_string'] = vals['driver']
    
    @api.model
    def create(self, vals):
        self.update_vals(vals)
        return super(printer, self).create(vals)
    
    @api.multi
    def write(self, vals):
        self.update_vals(vals)
        return super(printer, self).write(vals)
        
        
class PrinterDriver(models.Model):
    _name = 'printer.driver'
    _description = 'Printer Driver'
    
    name = fields.Char('Name', size=128, required=True)
    code = fields.Char('Internal Name', size=256, required=True)
    
    @api.model
    def update_drivers(self):
        # Automatiškai sukuria printerių draiverio objektus. Sukuria tiems 
        # driveriams, kurių failai jau yra kataloge '/etc/cups/ppd'
        
        context = self.env.context or {}
        create_ctx = context.copy()
        create_ctx['allow_to_create_driver'] = True
        no_update_ctx = context.copy()
        no_update_ctx['dont_update_drivers'] = True
        
        system_drivers = self.env['printer']._get_drivers()
        all_drivers = self.with_context(no_update_ctx).search([])
        used_drivers = self.browse()
        for system_driver in system_drivers:
            driver = self.with_context(no_update_ctx).search([('code','=',system_driver[0])])
            if driver:
                used_drivers += driver
            else:
                used_drivers += self.with_context(create_ctx).create({
                    'name': system_driver[1], 
                    'code': system_driver[0]
                })
        (all_drivers-used_drivers).unlink()
        
    @api.model
    def create(self, vals):
        context = self.env.context or {}
        if not context.get('allow_to_create_driver', False):
            raise UserError(_('You cannot create driver. Drivers will be created automatically.'))
        return super(PrinterDriver, self).create(vals)
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        
        context = self.env.context or {}
        if not context.get('dont_update_drivers', False):
            self.update_drivers()
        return super(PrinterDriver, self).search(
            args, offset=offset, limit=limit, order=order, count=count
        )

class ImportSkipSettings(models.Model):
    _name = 'import.skip.settings'
    _description = 'Settings for import'

    @api.model
    def _get_selection_values(self):
        return self.env['stock.route.integration.intermediate'].get_selection_values()

    company_id = fields.Many2one('res.company', 'Company')
    function = fields.Selection(_get_selection_values, 'Import Function', required=True)
    date_field = fields.Char('Date To Filter By', size=256, required=True)
    day_count = fields.Integer('Days too Old', required=True)
    
class NumberOfCopies(models.Model):
    _name = 'number.of.copies'
    _description = 'Number of print copies'
    
    notes = fields.Char("Notes")
    report_id = fields.Many2one('ir.actions.report')
    number_of_copies = fields.Integer("Number of Copies", required=True)
    warehouse_ids = fields.Many2many(
        'stock.warehouse', 'num_of_copies_warehouse_rel', 'num_of_copies_id', 'warehouse_id', 'Warehouses'
    )