# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, fields, _, SUPERUSER_ID
from odoo import api
from odoo.exceptions import UserError

import pytz
import datetime
import time

i = 1
GROUP_FOR_EDDITING_EXPORTS = 'base.group_system'

class ResUsers(models.Model):
    _inherit = 'res.users'

    default_warehouse_id = fields.Many2one(
        'stock.warehouse', 'Default Warehouse',readonly=True
    )
    default_printer_id = fields.Many2one(
        'printer', 'Default Printer',readonly=True
    )
    allowed_warehouse_ids = fields.Many2many(
        'stock.warehouse', 'warehouse_user_rel_ids',
        'warehouse_id', 'user_id', 'Allowed Warehouses'
    )
    default_region_id = fields.Many2one(
        'stock.region', 'Default Region',readonly=True
    )
    #
    # @api.multi
    # def _export_rows(self, fields):
    #     if self.env.user.company_id.user_faster_export:
    #         res = self.env['ir.model'].export_rows_with_psql(fields, self)
    #     else:
    #         res = super(ResUsers, self)._export_rows(fields)
    #     return res

    @api.multi
    def check_default_wh_region(self):
        if not self.default_region_id and not self.default_warehouse_id:
            raise UserError(_('To do that you have to have warehouse or region selected.'))

    @api.multi
    def does_user_belong_to_group(self, group_xml_id):
        group = self.env.ref(group_xml_id)
        if self.env.uid in group.users.mapped('id'):
            return True
        return False

    @api.multi
    def can_user_edit_export(self, functions):
        if not set(functions) & {'o_delete_exported_list', 'o_toggle_save_list'} \
            or self.does_user_belong_to_group(GROUP_FOR_EDDITING_EXPORTS)\
        :
            return True
        return False


    @api.multi
    def get_author_dict(self):
        d = {
             'authorid': str(self.id),
             'firstname': self.name.split(' ')[0],
             'lastname': self.name.split(' ')[-1],
        }
        return d
    
    @api.model
    def create(self, vals):
        return super(ResUsers, self).create(vals)
    
    @api.multi
    def get_default_warehouse(self):
        return self.default_warehouse_id and self.default_warehouse_id.id or False

    @api.multi
    def get_default_printer(self):
        return self.default_printer_id and self.default_printer_id.id or False

    @api.multi
    def is_user_in_group_xml(self, xml_full_name):
        data_obj = self.env['ir.model.data']
        grp_obj = self.env['res.groups']
        
        xml_module, xml_name = xml_full_name.split('.')
        
        data = data_obj.search([
            ('module','=',xml_module),
            ('name','=',xml_name),
            ('model','=','res.groups')
        ])
        if data:
            group = grp_obj.browse(data.res_id)
            if self.id in [user.id for user in group.users]:
                return True
        return False
    
    @api.multi
    def convert_datetime_to_user_tz(self, datetime_str):
        self.ensure_one()
        
#         if not self.tz:
#             raise UserError(
#                 _('User %s does not have filled time zone.') % (self.name)
#             )

        tz = self.tz or 'Europe/Vilnius'

        local = pytz.timezone(tz)
        
        date_utc = datetime.datetime.strptime(
            datetime_str, "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=pytz.utc)
        return date_utc.astimezone(local).strftime("%Y-%m-%d %H:%M:%S")
    
    @api.multi
    def get_today_datetime(self, format="%Y-%m-%d %H:%M:%S"):
        self.ensure_one()

        tz = self.tz or 'Europe/Vilnius'

        local = pytz.timezone(tz)
        
        date_utc = datetime.datetime.strptime(
            time.strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=pytz.utc)
        return date_utc.astimezone(local).strftime(format)

    @api.multi
    def unlink(self):
        context = self.env.context or {}
        if not context.get('allow_to_unlink_user', False):
            # Buvo nuspręsta kad naudotojų nebus galima trinti
            raise UserError(_('You cant not delete users. Make users inactive instead.'))
        return super(ResUsers, self).unlink()

    @api.multi
    def _is_admin(self):
        # Pakeitimas kad naudotojo formos langą galėtų atidaryti ne tik sistemos administratorius
        context = self.env.context or {}
        if context.get('allow_to_change_user_groups', False):
            return True
        else:
            return super(ResUsers, self)._is_admin()

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        # Pakeitimas kad naudotojo formos langą galėtų atidaryti ne tik sistemos administratorius
        context = self.env.context or {}
        ctx = context.copy()
        ctx['allow_to_change_user_groups'] = True
        return super(ResUsers, self.with_context(ctx)).fields_get(allfields=allfields, attributes=attributes)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ResUsers, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                      submenu=submenu)
        return res

    def _add_reified_groups(self, fields, values):
        """ add the given reified group fields into `values` """
        context = self.env.context or {}
        if context.get('no_default', False):
            return
        else:
            return super(ResUsers, self)._add_reified_groups(fields, values)
        # for f in fields:
        #     if f.startswith('sel_groups_'):
        #         values[f] = False

    @api.multi
    def get_current_warehouses(self):
        warehouses = self.env['stock.warehouse']
        if self.default_warehouse_id:
            return self.default_warehouse_id
        elif self.default_region_id:
            return self.default_region_id.sudo().warehouse_of_region_ids
        else:
            return warehouses.browse([])

    @api.model    
    def get_available_warehouses(self):
        warehouse_env = self.env['stock.warehouse']
        res = []
        user = self.browse(self.env.uid)
        domain = [('responsible_user_ids','in',self._uid)]
        if user.default_region_id:
            domain.append(('region_id','=',user.default_region_id.id))
        warehouses = warehouse_env.search(domain)
        if user.default_warehouse_id:
            res.append((False, _('Remove selected warehouse')))
        for warehouse in warehouses:
            res.append((warehouse.id, warehouse.name))
        return res
    
    @api.multi    
    def select_warehouse(self, warehosue_id):
        res = self.write({
            'default_warehouse_id': warehosue_id
        })

        # Patikrinam ar naudotojo spausdintuvas priklauso naujai pasirinktam sandėliui
        # ir jeigu nepriklauso, tada spausdintuvas nuimamas
        if self.default_printer_id and self.default_warehouse_id and \
            self.default_printer_id not in self.default_warehouse_id.printer_ids \
        :
            self.select_printer(False)
        if warehosue_id:
            self.select_region(False)
        self.env['ir.ui.menu'].invalidate_cache()
        return res
        
    @api.model    
    def get_available_printers(self):
        printer_env = self.env['printer']
        res = []
        printers = printer_env.with_context(search_printer_by_wh=True).search([])
        for printer in printers:
            res.append((printer.id, printer.name))
        return res
    
    @api.multi    
    def select_printer(self, printer_id):
        return self.write({
            'default_printer_id': printer_id
        })

    @api.model
    def get_available_regions(self):
        region_env = self.env['stock.region']
        user = self.browse(self.env.uid)
        res = []
        if user.does_user_belong_to_group('config_sanitex_delivery.stock_route_region_group'):
            regions = region_env.search([('responsible_user_ids','in',self._uid)])
            if user.default_region_id:
                res.append((False, _('Remove selected region')))
            for region in regions:
                res.append((region.id, region.name))
        return res

    @api.multi
    def select_region(self, region_id):
        # Patikrinam ar naujai pasirinktam regionui priklauso naudotojo seniau pasirinktas sandėlis,
        # jeigu nepriklauso, sandėlis nuimamas

        if region_id:
        #     and self.default_warehouse_id and ((self.default_warehouse_id.region_id \
        #     and self.default_warehouse_id.region_id.id != region_id) or not self.default_warehouse_id.region_id) \
        # :
            self.select_warehouse(False)
        res = self.write({
            'default_region_id': region_id
        })
        # Patikrinam ar naudotojo spausdintuvas priklauso naujai pasirinktam sandėliui
        # ir jeigu nepriklauso, tada spausdintuvas nuimamas

        if self.default_region_id and self.default_printer_id and \
            self.default_printer_id not in self.default_region_id.warehouse_of_region_ids.mapped('printer_ids')\
        :
            self.select_printer(False)
        return res

    @api.model
    def update_args(self, args):
        context = self.env.context or {}
        if context.get('filter_users_by_group', False):
            user = self.browse(self.env.uid)
            if user.does_user_belong_to_group('base.group_system'):
                pass
            elif user.does_user_belong_to_group('config_sanitex_delivery.stock_route_managament_group'):
                args.append(('id','not in',self.sudo().env.ref('base.group_system').users.mapped('id')))
            else:
                args.append(('id','=',self._uid))


    @api.model
    def _search(
        self, args, offset=0, limit=None,
        order=None, count=False,
        access_rights_uid=None
    ):
        self.update_args(args)
        return super(ResUsers, self)._search(
            args, offset=offset, limit=limit,
            order=order, count=count,
            access_rights_uid=access_rights_uid
        )
        
    @api.multi
    def write(self, vals):
        context = self._context and self._context.copy() or {}
        if (self._uid in self.ids) and ('password' in vals.keys()) and not context.get('pw_change_wizard', False):
            raise UserError(
                _('You cannot change your password directly in form view. Please use action "Change password".')
            )
        
        return super(ResUsers, self).write(vals)
    
    #Jei parinkas sandelis, grazins ta sandelio ID. Jei parinktas regionas, grazins to regiono pagrindinio sandelio ID
    @api.multi
    def get_main_warehouse_id(self):
        self.ensure_one()
        self._cr.execute('''
            SELECT
                default_warehouse_id, default_region_id
            FROM
                res_users
            WHERE id = %s
            LIMIT 1
        ''', (self.id,))
        
        default_warehouse_id, default_region_id = self._cr.fetchone()
        if default_warehouse_id:
            warehouse_id = default_warehouse_id
        elif default_region_id:
            self._cr.execute('''
                SELECT
                    location_id, name
                FROM
                    stock_region
                WHERE id = %s
                LIMIT 1
            ''', (default_region_id,))
            location_id, region_name = self._cr.fetchone()
            if not location_id:
                raise UserError(_('Region %s does not have main location filled in.') % (region_name))
            warehouse = self.env['stock.location'].browse(location_id).get_location_warehouse_id()
            if warehouse:
                warehouse_id = warehouse.id
            else:
                raise UserError(_('Main location of the region %s does not have warehouse.') % (region_name))
        else:
            raise UserError(_('Please select warehouse or region you are working in.'))
            
        
        return warehouse_id

class UsersView(models.Model):
    _inherit = 'res.users'

    @api.model
    def default_get(self, fields):
        context = self.env.context or {}
        ctx = context.copy()
        ctx['no_default'] = True
        return super(UsersView, self.with_context(ctx)).default_get(fields)

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        grp_obj = self.env['res.groups']
        res = super(UsersView, self).fields_get(allfields=allfields, attributes=attributes)
        if self.env.uid != SUPERUSER_ID:
            for field_name in res.keys():
                if 'sel_groups_' in field_name and res[field_name]['type']:
                    for group_tuple in res[field_name]['selection']:
                        if group_tuple[0]:
                            group = grp_obj.sudo().browse(group_tuple[0])
                            if self.env.uid in group.users.mapped('id'):
                                break
                    else:
                        res[field_name]['selection'] = [(False, '')]
        return res