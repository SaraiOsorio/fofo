# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015-Today Ecosoft Co., Ltd. (http://Ecosoft.co.th).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, Warning, RedirectWarning

class account_journal(models.Model):
    _inherit = 'account.journal'

    land_cost_journal = fields.Boolean('Landed Cost Journal', help='Check this box if you are creating laneded cost journal.')

class account_invoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_cancel(self):
        for invoice in self:
            if invoice.container_id and invoice.is_shipper_invoice and invoice.container_id.state == 'done' and invoice.container_id.landed_cost_move_id:
                raise Warning (_('Error!'), ('You can not cancel invoice if container order is done or landed cost journal is created.'))
        return super(account_invoice, self).action_cancel()
    
    container_id = fields.Many2one('container.order', string="Related Container Order")
    is_shipper_invoice = fields.Boolean('Shipper Invoice', help='If this check box is ticked that will indicate the invoice is related to shipper.')
    is_inbound_invoice = fields.Boolean('Inbound Shipper Invoice', readonly=True)
    is_outbound_invoice = fields.Boolean('Outbound Shipper Invoice', readonly=True)
    recreate_invoice_id = fields.Many2one('Recreated Invoice', readonly=True)
    #allocate_land_cost = fields.Boolean('Allocate Landed Cost', help='If this check box is ticked that will indicate the landed cost will go to product and journal entry will be raised for landed cost.', readonly=True, states={'draft': [('readonly', False)]})
    #landed_cost_journal_id = fields.Many2one('account.journal', string='Landed Cost Journal',
    #    required=False, readonly=True, states={'draft': [('readonly', False)]})
    #stock_valuation_landcost_account = fields.Many2one('account.account', string='Stock Valuation Account',#TODO remove.
    #    required=False, domain=[('type', 'not in', ['view', 'closed'])],
    #    help="The stock valuation account for landed cost entry.", readonly=True, states={'draft': [('readonly', False)]})#TODO remove.
    #expense_landcost_account = fields.Many2one('account.account', string='Expense Account',
    #    required=False, domain=[('type', 'not in', ['view', 'closed'])],
    #    help="The expense account for landed cost entry.", readonly=True, states={'draft': [('readonly', False)]}) #TODO remove.
    #move_landed_cost_id = fields.Many2one('account.move', string='Journal Entry - Landed Cost',
    #    readonly=True, index=True, ondelete='restrict', copy=False,
    #    help="Link to the automatically generated Journal Items for landed cost.")

    #TODO Remove below method since its unused becuase we are creating landed cost journal entry not from here.
    @api.one
    def create_move_landed_cost(self, landed_cost_journal, stock_valuation_landcost_account, expense_landcost_account):
        #Note: Actually, I think we don't need these fields at all (but it is fine to have it invisibly but must auto default, so what??), because,
        #(see above, I updated sample) the CR in logistic journal, are always the same account as the DR on purchase journal (whatever the account is, in this case, 51200, 51201, 51202, it will be even out line by line)
        #the DR in logistic journal, at first I want to get from Stock Valuation account in Product Category, but may be not good, as Product Lines can be different products. SO -> let's use the DR account from the Landed Cost Journal master data itself, WDYT?        
        period_obj = self.env['account.period']
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        currency_obj = self.env['res.currency']
        created_move_ids = []
        
        if not self.period_id:
            period_ids = period_obj.find(self.date_invoice)
        else:
            period_ids = [self.period_id.id]
        company_currency = self.company_id.currency_id
        current_currency = self.currency_id
        ctx = dict(self._context or {})
        ctx.update({'date': self.date_invoice})
        amount = current_currency.compute(self.amount_untaxed, company_currency)
        
        if landed_cost_journal.type == 'purchase':
            sign = 1
        else:
            sign = 1#TODO check
        move_name = self.name or self.number
        reference = self.name or self.number
        move_vals = {
            'name': '/',
            'date': self.date_invoice,
            'ref': reference,
            'period_id': period_ids and period_ids[0] or False,
            'journal_id': landed_cost_journal.id,
        }
        move_id = move_obj.create(move_vals)
        journal_id = landed_cost_journal.id
        partner_id = self.partner_id.id
        for line in self.invoice_line:
            move_line_obj.create({
                'name': move_name,
                'ref': reference,
                'move_id': move_id.id,
                'account_id': line.account_id.id,
                'debit': 0.0,
                'credit': line.price_subtotal,#amount,
                'period_id': period_ids and period_ids[0] or False,
                'journal_id': journal_id,
                'partner_id': partner_id,
                'currency_id': company_currency.id <> current_currency.id and current_currency.id or False,
                'amount_currency': company_currency.id <> current_currency.id and -sign * self.amount_untaxed or 0.0,
                'date': self.date_invoice,
                #'analytic_account_id' : ?,
            })
        move_line_obj.create({
            'name': move_name,
            'ref': reference,
            'move_id': move_id.id,
            'account_id': landed_cost_journal.default_debit_account_id.id, #expense_landcost_account.id,
            'credit': 0.0,
            'debit': amount,
            'period_id': period_ids and period_ids[0] or False,
            'journal_id': journal_id,
            'partner_id': partner_id,
            'currency_id': company_currency.id <> current_currency.id and  current_currency.id or False,
            'amount_currency': company_currency.id <> current_currency.id and sign * self.amount_untaxed or 0.0,
            #'analytic_account_id': ?,
            'date': self.date_invoice,
        })
        self.write({'move_landed_cost_id': move_id.id})
        created_move_ids.append(move_id.id)
        return True

    @api.multi
    def action_move_create(self):
        res = super(account_invoice, self).action_move_create()
        for inv in self:
            #set CO to done if all ivnoices are validated and picking transffered.
            flag = True
            for i in inv.container_id.invoice_ids:
                if i.id != inv.id and i.state == 'draft' and i.is_shipper_invoice:
                    flag = False
            if flag:
                check_picking_done = True
                if not inv.container_id.is_received:
                    check_picking_done = False
                if check_picking_done and inv.container_id.draft_invoice_shipper: #container order should only be done when all shipper invoices are validated and pickings are transfferd/done.
                    inv.container_id.action_done()
        return res

