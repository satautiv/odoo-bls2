# -*- encoding: utf-8 -*-
###########################################################################
#
#    Copyright (C) 2009 Sandas. (http://www.sandas.eu) All Rights Reserved.
#
###########################################################################

from odoo import models, api
import uuid

class InternalOperationAdjustment(models.Model):
    _inherit = 'internal.operation.adjustment'


    @api.multi
    def action_done(self):
        picking_env = self.env['stock.picking']
        res = super(InternalOperationAdjustment, self).action_done()
        self._cr.execute('''
            SELECT
                operation_id
            FROM
                internal_operation_adjustment 
            WHERE 
                id in %s
        ''', (tuple(self.ids),))
        operation_ids = [i[0] for i in self._cr.fetchall()]
        print('operation_ids', operation_ids)
        self._cr.execute("""
            SELECT
                id
            FROM
                stock_picking
            WHERE 
                picking_from_warehouse_for_internal_order_id in %s
                OR picking_to_warehouse_for_internal_order_id in %s
        """ , (tuple(operation_ids),tuple(operation_ids)))
        picking_ids = [i[0] for i in self._cr.fetchall()]
        print('picking_ids', picking_ids)
        for picking_id in picking_ids:
            self._cr.execute("""
                UPDATE
                    stock_picking
                SET
                    id_external = %s
                WHERE 
                    id = %s
            """ , (str(uuid.uuid1()), picking_id,))

        pickings = picking_env.browse(picking_ids)
        pickings.set_version()
        return res

class InternalOperationMovement(models.Model):
    _inherit = 'internal.operation.movement'
    
    @api.multi
    def action_done(self):
        res = super(InternalOperationMovement, self).action_done()
        picking_env = self.env['stock.picking']
        sale_env = self.env['sale.order']
        
        
        self._cr.execute('''
            SELECT
                operation_id
            FROM
                internal_operation_movement    
            WHERE 
                id in %s
        ''', (tuple(self.ids),))
        operation_ids = [i[0] for i in self._cr.fetchall()]
        
        self._cr.execute("""
            SELECT
                id
            FROM
                stock_picking
            WHERE 
                picking_from_warehouse_for_internal_order_id in %s
        """ , (tuple(operation_ids),))
        picking_ids = [i[0] for i in self._cr.fetchall()]
        
        for picking_id in picking_ids:
            self._cr.execute("""
                UPDATE
                    stock_picking
                SET
                    id_external = %s
                WHERE 
                    id = %s
            """ , (str(uuid.uuid1()), picking_id,))
        
        pickings = picking_env.browse(picking_ids)
        pickings.set_version()
        pickings.set_transportation_order_no()
        
        
        self._cr.execute("""
            SELECT
                id
            FROM
                sale_order
            WHERE 
                internal_movement_id in %s
        """ , (tuple(self.ids),))
        sale_ids = [i[0] for i in self._cr.fetchall()]
        sales = sale_env.browse(sale_ids)
        sales.do_out_movement_despatch()
        
        return res
    