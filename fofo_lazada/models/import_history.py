from openerp import models, fields, api, _

class import_history(models.Model):
    _name = 'import.history'
    
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    seller_sku = fields.Char('Seller SKU', readonly=True)
    created_at = fields.Char('Order Date', readonly=True)
    order_number = fields.Char('Lazada Order Number', readonly=True)
    unit_price = fields.Float('Unit Price', readonly=True)
    status = fields.Char('Lazada Status', readonly=True)
    import_time = fields.Datetime('Import Time', readonly=True)
    user_id = fields.Many2one('res.users', string= 'Imported By', readonly=True)
    order_status = fields.Selection([('done', 'Done'), ('fail', 'Fail')], string='Order Status', readonly=True)
    notes = fields.Text('Reason')
    sale_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')
